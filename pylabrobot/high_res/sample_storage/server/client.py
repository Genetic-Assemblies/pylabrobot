"""A HighRes sample store served elsewhere, driven as one in this process is.

`RemoteTundraStore` is a `TundraStore`: every public coroutine, its own and its `environment`'s, is
a call to the server. Its resource tree (stackers, nests and the plates in them) is the server's,
taken up again whenever a response says it changed; plates keep their identity across that, so a
`Plate` a caller holds is the one the store moves. What a caller does to the tree by hand (puts a
plate on a nest for the store to take in, takes one off after a fetch) is sent to the server before
the next call, as the server's tree must know it too.

Not carried: the events the driver emits in this process are emitted on the server.
"""

from __future__ import annotations

import inspect
import json
from typing import (
  Any,
  AsyncIterator,
  Awaitable,
  Dict,
  List,
  Literal,
  Mapping,
  Optional,
  TypeVar,
  Union,
)

from connectrpc.client import ResponseMetadata
from connectrpc.errors import ConnectError
from pyqwest import Client

from pylabrobot.high_res.sample_storage.driver import (
  HighResSampleStorage,
  HighResSampleStorageSettings,
  UnresolvedPlateTransfer,
)
from pylabrobot.high_res.sample_storage.driver.environment import EnvironmentControl
from pylabrobot.high_res.sample_storage.driver.models import get_model_info
from pylabrobot.high_res.sample_storage.driver.types import (
  DoorState,
  EnvironmentParameter,
  NestState,
  StackerDimensions,
  VersionInfo,
)
from pylabrobot.high_res.sample_storage.server.errors import from_connect_error
from pylabrobot.high_res.sample_storage.server.serve import (
  REVISION_HEADER,
  sample_storage_server_app,
)
from pylabrobot.high_res.sample_storage.server.v1 import sample_storage_pb2 as pb
from pylabrobot.high_res.sample_storage.server.v1.sample_storage_connect import (
  SampleStorageServiceClient,
)
from pylabrobot.high_res.sample_storage.tundra_store import TundraStore
from pylabrobot.resources import (
  Coordinate,
  Plate,
  PlateCarrier,
  PlateHolder,
  Resource,
  ResourceNotFoundError,
  Rotation,
)
from pylabrobot.resources.barcode import Barcode
from pylabrobot.resources.server.asgi_transport import ASGITransport
from pylabrobot.resources.server.client import _Headers
from pylabrobot.resources.server.v1 import types_pb2 as tpb

# The address a sample-storage server held in this process is spoken to at; never dialled.
_IN_PROCESS = "http://sample-storage.in-process"

R = TypeVar("R")

_DOOR_STATES: Dict[int, DoorState] = {
  pb.DOOR_STATE_OPEN: "open",
  pb.DOOR_STATE_CLOSED: "closed",
  pb.DOOR_STATE_OPENING: "opening",
  pb.DOOR_STATE_CLOSING: "closing",
}
_NEST_STATES: Dict[int, NestState] = {
  pb.NEST_STATE_CLEAR: "clear",
  pb.NEST_STATE_OCCUPIED: "occupied",
}
_LOCATIONS = {
  "source": pb.TRANSFER_LOCATION_SOURCE,
  "destination": pb.TRANSFER_LOCATION_DESTINATION,
  "unassigned": pb.TRANSFER_LOCATION_UNASSIGNED,
}


def _ref(name: str) -> tpb.ResourceRef:
  return tpb.ResourceRef(name=tpb.NameRef(name=name))


def _parameters(environment: pb.Environment) -> Dict[str, EnvironmentParameter]:
  return {
    name: EnvironmentParameter(
      name=p.name,
      current=p.current,
      setpoint=p.setpoint if p.HasField("setpoint") else None,
      limit=p.limit if p.HasField("limit") else None,
    )
    for name, p in environment.parameters.items()
  }


