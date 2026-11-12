"""Serving a Cytomat: one Connect application for one `CytomatBackend`.

A move (any of the firmware's, a fetch, a take-in, a door) streams its progress every few seconds
and finishes on the server even if its client goes away; a wait for the transfer station or a
task is dropped when its client goes. See `pylabrobot.legacy.storage.server.served` for how sites
and plates are named, and how calls from several clients share the serial port.
"""

from typing import Any, AsyncIterator, Awaitable, Callable, List, Optional, TypeVar

from connectrpc.request import RequestContext

from pylabrobot.legacy.storage.cytomat.cytomat import CytomatBackend
from pylabrobot.legacy.storage.cytomat.schemas import OverviewRegisterState
from pylabrobot.legacy.storage.cytomat.server.v1 import cytomat_pb2 as pb
from pylabrobot.legacy.storage.cytomat.server.v1.cytomat_connect import (
  CytomatServiceASGIApplication,
)
from pylabrobot.legacy.storage.server.served import ASGIApp, ServedBackend, describe_racks
from pylabrobot.legacy.storage.server.v1 import incubator_pb2 as ipb

T = TypeVar("T")
Ctx = RequestContext[Any, Any]


def overview(state: OverviewRegisterState) -> pb.OverviewRegister:
  return pb.OverviewRegister(
    transfer_station_occupied=state.transfer_station_occupied,
    device_door_open=state.device_door_open,
    automatic_gate_open=state.automatic_gate_open,
    handler_occupied=state.handler_occupied,
    error_register_set=state.error_register_set,
    warning_register_set=state.warning_register_set,
    ready_bit_set=state.ready_bit_set,
    busy_bit_set=state.busy_bit_set,
  )


def _with_overview(state: Optional[OverviewRegisterState], last: pb.Progress) -> None:
  if state is not None:
    last.overview.CopyFrom(overview(state))


def _shakers(message: pb.Shakers, given: bool) -> Optional[List[int]]:
  return list(message.shakers) if given else None


