"""Serving thermocyclers: one Connect application for the legacy thermocycler backends it holds,
by name.

A call that waits on the thermocycler (setup, a lid move, a temperature, a run) streams its
progress every few seconds, so nothing between the server and a client sees an idle call and cuts
it, and runs on the server to its end even if the client goes away. Status queries may be made
while a run goes on.
"""

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Mapping, Set, TypeVar

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext

from pylabrobot.legacy.thermocycling.backend import ThermocyclerBackend
from pylabrobot.legacy.thermocycling.server.errors import to_connect_error
from pylabrobot.legacy.thermocycling.server.v1 import thermocycler_pb2 as pb
from pylabrobot.legacy.thermocycling.server.v1.thermocycler_connect import (
  ThermocyclerServiceASGIApplication,
)
from pylabrobot.legacy.thermocycling.standard import (
  BlockStatus,
  LidStatus,
  Protocol,
  Stage,
  Step,
)

logger = logging.getLogger(__name__)

# An ASGI 3 application.
ASGIApp = Callable[[Dict[str, Any], Any, Any], Awaitable[None]]

# How often a long call says how far it has got, in seconds.
PROGRESS_INTERVAL = 5.0

T = TypeVar("T")
Ctx = RequestContext[Any, Any]
Backend = ThermocyclerBackend

_LID_STATUSES = {
  LidStatus.IDLE: pb.LID_STATUS_IDLE,
  LidStatus.HOLDING_AT_TARGET: pb.LID_STATUS_HOLDING_AT_TARGET,
}
_BLOCK_STATUSES = {
  BlockStatus.IDLE: pb.BLOCK_STATUS_IDLE,
  BlockStatus.HOLDING_AT_TARGET: pb.BLOCK_STATUS_HOLDING_AT_TARGET,
}


def protocol_to_proto(protocol: Protocol) -> pb.Protocol:
  message = pb.Protocol()
  for stage in protocol.stages:
    stage_message = message.stages.add(repeats=stage.repeats)
    for step in stage.steps:
      step_message = stage_message.steps.add(
        temperature=step.temperature, hold_seconds=step.hold_seconds
      )
      if step.rate is not None:
        step_message.rate = step.rate
  return message


def protocol_from_proto(message: pb.Protocol) -> Protocol:
  return Protocol(
    stages=[
      Stage(
        steps=[
          Step(
            temperature=list(step.temperature),
            hold_seconds=step.hold_seconds,
            rate=step.rate if step.HasField("rate") else None,
          )
          for step in stage.steps
        ],
        repeats=stage.repeats,
      )
      for stage in message.stages
    ]
  )


def kwargs_to_json(backend_kwargs: Mapping[str, Any]) -> str:
  """A backend's own keyword arguments as the requests carry them; empty for none.

  Raises:
    TypeError: If one is not something JSON can say.
  """
  return json.dumps(dict(backend_kwargs)) if backend_kwargs else ""


def kwargs_from_json(text: str) -> Dict[str, Any]:
  """The backend's own keyword arguments a request carries.

  Raises:
    TypeError: If they are not a JSON object.
  """
  if not text:
    return {}
  try:
    kwargs = json.loads(text)
  except ValueError as error:
    raise TypeError(f"backend_kwargs is not JSON: {error}") from None
  if not isinstance(kwargs, dict):
    raise TypeError(f"backend_kwargs is a JSON object, not {type(kwargs).__name__}")
  return kwargs


def _lid_status(status: Any) -> int:
  return _LID_STATUSES[status if isinstance(status, LidStatus) else LidStatus(status)]


def _block_status(status: Any) -> int:
  return _BLOCK_STATUSES[status if isinstance(status, BlockStatus) else BlockStatus(status)]


