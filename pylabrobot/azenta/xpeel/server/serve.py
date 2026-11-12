"""Serving XPeels: one Connect application for the peelers it holds, by name.

A call that waits on the peeler streams its progress every few seconds, so nothing between the
server and a client sees an idle call and cuts it, and, but for a call that only asks, runs on the
server to its end even if the client goes away. A peeler takes one call at a time, as its serial
line does: a call waits for the one before it.
"""

import asyncio
import logging
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Mapping, Set, TypeVar

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext

from pylabrobot.azenta.xpeel.server.errors import to_connect_error
from pylabrobot.azenta.xpeel.server.v1 import xpeel_pb2 as pb
from pylabrobot.azenta.xpeel.server.v1.xpeel_connect import XPeelServiceASGIApplication
from pylabrobot.azenta.xpeel.xpeel import XPeel

logger = logging.getLogger(__name__)

# An ASGI 3 application.
ASGIApp = Callable[[Dict[str, Any], Any, Any], Awaitable[None]]

# How often a long call says how far it has got, in seconds.
PROGRESS_INTERVAL = 5.0

# What `XPeel.seal_check` returns, as the proto numbers it.
SEAL_CHECKS: Dict[str, int] = {
  "seal_detected": pb.SEAL_CHECK_SEAL_DETECTED,
  "no_seal": pb.SEAL_CHECK_NO_SEAL,
  "plate_not_detected": pb.SEAL_CHECK_PLATE_NOT_DETECTED,
}

T = TypeVar("T")
Ctx = RequestContext[Any, Any]
# What a long call returned, as the progress that says it is done carries it.
Result = Callable[[Any, pb.Progress], None]


def _lines(lines: Any, progress: pb.Progress) -> None:
  progress.lines.lines.extend(lines)


def _seal_check(result: Any, progress: pb.Progress) -> None:
  progress.seal_check = SEAL_CHECKS[result]  # type: ignore[assignment]


def _tape_remaining(result: Any, progress: pb.Progress) -> None:
  supply, takeup = result
  progress.tape_remaining.supply_remaining = supply
  progress.tape_remaining.takeup_remaining = takeup


