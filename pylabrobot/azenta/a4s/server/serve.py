"""Serving a4S sealers: one Connect application for the sealers it holds, by name.

A call that waits on the sealer streams its progress every few seconds, so nothing between the
server and a client sees an idle call and cuts it, and, but for a call that only waits, runs on the
server to its end even if the client goes away. A sealer takes one call at a time, as its serial
line does: a call waits for the one before it.
"""

import asyncio
import logging
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Mapping, Set, TypeVar

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext

from pylabrobot.azenta.a4s.a4s import A4S, A4SStatus
from pylabrobot.azenta.a4s.server.errors import to_connect_error
from pylabrobot.azenta.a4s.server.v1 import a4s_pb2 as pb
from pylabrobot.azenta.a4s.server.v1.a4s_connect import A4SServiceASGIApplication

logger = logging.getLogger(__name__)

# An ASGI 3 application.
ASGIApp = Callable[[Dict[str, Any], Any, Any], Awaitable[None]]

# How often a long call says how far it has got, in seconds.
PROGRESS_INTERVAL = 5.0

T = TypeVar("T")
Ctx = RequestContext[Any, Any]


def status_to_proto(status: A4SStatus) -> pb.A4SStatus:
  sensors = status.sensor_status
  return pb.A4SStatus(
    current_temperature=status.current_temperature,
    system_status=status.system_status.value,  # type: ignore[arg-type]
    heater_block_status=status.heater_block_status.value,  # type: ignore[arg-type]
    error_code=status.error_code,
    warning_code=status.warning_code,
    sensor_status=pb.SensorStatus(
      shuttle_middle_sensor=sensors.shuttle_middle_sensor,
      shuttle_open_sensor=sensors.shuttle_open_sensor,
      shuttle_close_sensor=sensors.shuttle_close_sensor,
      clean_door_sensor=sensors.clean_door_sensor,
      seal_roll_sensor=sensors.seal_roll_sensor,
      heater_motor_up_sensor=sensors.heater_motor_up_sensor,
      heater_motor_down_sensor=sensors.heater_motor_down_sensor,
    ),
    remaining_time=status.remaining_time,
  )


def status_from_proto(status: pb.A4SStatus) -> A4SStatus:
  sensors = status.sensor_status
  return A4SStatus(
    current_temperature=status.current_temperature,
    system_status=A4SStatus.SystemStatus(status.system_status),
    heater_block_status=A4SStatus.HeaterBlockStatus(status.heater_block_status),
    error_code=status.error_code,
    warning_code=status.warning_code,
    sensor_status=A4SStatus.SensorStatus(
      shuttle_middle_sensor=sensors.shuttle_middle_sensor,
      shuttle_open_sensor=sensors.shuttle_open_sensor,
      shuttle_close_sensor=sensors.shuttle_close_sensor,
      clean_door_sensor=sensors.clean_door_sensor,
      seal_roll_sensor=sensors.seal_roll_sensor,
      heater_motor_up_sensor=sensors.heater_motor_up_sensor,
      heater_motor_down_sensor=sensors.heater_motor_down_sensor,
    ),
    remaining_time=status.remaining_time,
  )


