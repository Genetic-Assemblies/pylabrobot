"""Serving a HighRes sample store: one Connect application for one store.

The store is the driver PLR has, `TundraStore` say, and its resource tree is the server's: where
each plate is. A client names a plate, slot or nest by name in that tree, and tells the server
what it did to the tree by hand (`PlacePlates`), as the robot that loads a nest does.

A long call (a plate move, homing, a door) streams its progress every few seconds, so nothing
between the server and a client sees an idle call and cuts it, and it finishes on the server even
if the client goes away: a plate move is not left half done.
"""

import asyncio
import hashlib
import json
import time
from typing import (
  Any,
  AsyncIterator,
  Awaitable,
  Callable,
  Dict,
  Literal,
  Optional,
  Set,
  TypeVar,
  Union,
)

from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext

from pylabrobot.high_res.sample_storage.driver import HighResSampleStorage
from pylabrobot.high_res.sample_storage.driver.environment import EnvironmentControl
from pylabrobot.high_res.sample_storage.driver.types import (
  DoorState,
  EnvironmentParameter,
  NestState,
)
from pylabrobot.high_res.sample_storage.server.errors import to_connect_error
from pylabrobot.high_res.sample_storage.server.v1 import sample_storage_pb2 as pb
from pylabrobot.high_res.sample_storage.server.v1.sample_storage_connect import (
  SampleStorageServiceASGIApplication,
)
from pylabrobot.high_res.sample_storage.simulator import SampleStorageSimulator
from pylabrobot.resources import (
  Coordinate,
  Plate,
  PlateCarrier,
  PlateHolder,
  Resource,
  ResourceNotFoundError,
  Well,
)
from pylabrobot.resources.server.v1 import types_pb2 as tpb

# An ASGI 3 application.
ASGIApp = Callable[[Dict[str, Any], Any, Any], Awaitable[None]]

# The response header that says which description of the store is current.
REVISION_HEADER = "sample-storage-description-revision"

# How often a long call says how far it has got, in seconds.
PROGRESS_INTERVAL = 5.0

T = TypeVar("T")
Ctx = RequestContext[Any, Any]

DOOR_STATES: Dict[str, "pb.DoorState"] = {
  "open": pb.DOOR_STATE_OPEN,
  "closed": pb.DOOR_STATE_CLOSED,
  "opening": pb.DOOR_STATE_OPENING,
  "closing": pb.DOOR_STATE_CLOSING,
  "unknown": pb.DOOR_STATE_UNKNOWN,
}
NEST_STATES: Dict[str, "pb.NestState"] = {
  "clear": pb.NEST_STATE_CLEAR,
  "occupied": pb.NEST_STATE_OCCUPIED,
  "unknown": pb.NEST_STATE_UNKNOWN,
}
LOCATIONS: Dict[int, Literal["source", "destination", "unassigned"]] = {
  pb.TRANSFER_LOCATION_SOURCE: "source",
  pb.TRANSFER_LOCATION_DESTINATION: "destination",
  pb.TRANSFER_LOCATION_UNASSIGNED: "unassigned",
}

# The footprint of an SBS plate, in mm.
_PLATE_X = 127.76
_PLATE_Y = 85.48


def rack_definition(rack: PlateCarrier) -> str:
  """A stacker as PLR serializes it, without the plates in it."""
  data = rack.serialize()
  for site in data.get("children", []):
    site.pop("children", None)
  return json.dumps(data)


def make_plate(definition: pb.PlateDefinition) -> Plate:
  """The plate a definition says: as PLR serialized it, or one of its name with one well."""
  if definition.definition:
    plate = Resource.deserialize(json.loads(definition.definition))
    if not isinstance(plate, Plate):
      raise ValueError(f"'{definition.name}' is a {type(plate).__name__}, not a plate")
    if plate.name != definition.name:
      raise ValueError(f"the definition of '{definition.name}' is of '{plate.name}'")
    return plate
  size_z = definition.size_z if definition.HasField("size_z") else 0.0
  well = Well(name=f"{definition.name}_A1", size_x=1, size_y=1, size_z=1).at(Coordinate(0, 0, 0))
  return Plate(
    name=definition.name,
    size_x=_PLATE_X,
    size_y=_PLATE_Y,
    size_z=size_z,
    ordered_items={"A1": well},
  )


def _parameter(parameter: EnvironmentParameter) -> pb.EnvironmentParameter:
  message = pb.EnvironmentParameter(name=parameter.name, current=parameter.current)
  if parameter.setpoint is not None:
    message.setpoint = parameter.setpoint
  if parameter.limit is not None:
    message.limit = parameter.limit
  return message