class SampleStorageServer:
  """A sample-storage server: where a store is served, and how its calls get there.

  `connect` reaches one served elsewhere; `local` serves a store in this process, without a
  socket, as tests do.
  """

  def __init__(
    self, address: str, http: Optional[Client] = None, headers: Optional[Mapping[str, str]] = None
  ):
    interceptors = [_Headers(headers)] if headers else []
    self.address = address
    self.client = SampleStorageServiceClient(address, http_client=http, interceptors=interceptors)
    # The revision of the description the last response said is current.
    self.revision: Optional[str] = None

  @classmethod
  def connect(cls, url: str, headers: Optional[Mapping[str, str]] = None) -> SampleStorageServer:
    """A sample-storage server at `url`, "http://127.0.0.1:8091" say.

    Args:
      headers: sent with every call: the credentials the server asks for.
    """
    return cls(url, Client(), headers=headers)

  @classmethod
  def local(cls, store: HighResSampleStorage, set_up: bool = False) -> SampleStorageServer:
    """A store served in this process, spoken to over Connect without a socket."""
    app = sample_storage_server_app(store, set_up=set_up)
    return cls(_IN_PROCESS, Client(transport=ASGITransport(app)))

  async def close(self) -> None:
    await self.client.close()

  @staticmethod
  def _raised(error: ConnectError) -> BaseException:
    """What the served store raised, from the Connect error it came as."""
    return from_connect_error(error) or error

  async def call(self, response: Awaitable[R]) -> R:
    """A call's response, raising what the served store raised as it raised it."""
    with ResponseMetadata() as meta:
      try:
        return await response
      except ConnectError as error:
        raise self._raised(error) from None
      finally:
        self.revision = meta.headers.get(REVISION_HEADER) or self.revision

  async def stream(self, progress: AsyncIterator[pb.Progress], what: str) -> pb.Progress:
    """Read a long call's progress until the server says it is done; its last progress.

    Raises:
      ConnectionError: If the stream ends before the call is done.
    """
    last: Optional[pb.Progress] = None
    with ResponseMetadata() as meta:
      try:
        async for each in progress:
          if each.done:
            last = each
      except ConnectError as error:
        raise self._raised(error) from None
      finally:
        self.revision = meta.headers.get(REVISION_HEADER) or self.revision
    if last is None:
      raise ConnectionError(f"the sample-storage server stopped before {what} was done")
    return last


def _server(server: Union[str, SampleStorageServer]) -> SampleStorageServer:
  return SampleStorageServer.connect(server) if isinstance(server, str) else server


class RemoteEnvironmentControl(EnvironmentControl):
  """A served store's environment: every public coroutine is a call to the server. What it last
  read (`parameters`) is the server's."""

  def __init__(self, driver: RemoteTundraStore) -> None:
    super().__init__(driver=driver)
    self._remote = driver

  async def _empty(self, response: Awaitable[Any]) -> None:
    await self._remote._call(response)

  async def _value(self, response: Awaitable[pb.Value]) -> float:
    return (await self._remote._call(response)).value

  async def refresh(self) -> Dict[str, EnvironmentParameter]:
    s = self._remote.server.client
    self._parameters = _parameters(await self._remote._call(s.refresh(pb.Empty())))
    return dict(self._parameters)

  async def request_current_temperature(self) -> float:
    return await self._value(self._remote.server.client.request_current_temperature(pb.Empty()))

  async def request_target_temperature(self) -> float:
    return await self._value(self._remote.server.client.request_target_temperature(pb.Empty()))

  async def set_temperature(self, temperature: float) -> None:
    request = pb.Temperature(temperature=temperature)
    await self._empty(self._remote.server.client.set_temperature(request))

  async def start_temperature_control(self) -> None:
    await self._empty(self._remote.server.client.start_temperature_control(pb.Empty()))

  async def stop_temperature_control(self) -> None:
    await self._empty(self._remote.server.client.stop_temperature_control(pb.Empty()))

  async def request_current_humidity(self) -> float:
    return await self._value(self._remote.server.client.request_current_humidity(pb.Empty()))

  async def request_target_humidity(self) -> float:
    return await self._value(self._remote.server.client.request_target_humidity(pb.Empty()))

  async def set_humidity(self, humidity: float) -> None:
    await self._empty(self._remote.server.client.set_humidity(pb.Humidity(humidity=humidity)))

  async def start_humidity_control(self) -> None:
    await self._empty(self._remote.server.client.start_humidity_control(pb.Empty()))

  async def stop_humidity_control(self) -> None:
    await self._empty(self._remote.server.client.stop_humidity_control(pb.Empty()))

  async def request_current_co2(self) -> float:
    return await self._value(self._remote.server.client.request_current_co2(pb.Empty()))

  async def request_target_co2(self) -> float:
    return await self._value(self._remote.server.client.request_target_co2(pb.Empty()))

  async def set_co2(self, co2: float) -> None:
    await self._empty(self._remote.server.client.set_co2(pb.Co2(co2=co2)))

  async def start_co2_control(self) -> None:
    await self._empty(self._remote.server.client.start_co2_control(pb.Empty()))

  async def stop_co2_control(self) -> None:
    await self._empty(self._remote.server.client.stop_co2_control(pb.Empty()))

  async def request_current_o2(self) -> float:
    return await self._value(self._remote.server.client.request_current_o2(pb.Empty()))

  async def request_target_o2(self) -> float:
    return await self._value(self._remote.server.client.request_target_o2(pb.Empty()))

  async def set_o2(self, o2: float) -> None:
    await self._empty(self._remote.server.client.set_o2(pb.O2(o2=o2)))

  async def start_o2_control(self) -> None:
    await self._empty(self._remote.server.client.start_o2_control(pb.Empty()))

  async def stop_o2_control(self) -> None:
    await self._empty(self._remote.server.client.stop_o2_control(pb.Empty()))

  async def request_tank_pressures(self) -> Dict[str, float]:
    s = self._remote.server.client
    return dict((await self._remote._call(s.request_tank_pressures(pb.Empty()))).pressures)