class _Served:
  """The sealers a server holds, each call made on the one it names, one at a time."""

  def __init__(self, sealers: Mapping[str, A4S]):
    if not sealers:
      raise ValueError("an a4S server needs at least one sealer")
    self.sealers: Dict[str, A4S] = dict(sealers)
    self._locks: Dict[str, asyncio.Lock] = {}
    # Calls that keep running when their client has gone, held so they are not collected.
    self._running: Set["asyncio.Task[Any]"] = set()

  def _get(self, name: str) -> A4S:
    sealer = self.sealers.get(name)
    if sealer is None:
      raise ConnectError(Code.NOT_FOUND, f"this server holds no sealer named '{name}'")
    return sealer

  async def _one_at_a_time(self, name: str, sealer: A4S, call: Callable[[A4S], Awaitable[T]]) -> T:
    lock = self._locks.setdefault(name, asyncio.Lock())
    async with lock:
      return await call(sealer)

  async def _call(self, name: str, call: Callable[[A4S], Awaitable[T]]) -> T:
    """Make a call on the sealer named `name`, raising what it raised as a Connect error."""
    sealer = self._get(name)
    try:
      return await self._one_at_a_time(name, sealer, call)
    except Exception as error:
      raise to_connect_error(error) from error

  async def _stream(
    self,
    name: str,
    call: Callable[[A4S], Awaitable[Any]],
    finish_without_client: bool = True,
  ) -> AsyncIterator[pb.Progress]:
    """Make a long call, saying how far it has got every `PROGRESS_INTERVAL` seconds, and when it
    is done, with the status it returned, if it returned one.

    Args:
      finish_without_client: whether the call runs on when the client goes away.
    """
    sealer = self._get(name)
    start = time.monotonic()
    task = asyncio.ensure_future(self._one_at_a_time(name, sealer, call))
    try:
      while True:
        done, _ = await asyncio.wait({task}, timeout=PROGRESS_INTERVAL)
        if done:
          break
        yield pb.Progress(elapsed=time.monotonic() - start)
      try:
        result = task.result()
      except Exception as error:
        raise to_connect_error(error) from error
      progress = pb.Progress(elapsed=time.monotonic() - start, done=True)
      if isinstance(result, A4SStatus):
        progress.status.CopyFrom(status_to_proto(result))
      yield progress
    finally:
      if not task.done():
        if finish_without_client:
          self._running.add(task)
          task.add_done_callback(self._finished_without_client)
        else:
          task.cancel()

  def _finished_without_client(self, task: "asyncio.Task[Any]") -> None:
    """Let go of a call whose client went away, saying what went wrong if it failed."""
    self._running.discard(task)
    if not task.cancelled() and task.exception() is not None:
      logger.error("a call whose client went away failed", exc_info=task.exception())

  # -- the service --

  async def describe(self, request: pb.DescribeRequest, ctx: Ctx) -> pb.DescribeResponse:
    response = pb.DescribeResponse()
    for name, sealer in self.sealers.items():
      response.sealers.add(name=name, port=sealer.port, timeout=sealer.timeout)
    return response

  def setup(self, request: pb.SetupRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda s: s.setup())

  def stop(self, request: pb.StopRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda s: s.stop())

  async def send_command(self, request: pb.SendCommandRequest, ctx: Ctx) -> pb.SendCommandResponse:
    await self._call(request.name, lambda s: s.send_command(request.command))
    return pb.SendCommandResponse()

  async def read_message(self, request: pb.ReadMessageRequest, ctx: Ctx) -> pb.ReadMessageResponse:
    message = await self._call(request.name, lambda s: s.read_message())
    return pb.ReadMessageResponse(message=message)

  async def request_status(self, request: pb.RequestStatusRequest, ctx: Ctx) -> pb.A4SStatus:
    return status_to_proto(await self._call(request.name, lambda s: s.request_status()))

  def wait_for_status(
    self, request: pb.WaitForStatusRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    statuses = {A4SStatus.SystemStatus(status) for status in request.statuses}
    return self._stream(
      request.name, lambda s: s.wait_for_status(statuses), finish_without_client=False
    )

  def wait_for_shuttle_open_sensor(
    self, request: pb.WaitForShuttleOpenSensorRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    timeout = request.timeout if request.HasField("timeout") else 30.0
    return self._stream(
      request.name,
      lambda s: s.wait_for_shuttle_open_sensor(request.shuttle_open, timeout=timeout),
      finish_without_client=False,
    )

  def system_reset(self, request: pb.SystemResetRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda s: s.system_reset())

  def set_heater(self, request: pb.SetHeaterRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda s: s.set_heater(request.on))

  async def set_time(self, request: pb.SetTimeRequest, ctx: Ctx) -> pb.SetTimeResponse:
    await self._call(request.name, lambda s: s.set_time(request.seconds))
    return pb.SetTimeResponse()

  async def request_remaining_time(
    self, request: pb.RequestRemainingTimeRequest, ctx: Ctx
  ) -> pb.RequestRemainingTimeResponse:
    remaining = await self._call(request.name, lambda s: s.request_remaining_time())
    return pb.RequestRemainingTimeResponse(remaining_time=remaining)

  def seal(self, request: pb.SealRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(
      request.name,
      lambda s: s.seal(request.temperature, request.duration),  # type: ignore[arg-type]
    )

  def open_shuttle(self, request: pb.OpenShuttleRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda s: s.open())

  def close_shuttle(self, request: pb.CloseShuttleRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda s: s.close())

  def set_temperature(
    self, request: pb.SetTemperatureRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._stream(
      request.name,
      lambda s: s.set_temperature(request.temperature),
      finish_without_client=False,
    )

  async def request_current_temperature(
    self, request: pb.RequestCurrentTemperatureRequest, ctx: Ctx
  ) -> pb.RequestCurrentTemperatureResponse:
    temperature = await self._call(request.name, lambda s: s.request_current_temperature())
    return pb.RequestCurrentTemperatureResponse(temperature=temperature)

  def deactivate(self, request: pb.DeactivateRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda s: s.deactivate())


def a4s_server_app(sealers: Mapping[str, A4S]) -> ASGIApp:
  """One ASGI application serving these sealers, each called by its name.

  Raises:
    ValueError: If given none.
  """
  return A4SServiceASGIApplication(_Served(sealers))


async def serve(
  sealers: Mapping[str, A4S],
  host: str = "127.0.0.1",
  port: int = 8094,
) -> None:
  """Serve sealers until cancelled. Needs uvicorn, the `resource-server` extra.

  Args:
    sealers: the sealers to serve, by the name each is called by.
    host: the address to listen on.
    port: the port to listen on.
  """
  import uvicorn

  await uvicorn.Server(uvicorn.Config(a4s_server_app(sealers), host=host, port=port)).serve()
