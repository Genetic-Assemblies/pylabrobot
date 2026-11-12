"""A Cytomat served elsewhere, driven as one in this process is.

`RemoteCytomatBackend` is a `CytomatBackend`: every public coroutine is a call to the server, so
`Incubator(backend=RemoteCytomatBackend("http://host:8092"), racks=..., ...)` drives the served
Cytomat as it drives one on this computer's serial port. The racks the `Incubator` is given are
sent to the server when it is set up; the plates stay this process's, and each call that takes one
says where it is.
"""

from __future__ import annotations

from typing import Any, List, Literal, Mapping, Optional, Union

from pyqwest import Client

from pylabrobot.legacy.storage.backend import IncubatorBackend
from pylabrobot.legacy.storage.cytomat import errors as cytomat_errors
from pylabrobot.legacy.storage.cytomat.constants import (
  ActionRegister,
  ActionType,
  CytomatIncupationResponse,
  CytomatType,
  ErrorRegister,
  LoadStatusAtProcessor,
  LoadStatusFrontOfGate,
  SwapStationPosition,
  WarningRegister,
)
from pylabrobot.legacy.storage.cytomat.cytomat import CytomatBackend
from pylabrobot.legacy.storage.cytomat.schemas import (
  ActionRegisterState,
  OverviewRegisterState,
  SensorStates,
  SwapStationState,
)
from pylabrobot.legacy.storage.cytomat.server.serve import cytomat_server_app
from pylabrobot.legacy.storage.cytomat.server.v1 import cytomat_pb2 as pb
from pylabrobot.legacy.storage.cytomat.server.v1.cytomat_connect import CytomatServiceClient
from pylabrobot.legacy.storage.server.errors import ErrorClasses, exception_classes
from pylabrobot.legacy.storage.server.remote import (
  BackendServer,
  plate_message,
  racks_request,
  site_ref,
)
from pylabrobot.legacy.storage.server.v1 import incubator_pb2 as ipb
from pylabrobot.resources import Plate, PlateCarrier, PlateHolder, ResourceNotFoundError
from pylabrobot.resources.server.asgi_transport import ASGITransport
from pylabrobot.resources.server.client import _Headers

# The address a Cytomat server held in this process is spoken to at; never dialled.
_IN_PROCESS = "http://cytomat.in-process"

_ERRORS = ErrorClasses([*exception_classes(vars(cytomat_errors)), ResourceNotFoundError])


def overview_state(message: pb.OverviewRegister) -> OverviewRegisterState:
  return OverviewRegisterState(
    transfer_station_occupied=message.transfer_station_occupied,
    device_door_open=message.device_door_open,
    automatic_gate_open=message.automatic_gate_open,
    handler_occupied=message.handler_occupied,
    error_register_set=message.error_register_set,
    warning_register_set=message.warning_register_set,
    ready_bit_set=message.ready_bit_set,
    busy_bit_set=message.busy_bit_set,
  )


class CytomatServer(BackendServer[CytomatServiceClient]):
  """A Cytomat server: where a Cytomat is served, and how its calls get there.

  `connect` reaches one served elsewhere; `local` serves a backend in this process, without a
  socket, as tests do.
  """

  def __init__(
    self, address: str, http: Optional[Client] = None, headers: Optional[Mapping[str, str]] = None
  ):
    interceptors = [_Headers(headers)] if headers else []
    client = CytomatServiceClient(address, http_client=http, interceptors=interceptors)
    super().__init__(address, client, _ERRORS)

  @classmethod
  def connect(cls, url: str, headers: Optional[Mapping[str, str]] = None) -> CytomatServer:
    """A Cytomat server at `url`, "http://127.0.0.1:8092" say.

    Args:
      headers: sent with every call: the credentials the server asks for.
    """
    return cls(url, Client(), headers=headers)

  @classmethod
  def local(cls, backend: CytomatBackend) -> CytomatServer:
    """A backend served in this process, spoken to over Connect without a socket."""
    return cls(_IN_PROCESS, Client(transport=ASGITransport(cytomat_server_app(backend))))


def _server(server: Union[str, CytomatServer]) -> CytomatServer:
  return CytomatServer.connect(server) if isinstance(server, str) else server