class RemoteTundraStore(TundraStore):
  """The TundraStore a sample-storage server serves: every public coroutine is a call to it.

  Its stackers, nests and plates are the server's: none until setup (or any call) has taken them
  up. Put a plate on a nest, or take one away, as in this process; the server is told before the
  next call.
  """

  def __init__(
    self,
    name: str,
    sample_storage_server: Union[str, SampleStorageServer],
    size_x: float = 0,
    size_y: float = 0,
    size_z: float = 0,
    rotation: Optional[Rotation] = None,
    category: Optional[str] = "plate_store",
    barcode: Optional[Barcode] = None,
    preferred_pickup_location: Optional[Coordinate] = None,
    metadata: Optional[Mapping[str, Any]] = None,
  ) -> None:
    """
    Args:
      name: its name: the name of the store the server serves.
      sample_storage_server: the server, or its URL.

    The other arguments place it, as a resource, in this process's tree; they are not the server's.
    """
    Resource.__init__(
      self,
      name=name,
      size_x=size_x,
      size_y=size_y,
      size_z=size_z,
      rotation=rotation,
      category=category,
      model=self._model_name,
      barcode=barcode,
      preferred_pickup_location=preferred_pickup_location,
      metadata=metadata,
    )
    self.server = _server(sample_storage_server)
    self.nests: List[PlateHolder] = []
    self._racks_by_number: Dict[int, PlateCarrier] = {}
    self._racks_loaded = False
    self._retracted_y_max = 50.0
    self._retracted_z_max = 50.0
    self._model_info = get_model_info(self._model_name)
    if self._model_info.has_environment_control:
      self.environment: EnvironmentControl = RemoteEnvironmentControl(self)
    self._read_timeout = 30.0
    self._motion_timeout = 240.0
    self._unresolved_transfer: Optional[UnresolvedPlateTransfer] = None
    # The description of the server's tree this one was last made like.
    self._revision: Optional[str] = None
    # What was done to the tree by hand since the last call: each nest or slot, by name, and the
    # plate it holds now, in the order they were done.
    self._placed: Dict[str, Optional[Plate]] = {}
    self._taking_up = False
    self.register_did_assign_resource_callback(self._did_assign)
    self.register_will_unassign_resource_callback(self._will_unassign)

  # -- the tree --

  def _holders(self) -> Dict[str, PlateHolder]:
    holders: Dict[str, PlateHolder] = {nest.name: nest for nest in self.nests}
    for rack in self._racks_by_number.values():
      for site in rack.sites.values():
        holders[site.name] = site
    return holders

  def _is_holder(self, resource: Optional[Resource]) -> bool:
    if not isinstance(resource, PlateHolder):
      return False
    return resource in self.nests or resource.parent in self._racks_by_number.values()

  def _did_assign(self, resource: Resource) -> None:
    if self._taking_up or not isinstance(resource, Plate) or not self._is_holder(resource.parent):
      return
    assert resource.parent is not None
    self._placed.pop(resource.parent.name, None)
    self._placed[resource.parent.name] = resource

  def _will_unassign(self, resource: Resource) -> None:
    if self._taking_up or not isinstance(resource, Plate) or not self._is_holder(resource.parent):
      return
    assert resource.parent is not None
    self._placed.pop(resource.parent.name, None)
    self._placed[resource.parent.name] = None

  async def _send_placed(self) -> None:
    """Tell the server what was done to the tree by hand since the last call."""
    if not self._placed:
      return
    request = pb.PlacePlatesRequest()
    for holder, plate in self._placed.items():
      placement = request.placements.add(holder=_ref(holder))
      if plate is not None:
        placement.plate.name = plate.name
        placement.plate.definition = json.dumps(plate.serialize())
    self._placed = {}
    try:
      await self.server.call(self.server.client.place_plates(request))
    except BaseException:
      # Refused: this tree is made like the server's again, which is where the plates are.
      self._revision = None
      await self._take_up()
      raise

  def _nest_holder(self, name: str) -> PlateHolder:
    return PlateHolder(name=name, size_x=127.76, size_y=85.48, size_z=0, pedestal_size_z=0)

  async def _take_up(self) -> None:
    """Make this tree like the server's, when the last response said it changed."""
    revision = self.server.revision
    if revision is not None and revision == self._revision:
      return
    description: pb.Description = await self.server.call(self.server.client.describe(pb.Empty()))
    revision = self.server.revision
    if description.model != self.model:
      raise ValueError(f"the server's store is a {description.model}, not a {self.model}")
    held: Dict[str, Plate] = {}
    for holder in self._holders().values():
      if isinstance(holder.resource, Plate):
        held[holder.resource.name] = holder.resource
    wanted: Dict[str, str] = {
      site.name: site.plate
      for stacker in description.stackers
      for site in stacker.sites
      if site.HasField("plate")
    }
    wanted.update({nest.name: nest.plate for nest in description.nests if nest.HasField("plate")})
    # The plates this tree has not got, as the server serializes them.
    made: Dict[str, Plate] = {}
    for plate_name in set(wanted.values()) - set(held):
      plate = await self.server.call(self.server.client.get_plate(_ref(plate_name)))
      made_plate = Resource.deserialize(json.loads(plate.definition))
      assert isinstance(made_plate, Plate)
      made[plate_name] = made_plate
    self._taking_up = True
    try:
      self._take_up_racks(description)
      if [n.name for n in self.nests] != [n.name for n in description.nests]:
        for nest in self.nests:
          self.unassign_child_resource(nest)
        self.nests = []
        for described in description.nests:
          nest = self._nest_holder(described.name)
          self.assign_child_resource(nest, location=None)
          self.nests.append(nest)
      holders = self._holders()
      for holder in holders.values():
        if holder.resource is not None and holder.resource.name != wanted.get(holder.name):
          holder.resource.unassign()
      for holder_name, plate_name in wanted.items():
        holder = holders[holder_name]
        if holder.resource is None:
          holder.assign_child_resource(held.get(plate_name) or made[plate_name])
      self._take_up_transfer(description, {**held, **made})
      self._read_timeout = description.read_timeout
      self._motion_timeout = description.motion_timeout
      if description.HasField("environment") and self._model_info.has_environment_control:
        self.environment._parameters = _parameters(description.environment)
    finally:
      self._taking_up = False
    self._revision = revision

  def _take_up_racks(self, description: pb.Description) -> None:
    current = {number: rack.name for number, rack in self._racks_by_number.items()}
    if current == {s.number: s.name for s in description.stackers}:
      return
    for rack in self._racks_by_number.values():
      self.unassign_child_resource(rack)
    self._racks_by_number = {}
    for stacker in description.stackers:
      rack = PlateCarrier.deserialize(json.loads(stacker.definition))
      self._add_rack(rack, stacker=stacker.number)
    self._racks_loaded = bool(description.stackers)

  def _take_up_transfer(self, description: pb.Description, plates: Dict[str, Plate]) -> None:
    if not description.HasField("unresolved_transfer"):
      self._unresolved_transfer = None
      return
    t = description.unresolved_transfer
    holders = self._holders()
    previous = self._unresolved_transfer
    plate = plates.get(t.plate)
    if plate is None and previous is not None and previous.plate.name == t.plate:
      plate = previous.plate
    if plate is None:
      plate = self.get_resource(t.plate)  # type: ignore[assignment]
    assert isinstance(plate, Plate)
    self._unresolved_transfer = UnresolvedPlateTransfer(
      plate=plate,
      source=holders[t.source],
      destination=holders[t.destination],
      command=t.command,
      error_type=t.error_type,
      error_message=t.error_message,
    )

  async def _call(self, response: Awaitable[R]) -> R:
    """Tell the server what was done by hand, make a call, and take up what it changed."""
    try:
      await self._send_placed()
    except BaseException:
      if inspect.iscoroutine(response):
        response.close()
      raise
    try:
      return await self.server.call(response)
    finally:
      await self._take_up()

  async def _stream(self, progress: AsyncIterator[pb.Progress], what: str) -> pb.Progress:
    try:
      return await self.server.stream(progress, what)
    finally:
      await self._take_up()

  def _plate_named(self, name: str) -> Plate:
    plate = self.get_resource(name)
    if not isinstance(plate, Plate):
      raise ResourceNotFoundError(f"Plate {name!r} not found in {self.name!r}.")
    return plate

  def serialize(self) -> dict:
    data = Resource.serialize(self)
    data.pop("children", None)
    return {**data, "sample_storage_server": self.server.address}

  @classmethod
  def deserialize(cls, data: dict, allow_marshal: bool = False) -> RemoteTundraStore:
    return cls(name=data["name"], sample_storage_server=data["sample_storage_server"])

  async def _send_command(self, command: str, timeout: Optional[float] = None) -> List[str]:
    raise RuntimeError("a served store's commands are made by its server")

  # -- lifecycle --

  async def setup(self, home: bool = False) -> None:
    await self._send_placed()
    request = pb.SetupRequest(home=home)
    await self._stream(self.server.client.setup(request), "the setup")

  async def stop(self) -> None:
    await self._call(self.server.client.stop(pb.Empty()))

  # -- queries --

  async def request_version(self) -> VersionInfo:
    v = await self._call(self.server.client.request_version(pb.Empty()))
    return VersionInfo(
      product_name=v.product_name if v.HasField("product_name") else None,
      serial_number=v.serial_number if v.HasField("serial_number") else None,
      firmware_version=v.firmware_version if v.HasField("firmware_version") else None,
      firmware_build=v.firmware_build if v.HasField("firmware_build") else None,
      raw=dict(v.raw),
    )

  async def request_environment(self) -> Dict[str, EnvironmentParameter]:
    return _parameters(await self._call(self.server.client.request_environment(pb.Empty())))

  async def request_axis_positions(self) -> Dict[str, float]:
    response = await self._call(self.server.client.request_axis_positions(pb.Empty()))
    return dict(response.positions)

  async def request_is_homed(self) -> bool:
    return (await self._call(self.server.client.request_is_homed(pb.Empty()))).value

  async def request_door_status(self) -> Dict[str, DoorState]:
    response = await self._call(self.server.client.request_door_status(pb.Empty()))
    return {name: _DOOR_STATES.get(state, "unknown") for name, state in response.doors.items()}

  async def request_nest_status(self) -> Dict[int, NestState]:
    response = await self._call(self.server.client.request_nest_status(pb.Empty()))
    return {n: _NEST_STATES.get(state, "unknown") for n, state in response.nests.items()}

  async def request_spatula_is_holding(self) -> bool:
    return (await self._call(self.server.client.request_spatula_is_holding(pb.Empty()))).value

  async def request_nest_is_holding(self, nest: int) -> bool:
    request = pb.NestRequest(nest=nest)
    return (await self._call(self.server.client.request_nest_is_holding(request))).value

  async def request_stacker_dimensions(self) -> List[StackerDimensions]:
    response = await self._call(self.server.client.request_stacker_dimensions(pb.Empty()))
    return [
      StackerDimensions(
        stacker=d.stacker,
        zero_offset=d.zero_offset,
        slot_height=d.slot_height,
        slot_count=d.slot_count,
      )
      for d in response.stackers
    ]

  async def request_settings(self) -> HighResSampleStorageSettings:
    response = await self._call(self.server.client.request_settings(pb.Empty()))
    return HighResSampleStorageSettings.from_lines(response.lines)

  async def request_stacker_barcodes(
    self, stacker: Union[int, Literal["all"]], slot: Optional[int] = None
  ) -> List[str]:
    request = pb.RequestStackerBarcodesRequest()
    if stacker == "all":
      request.all = True
    elif isinstance(stacker, int) and not isinstance(stacker, bool):
      request.number = stacker
    else:
      raise ValueError("stacker must be a positive integer or 'all'.")
    if slot is not None:
      request.slot = slot
    await self._send_placed()
    last = await self._stream(self.server.client.request_stacker_barcodes(request), "the scan")
    return list(last.lines.lines)

  # -- motion --

  async def home(self) -> None:
    await self._send_placed()
    await self._stream(self.server.client.home(pb.Empty()), "homing")

  async def request_is_parked(self) -> bool:
    return (await self._call(self.server.client.request_is_parked(pb.Empty()))).value

  async def recover(self) -> bool:
    await self._send_placed()
    return (await self._stream(self.server.client.recover(pb.Empty()), "the recovery")).value

  async def open_all_doors(self) -> None:
    await self._send_placed()
    await self._stream(self.server.client.open_all_doors(pb.Empty()), "opening the doors")

  async def close_all_doors(self) -> None:
    await self._send_placed()
    await self._stream(self.server.client.close_all_doors(pb.Empty()), "closing the doors")

  async def clear_abort(self) -> None:
    await self._call(self.server.client.clear_abort(pb.Empty()))

  # -- plates --

  async def resolve_unresolved_transfer(
    self, location: Literal["source", "destination", "unassigned"]
  ) -> Plate:
    if location not in _LOCATIONS:
      raise ValueError(
        f"location must be 'source', 'destination', or 'unassigned'; got {location!r}."
      )
    previous = self._unresolved_transfer
    request = pb.ResolveUnresolvedTransferRequest(location=_LOCATIONS[location])
    response = await self._call(self.server.client.resolve_unresolved_transfer(request))
    if previous is not None and previous.plate.name == response.plate:
      return previous.plate
    return self._plate_named(response.plate)

  async def fetch_plate_to_loading_tray(self, plate: Union[Plate, str], tray_index: int) -> Plate:
    name = plate if isinstance(plate, str) else plate.name
    request = pb.FetchPlateToLoadingTrayRequest(plate=_ref(name), tray_index=tray_index)
    await self._send_placed()
    last = await self._stream(self.server.client.fetch_plate_to_loading_tray(request), "the fetch")
    return self._plate_named(last.plate)

  async def take_in_plate(
    self,
    tray_index: int,
    site: Union[PlateHolder, Literal["random", "smallest"]] = "smallest",
  ) -> Plate:
    request = pb.TakeInPlateRequest(tray_index=tray_index)
    if isinstance(site, PlateHolder):
      request.holder.CopyFrom(_ref(site.name))
    elif site == "random":
      request.choice = pb.SITE_CHOICE_RANDOM
    elif site == "smallest":
      request.choice = pb.SITE_CHOICE_SMALLEST
    else:
      raise ValueError(f"Invalid site: {site!r}")
    await self._send_placed()
    last = await self._stream(self.server.client.take_in_plate(request), "the take-in")
    return self._plate_named(last.plate)

  async def store_plate(self, plate: Plate, site: PlateHolder, tray_index: int) -> None:
    request = pb.StorePlateRequest(
      plate=_ref(plate.name), site=_ref(site.name), tray_index=tray_index
    )
    await self._send_placed()
    await self._stream(self.server.client.store_plate(request), "the store")

  async def transfer_plate_between_nests(
    self, source_tray_index: int, destination_tray_index: int
  ) -> Plate:
    request = pb.TransferPlateBetweenNestsRequest(
      source_tray_index=source_tray_index, destination_tray_index=destination_tray_index
    )
    await self._send_placed()
    last = await self._stream(
      self.server.client.transfer_plate_between_nests(request), "the transfer"
    )
    return self._plate_named(last.plate)
