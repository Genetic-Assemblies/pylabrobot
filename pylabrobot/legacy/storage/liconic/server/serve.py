"""Serving a Liconic: one Connect application for one `ExperimentalLiconicBackend`.

A call that waits for the PLC to be ready (a move, a door, a setpoint) streams its progress every
few seconds and finishes on the server even if its client goes away. See
`pylabrobot.legacy.storage.server.served` for how sites and plates are named, and how calls from
several clients share the serial port.
"""

from typing import Any, AsyncIterator, Awaitable, Callable, List, Optional

from connectrpc.request import RequestContext

from pylabrobot.legacy.storage.liconic.liconic_backend import ExperimentalLiconicBackend
from pylabrobot.legacy.storage.liconic.server.v1 import liconic_pb2 as pb
from pylabrobot.legacy.storage.liconic.server.v1.liconic_connect import (
  LiconicServiceASGIApplication,
)
from pylabrobot.legacy.storage.server.served import (
  ASGIApp,
  ServedBackend,
  describe_racks,
  from_barcode,
)
from pylabrobot.legacy.storage.server.v1 import incubator_pb2 as ipb
from pylabrobot.resources import Plate
from pylabrobot.resources.barcode import Barcode

Ctx = RequestContext[Any, Any]


def _with_barcode(barcode: Optional[Barcode], last: pb.Progress) -> None:
  if barcode is not None:
    last.barcode.CopyFrom(from_barcode(barcode))


def _with_value(value: float, last: pb.Progress) -> None:
  last.value = value