class _Served:
  """The thermocyclers a server holds, each call made on the backend of the one it names."""

  def __init__(self, thermocyclers: Mapping[str, Backend]):
    if not thermocyclers:
      raise ValueError("a thermocycler server needs at least one thermocycler")
    self.thermocyclers: Dict[str, Backend] = dict(thermocyclers)
    # Calls that keep running when their client has gone, held so they are not collected.
    self._running: Set["asyncio.Task[Any]"] = set()

  def _get(self, name: str) -> Backend:
    backend = self.thermocyclers.get(name)
    if backend is None:
      raise ConnectError(Code.NOT_FOUND, f"this server holds no thermocycler named '{name}'")
    return backend

  async def _call(self, name: str, kwargs: str, call: Callable[..., Awaitable[T]]) -> T:
    """Make a call on the backend of the thermocycler named `name`, with the backend's own keyword
    arguments, raising what it raised as a Connect error."""
    backend = self._get(name)
    try:
      return await call(backend, **kwargs_from_json(kwargs))
    except Exception as error:
      raise to_connect_error(error) from error

  async def _stream(
    self, name: str, kwargs: str, call: Callable[..., Awaitable[Any]]
  ) -> AsyncIterator[pb.Progress]:
    """Make a long call, saying how far it has got every `PROGRESS_INTERVAL` seconds, and when it
    is done. It runs on when the client goes away."""
    backend = self._get(name)
    try:
      arguments = kwargs_from_json(kwargs)
    except TypeError as error:
      raise to_connect_error(error) from error

    async def run() -> Any:
      # Called in the task, so arguments the backend does not take raise there, as its errors do.
      return await call(backend, **arguments)

    start = time.monotonic()
    task = asyncio.ensure_future(run())
    try:
      while True:
        done, _ = await asyncio.wait({task}, timeout=PROGRESS_INTERVAL)
        if done:
          break
        yield pb.Progress(elapsed=time.monotonic() - start)
      try:
        task.result()
      except Exception as error:
        raise to_connect_error(error) from error
      yield pb.Progress(elapsed=time.monotonic() - start, done=True)
    finally:
      if not task.done():
        self._running.add(task)
        task.add_done_callback(self._finished_without_client)

  def _finished_without_client(self, task: "asyncio.Task[Any]") -> None:
    """Let go of a call whose client went away, saying what went wrong if it failed."""
    self._running.discard(task)
    if not task.cancelled() and task.exception() is not None:
      logger.error("a call whose client went away failed", exc_info=task.exception())

  # -- the service --

  async def describe(self, request: pb.DescribeRequest, ctx: Ctx) -> pb.DescribeResponse:
    response = pb.DescribeResponse()
    for name, backend in self.thermocyclers.items():
      response.thermocyclers.add(name=name, backend=type(backend).__name__)
    return response

  def setup(self, request: pb.SetupRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, request.backend_kwargs, lambda b, **k: b.setup(**k))

  async def stop(self, request: pb.StopRequest, ctx: Ctx) -> pb.StopResponse:
    await self._call(request.name, "", lambda b: b.stop())
    return pb.StopResponse()

  def open_lid(self, request: pb.OpenLidRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, request.backend_kwargs, lambda b, **k: b.open_lid(**k))

  def close_lid(self, request: pb.CloseLidRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    return self._stream(request.name, request.backend_kwargs, lambda b, **k: b.close_lid(**k))

  def set_block_temperature(
    self, request: pb.SetBlockTemperatureRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    temperature = list(request.temperature)
    return self._stream(
      request.name,
      request.backend_kwargs,
      lambda b, **k: b.set_block_temperature(temperature, **k),
    )

  def set_lid_temperature(
    self, request: pb.SetLidTemperatureRequest, ctx: Ctx
  ) -> AsyncIterator[pb.Progress]:
    temperature = list(request.temperature)
    return self._stream(
      request.name,
      request.backend_kwargs,
      lambda b, **k: b.set_lid_temperature(temperature, **k),
    )

  async def deactivate_block(
    self, request: pb.DeactivateBlockRequest, ctx: Ctx
  ) -> pb.DeactivateBlockResponse:
    await self._call(request.name, request.backend_kwargs, lambda b, **k: b.deactivate_block(**k))
    return pb.DeactivateBlockResponse()

  async def deactivate_lid(
    self, request: pb.DeactivateLidRequest, ctx: Ctx
  ) -> pb.DeactivateLidResponse:
    await self._call(request.name, request.backend_kwargs, lambda b, **k: b.deactivate_lid(**k))
    return pb.DeactivateLidResponse()

  def run_protocol(self, request: pb.RunProtocolRequest, ctx: Ctx) -> AsyncIterator[pb.Progress]:
    protocol = protocol_from_proto(request.protocol)
    return self._stream(
      request.name,
      request.backend_kwargs,
      lambda b, **k: b.run_protocol(protocol, request.block_max_volume, **k),
    )

  async def _temperatures(
    self, request: pb.GetRequest, get: Callable[..., Awaitable[Any]]
  ) -> pb.TemperatureResponse:
    temperatures = await self._call(request.name, request.backend_kwargs, get)
    return pb.TemperatureResponse(temperature=[float(t) for t in temperatures])

  async def get_block_current_temperature(
    self, request: pb.GetRequest, ctx: Ctx
  ) -> pb.TemperatureResponse:
    return await self._temperatures(request, lambda b, **k: b.get_block_current_temperature(**k))

  async def get_block_target_temperature(
    self, request: pb.GetRequest, ctx: Ctx
  ) -> pb.TemperatureResponse:
    return await self._temperatures(request, lambda b, **k: b.get_block_target_temperature(**k))

  async def get_lid_current_temperature(
    self, request: pb.GetRequest, ctx: Ctx
  ) -> pb.TemperatureResponse:
    return await self._temperatures(request, lambda b, **k: b.get_lid_current_temperature(**k))

  async def get_lid_target_temperature(
    self, request: pb.GetRequest, ctx: Ctx
  ) -> pb.TemperatureResponse:
    return await self._temperatures(request, lambda b, **k: b.get_lid_target_temperature(**k))

  async def get_lid_open(self, request: pb.GetRequest, ctx: Ctx) -> pb.GetLidOpenResponse:
    lid_open = await self._call(
      request.name, request.backend_kwargs, lambda b, **k: b.get_lid_open(**k)
    )
    return pb.GetLidOpenResponse(open=bool(lid_open))

  async def get_lid_status(self, request: pb.GetRequest, ctx: Ctx) -> pb.GetLidStatusResponse:
    status = await self._call(
      request.name,
      request.backend_kwargs,
      lambda b, **k: _as_status(b.get_lid_status(**k), _lid_status),
    )
    return pb.GetLidStatusResponse(status=status)  # type: ignore[arg-type]

  async def get_block_status(self, request: pb.GetRequest, ctx: Ctx) -> pb.GetBlockStatusResponse:
    status = await self._call(
      request.name,
      request.backend_kwargs,
      lambda b, **k: _as_status(b.get_block_status(**k), _block_status),
    )
    return pb.GetBlockStatusResponse(status=status)  # type: ignore[arg-type]

  async def get_hold_time(self, request: pb.GetRequest, ctx: Ctx) -> pb.GetHoldTimeResponse:
    seconds = await self._call(
      request.name, request.backend_kwargs, lambda b, **k: b.get_hold_time(**k)
    )
    return pb.GetHoldTimeResponse(seconds=float(seconds))

  async def _integer(
    self, request: pb.GetRequest, get: Callable[..., Awaitable[Any]]
  ) -> pb.IntegerResponse:
    value = await self._call(request.name, request.backend_kwargs, get)
    return pb.IntegerResponse(value=int(value))

  async def get_current_cycle_index(self, request: pb.GetRequest, ctx: Ctx) -> pb.IntegerResponse:
    return await self._integer(request, lambda b, **k: b.get_current_cycle_index(**k))

  async def get_total_cycle_count(self, request: pb.GetRequest, ctx: Ctx) -> pb.IntegerResponse:
    return await self._integer(request, lambda b, **k: b.get_total_cycle_count(**k))

  async def get_current_step_index(self, request: pb.GetRequest, ctx: Ctx) -> pb.IntegerResponse:
    return await self._integer(request, lambda b, **k: b.get_current_step_index(**k))

  async def get_total_step_count(self, request: pb.GetRequest, ctx: Ctx) -> pb.IntegerResponse:
    return await self._integer(request, lambda b, **k: b.get_total_step_count(**k))


async def _as_status(status: Awaitable[Any], number: Callable[[Any], int]) -> int:
  """A status a backend returned, as the proto numbers it.

  Raises:
    ValueError: If it is none of the statuses.
  """
  return number(await status)


def thermocycler_server_app(thermocyclers: Mapping[str, Backend]) -> ASGIApp:
  """One ASGI application serving these thermocyclers' backends, each called by its name.

  Raises:
    ValueError: If given none.
  """
  return ThermocyclerServiceASGIApplication(_Served(thermocyclers))


async def serve(
  thermocyclers: Mapping[str, Backend], host: str = "127.0.0.1", port: int = 8096
) -> None:
  """Serve thermocyclers until cancelled. Needs uvicorn, the `resource-server` extra.

  Args:
    thermocyclers: the backends of the thermocyclers to serve, by the name each is called by.
    host: the address to listen on.
    port: the port to listen on.
  """
  import uvicorn

  await uvicorn.Server(
    uvicorn.Config(thermocycler_server_app(thermocyclers), host=host, port=port)
  ).serve()