class RemoteCytomatBackend(CytomatBackend):
  """The Cytomat a Cytomat server serves: every public coroutine is a call to it.

  Attributes:
    model: the server's, known once setup has run.
  """

  def __init__(
    self,
    cytomat_server: Union[str, CytomatServer],
    model: Union[CytomatType, str, None] = None,
  ):
    """
    Args:
      cytomat_server: the server, or its URL.
      model: the Cytomat it must be; setup refuses a server serving another.
    """
    IncubatorBackend.__init__(self)
    self.server = _server(cytomat_server)
    self._expected = CytomatType(model) if isinstance(model, str) else model
    self.model = self._expected  # type: ignore[assignment]
    self._racks: List[PlateCarrier] = []

  def serialize(self) -> dict:
    return {
      "type": type(self).__name__,
      "cytomat_server": self.server.address,
      "model": None if self.model is None else self.model.value,
    }

  async def _move(self, response: Any, what: str) -> OverviewRegisterState:
    last = await self.server.stream(response, what)
    if not last.HasField("overview"):
      raise ConnectionError(f"the Cytomat server did not say how {what} left the Cytomat")
    return overview_state(last.overview)

  def _site(self, site: PlateHolder) -> ipb.SiteRequest:
    return ipb.SiteRequest(site=site_ref(site))

  # -- lifecycle --

  async def setup(self):
    await self.server.stream(self.server.client.setup(ipb.Empty()), "the setup")
    description = await self.server.call(self.server.client.describe(ipb.Empty()))
    model = CytomatType(description.model)
    if self._expected is not None and model != self._expected:
      raise ValueError(f"the server serves a {model.value}, not a {self._expected.value}")
    self.model = model

  async def set_racks(self, racks: List[PlateCarrier]):
    await IncubatorBackend.set_racks(self, racks)
    await self.server.call(self.server.client.set_racks(racks_request(racks)))

  async def stop(self):
    await self.server.call(self.server.client.stop(ipb.Empty()))

  # -- commands and registers --

  async def send_command(self, command_type: str, command: str, params: str) -> str:
    request = pb.SendCommandRequest(command_type=command_type, command=command, params=params)
    return (await self.server.call(self.server.client.send_command(request))).value

  async def send_action(
    self, command_type: str, command: str, params: str, timeout: Optional[int] = 60
  ) -> OverviewRegisterState:
    request = pb.SendActionRequest(command_type=command_type, command=command, params=params)
    request.timeout.SetInParent()
    if timeout is not None:
      request.timeout.value = timeout
    return await self._move(self.server.client.send_action(request), "the action")

  async def get_overview_register(self) -> OverviewRegisterState:
    response = await self.server.call(self.server.client.get_overview_register(ipb.Empty()))
    return overview_state(response)

  async def get_warning_register(self) -> WarningRegister:
    response = await self.server.call(self.server.client.get_warning_register(ipb.Empty()))
    return WarningRegister(response.value)

  async def get_error_register(self) -> ErrorRegister:
    response = await self.server.call(self.server.client.get_error_register(ipb.Empty()))
    return ErrorRegister(response.value)

  async def reset_error_register(self) -> None:
    await self.server.call(self.server.client.reset_error_register(ipb.Empty()))

  async def initialize(self) -> None:
    await self.server.stream(self.server.client.initialize(ipb.Empty()), "the initialization")

  async def open_door(self):
    return await self._move(self.server.client.open_door(ipb.Empty()), "opening the door")

  async def close_door(self):
    return await self._move(self.server.client.close_door(ipb.Empty()), "closing the door")

  async def shovel_in(self):
    return await self._move(self.server.client.shovel_in(ipb.Empty()), "the shovel")

  async def shovel_out(self):
    return await self._move(self.server.client.shovel_out(ipb.Empty()), "the shovel")

  async def get_action_register(self) -> ActionRegisterState:
    response = await self.server.call(self.server.client.get_action_register(ipb.Empty()))
    return ActionRegisterState(
      target=ActionType(response.target), action=ActionRegister(response.action)
    )

  async def get_swap_register(self) -> SwapStationState:
    response = await self.server.call(self.server.client.get_swap_register(ipb.Empty()))
    return SwapStationState(
      position=SwapStationPosition(response.position),
      load_status_front_of_gate=LoadStatusFrontOfGate(response.load_status_front_of_gate),
      load_status_at_processor=LoadStatusAtProcessor(response.load_status_at_processor),
    )

  async def get_sensor_register(self) -> SensorStates:
    response = await self.server.call(self.server.client.get_sensor_register(ipb.Empty()))
    return SensorStates(**dict(response.states))

  # -- moves --

  async def action_transfer_to_storage(self, site: PlateHolder) -> OverviewRegisterState:
    response = self.server.client.action_transfer_to_storage(self._site(site))
    return await self._move(response, "the move")

  async def action_storage_to_transfer(self, site: PlateHolder) -> OverviewRegisterState:
    response = self.server.client.action_storage_to_transfer(self._site(site))
    return await self._move(response, "the move")

  async def action_storage_to_wait(self, site: PlateHolder) -> OverviewRegisterState:
    response = self.server.client.action_storage_to_wait(self._site(site))
    return await self._move(response, "the move")

  async def action_wait_to_storage(self, site: PlateHolder) -> OverviewRegisterState:
    response = self.server.client.action_wait_to_storage(self._site(site))
    return await self._move(response, "the move")

  async def action_wait_to_transfer(self) -> OverviewRegisterState:
    response = self.server.client.action_wait_to_transfer(ipb.Empty())
    return await self._move(response, "the move")

  async def action_transfer_to_wait(self) -> OverviewRegisterState:
    response = self.server.client.action_transfer_to_wait(ipb.Empty())
    return await self._move(response, "the move")

  async def action_wait_to_exposed(self) -> OverviewRegisterState:
    response = self.server.client.action_wait_to_exposed(ipb.Empty())
    return await self._move(response, "the move")

  async def action_exposed_to_wait(self) -> OverviewRegisterState:
    response = self.server.client.action_exposed_to_wait(ipb.Empty())
    return await self._move(response, "the move")

  async def action_exposed_to_storage(self, site: PlateHolder) -> OverviewRegisterState:
    response = self.server.client.action_exposed_to_storage(self._site(site))
    return await self._move(response, "the move")

  async def action_storage_to_exposed(self, site: PlateHolder) -> OverviewRegisterState:
    response = self.server.client.action_storage_to_exposed(self._site(site))
    return await self._move(response, "the move")

  async def action_read_barcode(
    self,
    site_number_a: str,
    site_number_b: str,
  ) -> OverviewRegisterState:
    request = pb.ReadBarcodeRequest(site_number_a=site_number_a, site_number_b=site_number_b)
    return overview_state(await self.server.call(self.server.client.action_read_barcode(request)))

  async def wait_for_transfer_station(self, occupied: bool = False):
    request = pb.WaitForTransferStationRequest(occupied=occupied)
    await self.server.stream(
      self.server.client.wait_for_transfer_station(request), "the wait for the transfer station"
    )

  async def wait_for_task_completion(self, timeout=60) -> OverviewRegisterState:
    request = pb.WaitForTaskCompletionRequest(timeout=timeout)
    return await self._move(self.server.client.wait_for_task_completion(request), "the wait")

  # -- shaking --

  async def init_shakers(self):
    return (await self.server.call(self.server.client.init_shakers(ipb.Empty()))).value

  async def start_shaking(self, frequency: float, shakers: Optional[List[int]] = None):
    request = pb.StartShakingRequest(frequency=frequency)
    if shakers is not None:
      request.shakers.shakers.extend(shakers)
      request.shakers.SetInParent()
    return (await self.server.call(self.server.client.start_shaking(request))).value

  async def stop_shaking(self):
    return (await self.server.call(self.server.client.stop_shaking(ipb.Empty()))).value

  async def set_shaking_frequency(
    self, frequency: int, shakers: Optional[List[int]] = None
  ) -> List[str]:
    request = pb.SetShakingFrequencyRequest(frequency=frequency)
    if shakers is not None:
      request.shakers.shakers.extend(shakers)
      request.shakers.SetInParent()
    return list((await self.server.call(self.server.client.set_shaking_frequency(request))).values)

  # -- climate --

  async def get_incubation_query(
    self, query: Literal["ic", "ih", "io", "it"]
  ) -> CytomatIncupationResponse:
    request = pb.IncubationQueryRequest(query=query)
    response = await self.server.call(self.server.client.get_incubation_query(request))
    return CytomatIncupationResponse(
      nominal_value=response.nominal_value, actual_value=response.actual_value
    )

  async def _incubation(self, response: Any) -> CytomatIncupationResponse:
    message = await self.server.call(response)
    return CytomatIncupationResponse(
      nominal_value=message.nominal_value, actual_value=message.actual_value
    )

  async def get_co2(self) -> CytomatIncupationResponse:
    return await self._incubation(self.server.client.get_co2(ipb.Empty()))

  async def get_humidity(self) -> CytomatIncupationResponse:
    return await self._incubation(self.server.client.get_humidity(ipb.Empty()))

  async def get_o2(self) -> CytomatIncupationResponse:
    return await self._incubation(self.server.client.get_o2(ipb.Empty()))

  async def get_temperature(self) -> float:
    return (await self.server.call(self.server.client.get_temperature(ipb.Empty()))).value

  async def set_temperature(self, *args, **kwargs):
    temperature = args[0] if args else kwargs.get("temperature", 0.0)
    request = pb.SetTemperatureRequest(temperature=temperature)
    await self.server.call(self.server.client.set_temperature(request))

  # -- plates --

  async def fetch_plate_to_loading_tray(self, plate: Plate, **backend_kwargs):
    request = pb.PlateRequest(plate=plate_message(plate, self._racks))
    await self.server.stream(self.server.client.fetch_plate_to_loading_tray(request), "the fetch")

  async def take_in_plate(self, plate: Plate, site: PlateHolder, **backend_kwargs):
    request = pb.TakeInPlateRequest(plate=plate_message(plate, self._racks), site=site_ref(site))
    await self.server.stream(self.server.client.take_in_plate(request), "the take-in")