def _environment(parameters: Dict[str, EnvironmentParameter]) -> pb.Environment:
  return pb.Environment(parameters={k: _parameter(v) for k, v in parameters.items()})


def _doors(doors: Dict[str, DoorState]) -> pb.Doors:
  return pb.Doors(doors={k: DOOR_STATES[v] for k, v in doors.items()})


def _nests(nests: Dict[int, NestState]) -> pb.NestStates:
  return pb.NestStates(nests={k: NEST_STATES[v] for k, v in nests.items()})


class _Served:
  """One store, each call made on it."""

  def __init__(self, store: HighResSampleStorage, set_up: bool = False):
    self.store = store
    # Whether the store has been set up; `Setup` sets it up only when it has not.
    self.set_up = set_up
    # Calls that keep running when their client has gone, held so they are not collected.
    self._running: Set["asyncio.Task[Any]"] = set()
    self._digest: Optional[bytes] = None
    self.revision = 0

  # -- the tree --

  def description(self) -> pb.Description:
    store = self.store
    response = pb.Description(
      name=store.name,
      model=store.model or "",
      read_timeout=store.read_timeout,
      motion_timeout=store.motion_timeout,
    )
    for number, rack in sorted(store._racks_by_number.items()):
      stacker = response.stackers.add(
        number=number, name=rack.name, definition=rack_definition(rack)
      )
      for spot, site in sorted(rack.sites.items()):
        described = stacker.sites.add(name=site.name, slot=spot + 1, size_z=site.get_size_z())
        if site.resource is not None:
          described.plate = site.resource.name
    for tray_index, nest in enumerate(store.nests):
      described_nest = response.nests.add(
        tray_index=tray_index, number=tray_index + 1, name=nest.name
      )
      if nest.resource is not None:
        described_nest.plate = nest.resource.name
    transfer = store.unresolved_transfer
    if transfer is not None:
      response.unresolved_transfer.CopyFrom(
        pb.UnresolvedTransfer(
          plate=transfer.plate.name,
          source=transfer.source.name,
          destination=transfer.destination.name,
          command=transfer.command,
          error_type=transfer.error_type,
          error_message=transfer.error_message,
        )
      )
    if store.model_info.has_environment_control:
      response.environment.CopyFrom(_environment(store.environment.parameters))
    return response

  def _stamp(self, ctx: Ctx) -> None:
    """Say which description is current, moving the revision on when it changed."""
    digest = hashlib.sha256(self.description().SerializeToString(deterministic=True)).digest()
    if digest != self._digest:
      self._digest = digest
      self.revision += 1
    ctx.response_headers[REVISION_HEADER] = str(self.revision)

  def resolve(self, ref: tpb.ResourceRef) -> Resource:
    """The resource of the store's tree a reference names.

    Raises:
      ValueError: If it is not a reference by name, or names another root.
      ResourceNotFoundError: If the tree has no resource of that name.
    """
    if ref.WhichOneof("ref") != "name":
      raise ValueError("this server names resources by name: give a NameRef")
    if ref.name.root not in ("", self.store.name):
      raise ValueError(f"'{ref.name.root}' is not this server's store, '{self.store.name}'")
    if ref.name.name == self.store.name:
      return self.store
    return self.store.get_resource(ref.name.name)

  def _plate(self, ref: tpb.ResourceRef) -> Plate:
    plate = self.resolve(ref)
    if not isinstance(plate, Plate):
      raise ValueError(f"'{plate.name}' is a {type(plate).__name__}, not a plate")
    return plate

  def _holder(self, ref: tpb.ResourceRef) -> PlateHolder:
    holder = self.resolve(ref)
    racks = self.store.racks
    if not isinstance(holder, PlateHolder) or not (
      holder in self.store.nests or holder.parent in racks
    ):
      raise ValueError(f"'{holder.name}' is not a nest or a stacker slot of '{self.store.name}'")
    return holder

  def _sense(self, holder: PlateHolder) -> None:
    """Make a simulated store hold a plate where the tree now says it does."""
    simulator = self.store.io
    if not isinstance(simulator, SampleStorageSimulator):
      return
    held = holder.resource is not None
    if holder in self.store.nests:
      simulator.nests[self.store.nests.index(holder) + 1] = held
      return
    where = self.store._locate(holder)
    (simulator.slots.add if held else simulator.slots.discard)(where)

  def place(self, placement: pb.Placement) -> None:
    holder = self._holder(placement.holder)
    current = holder.resource
    if not placement.HasField("plate"):
      if current is not None:
        current.unassign()
      self._sense(holder)
      return
    name = placement.plate.name
    if current is not None:
      if current.name == name:
        return
      raise ValueError(f"'{holder.name}' holds '{current.name}': take it away first")
    try:
      plate: Optional[Resource] = self.store.get_resource(name)
    except ResourceNotFoundError:
      plate = None
    if plate is not None:
      if not isinstance(plate, Plate):
        raise ValueError(f"'{name}' is a {type(plate).__name__}, not a plate")
      previous = plate.parent
      plate.unassign()
      if isinstance(previous, PlateHolder):
        self._sense(previous)
    else:
      plate = make_plate(placement.plate)
    holder.assign_child_resource(plate)
    self._sense(holder)

  # -- calls --

  async def _call(self, ctx: Ctx, call: Callable[[], Awaitable[T]]) -> T:
    """Make a call on the store, raising what it raised as a Connect error."""
    try:
      return await call()
    except ConnectError:
      raise
    except Exception as error:
      raise to_connect_error(error) from error
    finally:
      self._stamp(ctx)

  async def _stream(
    self,
    ctx: Ctx,
    call: Callable[[], Awaitable[T]],
    result: Callable[[T, pb.Progress], None] = lambda _, __: None,
    finish_without_client: bool = True,
  ) -> AsyncIterator[pb.Progress]:
    """Make a long call, saying how far it has got every `PROGRESS_INTERVAL` seconds, and when it
    is done, with what it returned.

    Args:
      result: puts what the call returned in the last progress.
      finish_without_client: whether the call runs on when the client goes away.
    """
    self._stamp(ctx)
    start = time.monotonic()
    task = asyncio.ensure_future(call())
    try:
      while True:
        done, _ = await asyncio.wait({task}, timeout=PROGRESS_INTERVAL)
        if done:
          break
        yield pb.Progress(elapsed=time.monotonic() - start)
      try:
        value = task.result()
      except Exception as error:
        raise to_connect_error(error) from error
      finally:
        self._stamp(ctx)
      last = pb.Progress(elapsed=time.monotonic() - start, done=True)
      result(value, last)
      yield last
    finally:
      if not task.done():
        if finish_without_client:
          self._running.add(task)
          task.add_done_callback(self._running.discard)
        else:
          task.cancel()

  def _environment(self) -> EnvironmentControl:
    if not self.store.model_info.has_environment_control:
      raise NotImplementedError(f"{self.store.model} has no environment control")
    return self.store.environment

  async def _env(self, ctx: Ctx, call: Callable[[EnvironmentControl], Awaitable[T]]) -> T:
    return await self._call(ctx, lambda: call(self._environment()))

  # -- the service: the tree --

  async def describe(self, request: pb.Empty, ctx: Ctx) -> pb.Description:
    self._stamp(ctx)
    return self.description()

  async def place_plates(self, request: pb.PlacePlatesRequest, ctx: Ctx) -> pb.Empty:
    async def place() -> None:
      for placement in request.placements:
        self.place(placement)

    await self._call(ctx, place)
    return pb.Empty()

  async def get_plate(self, request: tpb.ResourceRef, ctx: Ctx) -> pb.PlateDefinition:
    async def get() -> pb.PlateDefinition:
      plate = self._plate(request)
      return pb.PlateDefinition(name=plate.name, definition=json.dumps(plate.serialize()))

    return await self._call(ctx, get)

  # -- the service: the device --

  def setup(self, request: pb.SetupRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    home = request.home if request.HasField("home") else False

    async def setup() -> None:
      if not self.set_up:
        await self.store.setup(home=home)
        self.set_up = True
      elif home:
        await self.store.home()

    return self._stream(ctx, setup)

  async def stop(self, request: pb.Empty, ctx: Ctx) -> pb.Empty:
    async def stop() -> None:
      self.set_up = False
      await self.store.stop()

    await self._call(ctx, stop)
    return pb.Empty()

  async def request_version(self, request: pb.Empty, ctx: Ctx) -> pb.Version:
    version = await self._call(ctx, self.store.request_version)
    response = pb.Version(raw=version.raw)
    for field in ("product_name", "serial_number", "firmware_version", "firmware_build"):
      value = getattr(version, field)
      if value is not None:
        setattr(response, field, value)
    return response

  async def request_environment(self, request: pb.Empty, ctx: Ctx) -> pb.Environment:
    return _environment(await self._call(ctx, self.store.request_environment))

  async def request_axis_positions(self, request: pb.Empty, ctx: Ctx) -> pb.AxisPositions:
    return pb.AxisPositions(positions=await self._call(ctx, self.store.request_axis_positions))

  async def request_is_homed(self, request: pb.Empty, ctx: Ctx) -> pb.Flag:
    return pb.Flag(value=await self._call(ctx, self.store.request_is_homed))

  async def request_door_status(self, request: pb.Empty, ctx: Ctx) -> pb.Doors:
    return _doors(await self._call(ctx, self.store.request_door_status))

  async def request_nest_status(self, request: pb.Empty, ctx: Ctx) -> pb.NestStates:
    return _nests(await self._call(ctx, self.store.request_nest_status))

  async def request_spatula_is_holding(self, request: pb.Empty, ctx: Ctx) -> pb.Flag:
    return pb.Flag(value=await self._call(ctx, self.store.request_spatula_is_holding))

  async def request_nest_is_holding(self, request: pb.NestRequest, ctx: Ctx) -> pb.Flag:
    held = await self._call(ctx, lambda: self.store.request_nest_is_holding(request.nest))
    return pb.Flag(value=held)

  async def request_stacker_dimensions(
    self, request: pb.Empty, ctx: Ctx
  ) -> pb.StackerDimensionsList:
    dimensions = await self._call(ctx, self.store.request_stacker_dimensions)
    return pb.StackerDimensionsList(
      stackers=[
        pb.StackerDimensions(
          stacker=d.stacker,
          zero_offset=d.zero_offset,
          slot_height=d.slot_height,
          slot_count=d.slot_count,
        )
        for d in dimensions
      ]
    )

  async def request_settings(self, request: pb.Empty, ctx: Ctx) -> pb.Lines:
    settings = await self._call(ctx, self.store.request_settings)
    return pb.Lines(lines=[f"{key} = {value}" for key, value in settings.raw.items()])

  def request_stacker_barcodes(
    self, request: pb.RequestStackerBarcodesRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    stacker: Union[int, Literal["all"]] = (
      "all" if request.WhichOneof("stacker") == "all" else request.number
    )
    slot = request.slot if request.HasField("slot") else None
    return self._stream(
      ctx,
      lambda: self.store.request_stacker_barcodes(stacker, slot),
      lambda lines, last: last.lines.lines.extend(lines),
    )

  def home(self, request: pb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(ctx, self.store.home)

  async def request_is_parked(self, request: pb.Empty, ctx: Ctx) -> pb.Flag:
    return pb.Flag(value=await self._call(ctx, self.store.request_is_parked))

  def recover(self, request: pb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(
      ctx, self.store.recover, lambda parked, last: setattr(last, "value", parked)
    )

  def open_all_doors(self, request: pb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(ctx, self.store.open_all_doors)

  def close_all_doors(self, request: pb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(ctx, self.store.close_all_doors)

  async def clear_abort(self, request: pb.Empty, ctx: Ctx) -> pb.Empty:
    await self._call(ctx, self.store.clear_abort)
    return pb.Empty()

  async def resolve_unresolved_transfer(
    self, request: pb.ResolveUnresolvedTransferRequest, ctx: Ctx
  ) -> pb.PlateName:
    async def resolve() -> Plate:
      location = LOCATIONS.get(request.location)
      if location is None:
        raise ValueError("location must be source, destination or unassigned")
      plate = await self.store.resolve_unresolved_transfer(location)
      for holder in [*self.store.nests, *(s for r in self.store.racks for s in r.sites.values())]:
        self._sense(holder)
      return plate

    plate = await self._call(ctx, resolve)
    return pb.PlateName(plate=plate.name)

  @staticmethod
  def _moved(plate: Plate, last: pb.Progress) -> None:
    last.plate = plate.name

  def fetch_plate_to_loading_tray(
    self, request: pb.FetchPlateToLoadingTrayRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    async def fetch() -> Plate:
      # A name the tree does not have goes to the store as a name, which it reports as it does.
      plate: Union[Plate, str]
      try:
        plate = self._plate(request.plate)
      except ResourceNotFoundError:
        plate = request.plate.name.name
      return await self.store.fetch_plate_to_loading_tray(plate, request.tray_index)

    return self._stream(ctx, fetch, self._moved)

  def take_in_plate(self, request: pb.TakeInPlateRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    async def take_in() -> Plate:
      site: Union[PlateHolder, Literal["random", "smallest"]] = "smallest"
      if request.WhichOneof("site") == "holder":
        site = self._holder(request.holder)
      elif request.WhichOneof("site") == "choice" and request.choice == pb.SITE_CHOICE_RANDOM:
        site = "random"
      return await self.store.take_in_plate(request.tray_index, site)

    return self._stream(ctx, take_in, self._moved)

  def store_plate(self, request: pb.StorePlateRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    async def store() -> Plate:
      plate = self._plate(request.plate)
      await self.store.store_plate(plate, self._holder(request.site), request.tray_index)
      return plate

    return self._stream(ctx, store, self._moved)

  def transfer_plate_between_nests(
    self, request: pb.TransferPlateBetweenNestsRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._stream(
      ctx,
      lambda: self.store.transfer_plate_between_nests(
        request.source_tray_index, request.destination_tray_index
      ),
      self._moved,
    )

  # -- the service: the environment --

  async def refresh(self, request: pb.Empty, ctx: Ctx) -> pb.Environment:
    return _environment(await self._env(ctx, lambda e: e.refresh()))

  async def request_current_temperature(self, request: pb.Empty, ctx: Ctx) -> pb.Value:
    return pb.Value(value=await self._env(ctx, lambda e: e.request_current_temperature()))

  async def request_target_temperature(self, request: pb.Empty, ctx: Ctx) -> pb.Value:
    return pb.Value(value=await self._env(ctx, lambda e: e.request_target_temperature()))

  async def set_temperature(self, request: pb.Temperature, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.set_temperature(request.temperature))
    return pb.Empty()

  async def start_temperature_control(self, request: pb.Empty, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.start_temperature_control())
    return pb.Empty()

  async def stop_temperature_control(self, request: pb.Empty, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.stop_temperature_control())
    return pb.Empty()

  async def request_current_humidity(self, request: pb.Empty, ctx: Ctx) -> pb.Value:
    return pb.Value(value=await self._env(ctx, lambda e: e.request_current_humidity()))

  async def request_target_humidity(self, request: pb.Empty, ctx: Ctx) -> pb.Value:
    return pb.Value(value=await self._env(ctx, lambda e: e.request_target_humidity()))

  async def set_humidity(self, request: pb.Humidity, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.set_humidity(request.humidity))
    return pb.Empty()

  async def start_humidity_control(self, request: pb.Empty, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.start_humidity_control())
    return pb.Empty()

  async def stop_humidity_control(self, request: pb.Empty, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.stop_humidity_control())
    return pb.Empty()

  async def request_current_co2(self, request: pb.Empty, ctx: Ctx) -> pb.Value:
    return pb.Value(value=await self._env(ctx, lambda e: e.request_current_co2()))

  async def request_target_co2(self, request: pb.Empty, ctx: Ctx) -> pb.Value:
    return pb.Value(value=await self._env(ctx, lambda e: e.request_target_co2()))

  async def set_co2(self, request: pb.Co2, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.set_co2(request.co2))
    return pb.Empty()

  async def start_co2_control(self, request: pb.Empty, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.start_co2_control())
    return pb.Empty()

  async def stop_co2_control(self, request: pb.Empty, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.stop_co2_control())
    return pb.Empty()

  async def request_current_o2(self, request: pb.Empty, ctx: Ctx) -> pb.Value:
    return pb.Value(value=await self._env(ctx, lambda e: e.request_current_o2()))

  async def request_target_o2(self, request: pb.Empty, ctx: Ctx) -> pb.Value:
    return pb.Value(value=await self._env(ctx, lambda e: e.request_target_o2()))

  async def set_o2(self, request: pb.O2, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.set_o2(request.o2))
    return pb.Empty()

  async def start_o2_control(self, request: pb.Empty, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.start_o2_control())
    return pb.Empty()

  async def stop_o2_control(self, request: pb.Empty, ctx: Ctx) -> pb.Empty:
    await self._env(ctx, lambda e: e.stop_o2_control())
    return pb.Empty()

  async def request_tank_pressures(self, request: pb.Empty, ctx: Ctx) -> pb.Pressures:
    return pb.Pressures(pressures=await self._env(ctx, lambda e: e.request_tank_pressures()))


def sample_storage_server_app(store: HighResSampleStorage, set_up: bool = False) -> ASGIApp:
  """One ASGI application serving a store.

  Args:
    set_up: whether the store has been set up already, so a client's `setup` does not set it up
      again.
  """
  return SampleStorageServiceASGIApplication(_Served(store, set_up=set_up))


async def serve(
  store: HighResSampleStorage, host: str = "127.0.0.1", port: int = 8091, set_up: bool = False
) -> None:
  """Serve a store until cancelled. Needs uvicorn, the `resource-server` extra.

  Args:
    store: the store to serve.
    host: the address to listen on.
    port: the port to listen on.
    set_up: as `sample_storage_server_app` takes it.
  """
  import uvicorn

  await uvicorn.Server(
    uvicorn.Config(sample_storage_server_app(store, set_up=set_up), host=host, port=port)
  ).serve()