class _Served(ServedBackend):
  """One Cytomat, each call made on it."""

  def __init__(self, backend: CytomatBackend):
    super().__init__(backend, io="send_command")
    self.cytomat = backend

  def _move(
    self, work: Callable[[], Awaitable[Optional[OverviewRegisterState]]]
  ) -> AsyncIterator[pb.Progress]:
    return self.stream(work, pb.Progress, _with_overview)

  def _site_move(
    self,
    request: ipb.SiteRequest,
    action: Callable[..., Awaitable[OverviewRegisterState]],
  ) -> AsyncIterator[pb.Progress]:
    return self._move(lambda: action(self.site(request.site)))

  # -- the backend --

  async def describe(self, request: ipb.Empty, ctx: Ctx) -> pb.Description:
    return pb.Description(model=self.cytomat.model.value, racks=describe_racks(self.racks))

  def setup(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self.stream(self.cytomat.setup, pb.Progress)

  async def stop(self, request: ipb.Empty, ctx: Ctx) -> ipb.Empty:
    await self.call(self.cytomat.stop)
    return ipb.Empty()

  async def set_racks(self, request: ipb.SetRacksRequest, ctx: Ctx) -> ipb.Empty:
    await self.call(lambda: self.take_racks(request))
    return ipb.Empty()

  async def send_command(self, request: pb.SendCommandRequest, ctx: Ctx) -> ipb.Text:
    reply = await self.call(
      lambda: self.cytomat.send_command(request.command_type, request.command, request.params)
    )
    return ipb.Text(value=reply)

  def send_action(self, request: pb.SendActionRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    timeout: Optional[int] = 60
    if request.HasField("timeout"):
      timeout = request.timeout.value if request.timeout.HasField("value") else None
    return self._move(
      lambda: self.cytomat.send_action(
        request.command_type, request.command, request.params, timeout=timeout
      )
    )

  async def get_overview_register(self, request: ipb.Empty, ctx: Ctx) -> pb.OverviewRegister:
    return overview(await self.call(self.cytomat.get_overview_register))

  async def get_warning_register(self, request: ipb.Empty, ctx: Ctx) -> pb.Register:
    return pb.Register(value=(await self.call(self.cytomat.get_warning_register)).value)

  async def get_error_register(self, request: ipb.Empty, ctx: Ctx) -> pb.Register:
    return pb.Register(value=(await self.call(self.cytomat.get_error_register)).value)

  async def reset_error_register(self, request: ipb.Empty, ctx: Ctx) -> ipb.Empty:
    await self.call(self.cytomat.reset_error_register)
    return ipb.Empty()

  def initialize(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self.stream(self.cytomat.initialize, pb.Progress)

  def open_door(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._move(self.cytomat.open_door)

  def close_door(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._move(self.cytomat.close_door)

  def shovel_in(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._move(self.cytomat.shovel_in)

  def shovel_out(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._move(self.cytomat.shovel_out)

  async def get_action_register(self, request: ipb.Empty, ctx: Ctx) -> pb.ActionRegisterState:
    state = await self.call(self.cytomat.get_action_register)
    return pb.ActionRegisterState(target=state.target.value, action=state.action.value)

  async def get_swap_register(self, request: ipb.Empty, ctx: Ctx) -> pb.SwapStationState:
    state = await self.call(self.cytomat.get_swap_register)
    return pb.SwapStationState(
      position=state.position.value,
      load_status_front_of_gate=state.load_status_front_of_gate.value,
      load_status_at_processor=state.load_status_at_processor.value,
    )

  async def get_sensor_register(self, request: ipb.Empty, ctx: Ctx) -> pb.SensorStates:
    states = await self.call(self.cytomat.get_sensor_register)
    return pb.SensorStates(states=dict(vars(states)))

  def action_transfer_to_storage(
    self, request: ipb.SiteRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._site_move(request, self.cytomat.action_transfer_to_storage)

  def action_storage_to_transfer(
    self, request: ipb.SiteRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._site_move(request, self.cytomat.action_storage_to_transfer)

  def action_storage_to_wait(
    self, request: ipb.SiteRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._site_move(request, self.cytomat.action_storage_to_wait)

  def action_wait_to_storage(
    self, request: ipb.SiteRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._site_move(request, self.cytomat.action_wait_to_storage)

  def action_wait_to_transfer(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._move(self.cytomat.action_wait_to_transfer)

  def action_transfer_to_wait(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._move(self.cytomat.action_transfer_to_wait)

  def action_wait_to_exposed(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._move(self.cytomat.action_wait_to_exposed)

  def action_exposed_to_wait(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._move(self.cytomat.action_exposed_to_wait)

  def action_exposed_to_storage(
    self, request: ipb.SiteRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._site_move(request, self.cytomat.action_exposed_to_storage)

  def action_storage_to_exposed(
    self, request: ipb.SiteRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._site_move(request, self.cytomat.action_storage_to_exposed)

  async def action_read_barcode(
    self, request: pb.ReadBarcodeRequest, ctx: Ctx
  ) -> pb.OverviewRegister:
    state = await self.call(
      lambda: self.cytomat.action_read_barcode(request.site_number_a, request.site_number_b),
      motion=True,
    )
    return overview(state)

  def wait_for_transfer_station(
    self, request: pb.WaitForTransferStationRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    occupied = request.occupied if request.HasField("occupied") else False
    return self.stream(
      lambda: self.cytomat.wait_for_transfer_station(occupied=occupied), pb.Progress, motion=False
    )

  def wait_for_task_completion(
    self, request: pb.WaitForTaskCompletionRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    timeout = request.timeout if request.HasField("timeout") else 60
    return self.stream(
      lambda: self.cytomat.wait_for_task_completion(timeout=timeout),
      pb.Progress,
      _with_overview,
      motion=False,
    )

  async def init_shakers(self, request: ipb.Empty, ctx: Ctx) -> ipb.Text:
    return ipb.Text(value=await self.call(self.cytomat.init_shakers))

  async def start_shaking(self, request: pb.StartShakingRequest, ctx: Ctx) -> ipb.Text:
    shakers = _shakers(request.shakers, request.HasField("shakers"))
    reply = await self.call(lambda: self.cytomat.start_shaking(request.frequency, shakers=shakers))
    return ipb.Text(value=reply)

  async def stop_shaking(self, request: ipb.Empty, ctx: Ctx) -> ipb.Text:
    return ipb.Text(value=await self.call(self.cytomat.stop_shaking))

  async def set_shaking_frequency(
    self, request: pb.SetShakingFrequencyRequest, ctx: Ctx
  ) -> pb.Texts:
    shakers = _shakers(request.shakers, request.HasField("shakers"))
    replies = await self.call(
      lambda: self.cytomat.set_shaking_frequency(request.frequency, shakers=shakers)
    )
    return pb.Texts(values=replies)

  async def _incubation(self, work: Callable[[], Awaitable[object]]) -> pb.IncubationResponse:
    response = await self.call(work)
    return pb.IncubationResponse(
      nominal_value=getattr(response, "nominal_value"),
      actual_value=getattr(response, "actual_value"),
    )

  async def get_incubation_query(
    self, request: pb.IncubationQueryRequest, ctx: Ctx
  ) -> pb.IncubationResponse:
    return await self._incubation(
      lambda: self.cytomat.get_incubation_query(request.query)  # type: ignore[arg-type]
    )

  async def get_co2(self, request: ipb.Empty, ctx: Ctx) -> pb.IncubationResponse:
    return await self._incubation(self.cytomat.get_co2)

  async def get_humidity(self, request: ipb.Empty, ctx: Ctx) -> pb.IncubationResponse:
    return await self._incubation(self.cytomat.get_humidity)

  async def get_o2(self, request: ipb.Empty, ctx: Ctx) -> pb.IncubationResponse:
    return await self._incubation(self.cytomat.get_o2)

  async def get_temperature(self, request: ipb.Empty, ctx: Ctx) -> ipb.Value:
    return ipb.Value(value=await self.call(self.cytomat.get_temperature))

  async def set_temperature(self, request: pb.SetTemperatureRequest, ctx: Ctx) -> ipb.Empty:
    await self.call(lambda: self.cytomat.set_temperature(request.temperature))
    return ipb.Empty()

  def fetch_plate_to_loading_tray(
    self, request: pb.PlateRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    async def fetch() -> None:
      with self.plate(request.plate) as plate:
        await self.cytomat.fetch_plate_to_loading_tray(plate)

    return self.stream(fetch, pb.Progress)

  def take_in_plate(self, request: pb.TakeInPlateRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    async def take_in() -> None:
      with self.plate(request.plate) as plate:
        await self.cytomat.take_in_plate(plate, self.site(request.site))

    return self.stream(take_in, pb.Progress)


def cytomat_server_app(backend: CytomatBackend) -> ASGIApp:
  """One ASGI application serving a Cytomat's backend."""
  return CytomatServiceASGIApplication(_Served(backend))


async def serve(backend: CytomatBackend, host: str = "127.0.0.1", port: int = 8092) -> None:
  """Serve a Cytomat until cancelled. Needs uvicorn, the `resource-server` extra.

  Args:
    backend: the backend to serve.
    host: the address to listen on.
    port: the port to listen on.
  """
  import uvicorn

  await uvicorn.Server(uvicorn.Config(cytomat_server_app(backend), host=host, port=port)).serve()