class _Served:
  """The peelers a server holds, each call made on the one it names, one at a time."""

  def __init__(self, peelers: Mapping[str, XPeel]):
    if not peelers:
      raise ValueError("an XPeel server needs at least one peeler")
    self.peelers: Dict[str, XPeel] = dict(peelers)
    self._locks: Dict[str, asyncio.Lock] = {}
    # Calls that keep running when their client has gone, held so they are not collected.
    self._running: Set["asyncio.Task[Any]"] = set()

  def _get(self, name: str) -> XPeel:
    peeler = self.peelers.get(name)
    if peeler is None:
      raise ConnectError(Code.NOT_FOUND, f"this server holds no peeler named '{name}'")
    return peeler

  async def _one_at_a_time(
    self, name: str, peeler: XPeel, call: Callable[[XPeel], Awaitable[T]]
  ) -> T:
    lock = self._locks.setdefault(name, asyncio.Lock())
    async with lock:
      return await call(peeler)

  async def _call(self, name: str, call: Callable[[XPeel], Awaitable[T]]) -> T:
    """Make a call on the peeler named `name`, raising what it raised as a Connect error."""
    peeler = self._get(name)
    try:
      return await self._one_at_a_time(name, peeler, call)
    except Exception as error:
      raise to_connect_error(error) from error

  async def _stream(
    self,
    name: str,
    call: Callable[[XPeel], Awaitable[Any]],
    result: Result = _lines,
    finish_without_client: bool = True,
  ) -> AsyncIterator[pb.Progress]:
    """Make a long call, saying how far it has got every `PROGRESS_INTERVAL` seconds, and when it
    is done, with what it returned.

    Args:
      result: puts what the call returned in the progress that says it is done.
      finish_without_client: whether the call runs on when the client goes away.
    """
    peeler = self._get(name)
    start = time.monotonic()
    task = asyncio.ensure_future(self._one_at_a_time(name, peeler, call))
    try:
      while True:
        done, _ = await asyncio.wait({task}, timeout=PROGRESS_INTERVAL)
        if done:
          break
        yield pb.Progress(elapsed=time.monotonic() - start)
      try:
        returned = task.result()
      except Exception as error:
        raise to_connect_error(error) from error
      progress = pb.Progress(elapsed=time.monotonic() - start, done=True)
      result(returned, progress)
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
    for name, peeler in self.peelers.items():
      response.peelers.add(name=name, port=peeler.port, response_timeout=peeler.response_timeout)
    return response

  async def setup(self, request: pb.SetupRequest, ctx: Ctx) -> pb.SetupResponse:
    await self._call(request.name, lambda p: p.setup())
    return pb.SetupResponse()

  async def stop(self, request: pb.StopRequest, ctx: Ctx) -> pb.StopResponse:
    await self._call(request.name, lambda p: p.stop())
    return pb.StopResponse()

  def send_command(self, request: pb.SendCommandRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    expect_ack = request.expect_ack if request.HasField("expect_ack") else False
    wait_for_ready = request.wait_for_ready if request.HasField("wait_for_ready") else False
    clear_buffer = request.clear_buffer if request.HasField("clear_buffer") else True
    return self._stream(
      request.name,
      lambda p: p.send_command(
        request.cmd,
        expect_ack=expect_ack,
        wait_for_ready=wait_for_ready,
        clear_buffer=clear_buffer,
      ),
    )

  async def request_status(
    self, request: pb.RequestStatusRequest, ctx: Ctx
  ) -> pb.RequestStatusResponse:
    first, second, third = await self._call(request.name, lambda p: p.request_status())
    return pb.RequestStatusResponse(first=first, second=second, third=third)

  async def request_version(
    self, request: pb.RequestVersionRequest, ctx: Ctx
  ) -> pb.RequestVersionResponse:
    lines = await self._call(request.name, lambda p: p.request_version())
    return pb.RequestVersionResponse(lines=lines)

  def reset(self, request: pb.ResetRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda p: p.reset())

  def seal_check(self, request: pb.SealCheckRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(
      request.name, lambda p: p.seal_check(), _seal_check, finish_without_client=False
    )

  def request_tape_remaining(
    self, request: pb.RequestTapeRemainingRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._stream(
      request.name,
      lambda p: p.request_tape_remaining(),
      _tape_remaining,
      finish_without_client=False,
    )

  def enable_plate_check(
    self, request: pb.EnablePlateCheckRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    enabled = request.enabled if request.HasField("enabled") else True
    return self._stream(request.name, lambda p: p.enable_plate_check(enabled))

  def request_seal_sensor_status(
    self, request: pb.RequestSealSensorStatusRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._stream(
      request.name, lambda p: p.request_seal_sensor_status(), finish_without_client=False
    )

  def set_seal_threshold_upper(
    self, request: pb.SetSealThresholdUpperRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda p: p.set_seal_threshold_upper(request.value))

  def set_seal_threshold_lower(
    self, request: pb.SetSealThresholdLowerRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda p: p.set_seal_threshold_lower(request.value))

  def move_conveyor_out(
    self, request: pb.MoveConveyorOutRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda p: p.move_conveyor_out())

  def move_conveyor_in(
    self, request: pb.MoveConveyorInRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda p: p.move_conveyor_in())

  def move_elevator_down(
    self, request: pb.MoveElevatorDownRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda p: p.move_elevator_down())

  def move_elevator_up(
    self, request: pb.MoveElevatorUpRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda p: p.move_elevator_up())

  def advance_tape(self, request: pb.AdvanceTapeRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda p: p.advance_tape())

  def peel(self, request: pb.PeelRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    arguments: Dict[str, Any] = {}
    if request.HasField("begin_location"):
      arguments["begin_location"] = request.begin_location
    if request.HasField("fast"):
      arguments["fast"] = request.fast
    if request.HasField("adhere_time"):
      arguments["adhere_time"] = request.adhere_time
    return self._stream(request.name, lambda p: p.peel(**arguments))

  def restart(self, request: pb.RestartRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, lambda p: p.restart())


def xpeel_server_app(peelers: Mapping[str, XPeel]) -> ASGIApp:
  """One ASGI application serving these peelers, each called by its name.

  Raises:
    ValueError: If given none.
  """
  return XPeelServiceASGIApplication(_Served(peelers))


async def serve(peelers: Mapping[str, XPeel], host: str = "127.0.0.1", port: int = 8095) -> None:
  """Serve peelers until cancelled. Needs uvicorn, the `resource-server` extra.

  Args:
    peelers: the peelers to serve, by the name each is called by.
    host: the address to listen on.
    port: the port to listen on.
  """
  import uvicorn

  await uvicorn.Server(uvicorn.Config(xpeel_server_app(peelers), host=host, port=port)).serve()