class _Served(ServedBackend):
  """One Liconic, each call made on it."""

  def __init__(self, backend: ExperimentalLiconicBackend):
    super().__init__(backend, io="_send_command")
    self.liconic = backend

  def _long(self, work: Callable[[], Awaitable[Any]]) -> AsyncIterator[pb.Progress]:
    return self.stream(work, pb.Progress)

  def _move(
    self, request: Any, move: Callable[[Plate, bool], Awaitable[None]]
  ) -> AsyncIterator[pb.Progress]:
    """A move of the plate a request gives, ending with the barcode it read when it read one; a
    move that fails after reading it sends it ahead of the error, as the plate has it then."""
    read_barcode = request.read_barcode if request.HasField("read_barcode") else False
    moving: List[Plate] = []

    async def run() -> Optional[Barcode]:
      with self.plate(request.plate) as plate:
        moving.append(plate)
        await move(plate, read_barcode)
        return plate.barcode if read_barcode else None

    def read_before_failing(progress: pb.Progress) -> bool:
      if not read_barcode or not moving or moving[0].barcode is None:
        return False
      _with_barcode(moving[0].barcode, progress)
      return True

    return self.stream(run, pb.Progress, _with_barcode, partial=read_before_failing)

  # -- the backend --

  async def describe(self, request: ipb.Empty, ctx: Ctx) -> pb.Description:
    return pb.Description(
      model=self.liconic.model.value,
      racks=describe_racks(self.racks),
      barcode_scanner=self.liconic.barcode_scanner is not None,
    )

  def setup(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._long(self.liconic.setup)

  async def stop(self, request: ipb.Empty, ctx: Ctx) -> ipb.Empty:
    await self.call(self.liconic.stop)
    return ipb.Empty()

  async def set_racks(self, request: ipb.SetRacksRequest, ctx: Ctx) -> ipb.Empty:
    await self.call(lambda: self.take_racks(request))
    return ipb.Empty()

  def initialize(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._long(self.liconic.initialize)

  def open_door(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._long(self.liconic.open_door)

  def close_door(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._long(self.liconic.close_door)

  def fetch_plate_to_loading_tray(
    self, request: pb.FetchPlateToLoadingTrayRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._move(
      request,
      lambda plate, read: self.liconic.fetch_plate_to_loading_tray(plate, read_barcode=read),
    )

  def take_in_plate(self, request: pb.TakeInPlateRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._move(
      request,
      lambda plate, read: self.liconic.take_in_plate(
        plate, self.site(request.site), read_barcode=read
      ),
    )

  def move_position_to_position(
    self, request: pb.MovePositionToPositionRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._move(
      request,
      lambda plate, read: self.liconic.move_position_to_position(
        plate, self.site(request.dest_site), read_barcode=read
      ),
    )

  def read_barcode_inline(
    self, request: pb.ReadBarcodeInlineRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self.stream(
      lambda: self.liconic.read_barcode_inline(request.cassette, request.plt_position),
      pb.Progress,
      _with_barcode,
    )

  def scan_barcode(self, request: ipb.SiteRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self.stream(
      lambda: self.liconic.scan_barcode(self.site(request.site)), pb.Progress, _with_barcode
    )

  async def _value(self, work: Callable[[], Awaitable[float]]) -> ipb.Value:
    return ipb.Value(value=await self.call(work))

  def set_temperature(self, request: pb.Temperature, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._long(lambda: self.liconic.set_temperature(request.temperature))

  async def get_temperature(self, request: ipb.Empty, ctx: Ctx) -> ipb.Value:
    return await self._value(self.liconic.get_temperature)

  async def get_target_temperature(self, request: ipb.Empty, ctx: Ctx) -> ipb.Value:
    return await self._value(self.liconic.get_target_temperature)

  def set_humidity(self, request: pb.Humidity, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._long(lambda: self.liconic.set_humidity(request.humidity))

  async def get_humidity(self, request: ipb.Empty, ctx: Ctx) -> ipb.Value:
    return await self._value(self.liconic.get_humidity)

  async def get_target_humidity(self, request: ipb.Empty, ctx: Ctx) -> ipb.Value:
    return await self._value(self.liconic.get_target_humidity)

  def set_co2_level(self, request: pb.Co2Level, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._long(lambda: self.liconic.set_co2_level(request.co2_level))

  async def get_co2_level(self, request: ipb.Empty, ctx: Ctx) -> ipb.Value:
    return await self._value(self.liconic.get_co2_level)

  async def get_target_co2_level(self, request: ipb.Empty, ctx: Ctx) -> ipb.Value:
    return await self._value(self.liconic.get_target_co2_level)

  def set_n2_level(self, request: pb.N2Level, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._long(lambda: self.liconic.set_n2_level(request.n2_level))

  async def get_n2_level(self, request: ipb.Empty, ctx: Ctx) -> ipb.Value:
    return await self._value(self.liconic.get_n2_level)

  async def get_target_n2_level(self, request: ipb.Empty, ctx: Ctx) -> ipb.Value:
    return await self._value(self.liconic.get_target_n2_level)

  async def shaker_status(self, request: ipb.Empty, ctx: Ctx) -> pb.ShakerStatusResponse:
    return pb.ShakerStatusResponse(status=await self.call(self.liconic.shaker_status))

  def get_shaker_speed(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self.stream(self.liconic.get_shaker_speed, pb.Progress, _with_value)

  def start_shaking(self, request: pb.Frequency, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._long(lambda: self.liconic.start_shaking(request.frequency))

  def stop_shaking(self, request: ipb.Empty, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._long(self.liconic.stop_shaking)

  async def turn_swap_station(self, request: pb.TurnSwapStationRequest, ctx: Ctx) -> ipb.Empty:
    await self.call(lambda: self.liconic.turn_swap_station(request.home), motion=True)
    return ipb.Empty()

  async def check_shovel_sensor(self, request: ipb.Empty, ctx: Ctx) -> ipb.Flag:
    return ipb.Flag(value=await self.call(self.liconic.check_shovel_sensor))

  async def check_transfer_sensor(self, request: ipb.Empty, ctx: Ctx) -> ipb.Flag:
    return ipb.Flag(value=await self.call(self.liconic.check_transfer_sensor))

  async def check_second_transfer_sensor(self, request: ipb.Empty, ctx: Ctx) -> ipb.Flag:
    return ipb.Flag(value=await self.call(self.liconic.check_second_transfer_sensor))


def liconic_server_app(backend: ExperimentalLiconicBackend) -> ASGIApp:
  """One ASGI application serving a Liconic's backend."""
  return LiconicServiceASGIApplication(_Served(backend))


async def serve(
  backend: ExperimentalLiconicBackend, host: str = "127.0.0.1", port: int = 8093
) -> None:
  """Serve a Liconic until cancelled. Needs uvicorn, the `resource-server` extra.

  Args:
    backend: the backend to serve.
    host: the address to listen on.
    port: the port to listen on.
  """
  import uvicorn

  await uvicorn.Server(uvicorn.Config(liconic_server_app(backend), host=host, port=port)).serve()
