"""A MicroSpin served elsewhere, driven with the same methods as one in this process.

`MicroSpin(microspin_server=url, resource_server=url)` is a `ServedMicroSpin`: each method is a call
to the MicroSpin server, and the device's resources are read off the resource server the MicroSpin
server keeps them on. What a call raises on the server, the client raises, as the same class.

A spin is streamed. The client makes its request id, and if the stream drops it asks for the same
spin again by that id, which the server does not start twice; so a spin is never lost or doubled by
a network that comes and goes.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Dict, List, Mapping, Optional, TypeVar, Union

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext
from pyqwest import Client

from pylabrobot.resources.server import PlateHolder, ResourceServer
from pylabrobot.resources.server.asgi_transport import ASGITransport

from ..device import MicroSpin
from ..driver import Bucket, CommandStatus, MicroSpinDriver, MicroSpinStatus
from ..errors import ErrorEntry
from .errors import from_connect_error, from_error
from .v1 import microspin_pb2 as mpb
from .v1.microspin_connect import MicroSpinServiceClient

logger = logging.getLogger(__name__)

REQ = TypeVar("REQ")
RES = TypeVar("RES")

_IN_PROCESS = "http://in-process"

# The codes a dropped connection comes as, after which a spin is asked for again.
_RECONNECT_CODES = (Code.UNAVAILABLE, Code.UNKNOWN)

_COMMAND_STATUSES: Dict[mpb.CommandStatus, CommandStatus] = {
  mpb.COMMAND_STATUS_OK: "OK",
  mpb.COMMAND_STATUS_ERROR: "ERROR",
  mpb.COMMAND_STATUS_ABORTED: "ABORTED",
  mpb.COMMAND_STATUS_FAIL: "FAIL",
  mpb.COMMAND_STATUS_RUNNING: "RUNNING",
}


class _Errors:
  """Raises what a call raised on the server, for every call a client makes."""

  async def intercept_unary(
    self,
    call_next: Callable[[REQ, RequestContext], Awaitable[RES]],
    request: REQ,
    ctx: RequestContext,
    /,
  ) -> RES:
    try:
      return await call_next(request, ctx)
    except ConnectError as error:
      raised = from_connect_error(error)
      if raised is None:
        raise
      raise raised from error

  async def intercept_server_stream(
    self,
    call_next: Callable[[REQ, RequestContext], AsyncIterator[RES]],
    request: REQ,
    ctx: RequestContext,
    /,
  ) -> AsyncIterator[RES]:
    try:
      async for response in call_next(request, ctx):
        yield response
    except ConnectError as error:
      raised = from_connect_error(error)
      if raised is None:
        raise
      raise raised from error


class _Headers:
  """Sends the same headers with every call a client makes: its credentials."""

  def __init__(self, headers: Mapping[str, str]) -> None:
    self.headers = dict(headers)

  async def intercept_unary(
    self,
    call_next: Callable[[REQ, RequestContext], Awaitable[RES]],
    request: REQ,
    ctx: RequestContext,
    /,
  ) -> RES:
    ctx.request_headers.update(self.headers)
    return await call_next(request, ctx)

  async def intercept_server_stream(
    self,
    call_next: Callable[[REQ, RequestContext], AsyncIterator[RES]],
    request: REQ,
    ctx: RequestContext,
    /,
  ) -> AsyncIterator[RES]:
    ctx.request_headers.update(self.headers)
    async for response in call_next(request, ctx):
      yield response


class MicroSpinServer:
  """A connection to a MicroSpin server.

  Attributes:
    service: the server's `MicroSpinService`.
  """

  def __init__(self, address: str, http: Client, headers: Optional[Mapping[str, str]] = None):
    interceptors: List[Any] = [_Errors()]
    if headers:
      interceptors.append(_Headers(headers))
    self._http = http
    self.service = MicroSpinServiceClient(address, http_client=http, interceptors=interceptors)

  @classmethod
  def connect(cls, url: str, headers: Optional[Mapping[str, str]] = None) -> "MicroSpinServer":
    """A MicroSpin server served at `url`, "http://lab-cf:8082" say.

    Args:
      headers: sent with every call: the credentials whatever the server sits behind asks for.
    """
    return cls(url, Client(), headers=headers)

  @classmethod
  def in_process(cls, app: Any) -> "MicroSpinServer":
    """A MicroSpin server's application in this process, spoken to without a socket."""
    return cls(_IN_PROCESS, Client(transport=ASGITransport(app)))


def _status(message: mpb.Status) -> MicroSpinStatus:
  return MicroSpinStatus(
    spindle_position=message.spindle_position, door_position=message.door_position
  )


class ServedMicroSpin(MicroSpin):
  """A MicroSpin served by a MicroSpin server: the same methods, each a call to it.

  The device's resources are on the resource server it keeps them on, which a client names too;
  `get_door`, `get_bucket_at_door` and the balance check read them there. Settings, the defaults
  used where a call names none, belong to the server: `settings` reads them.
  """

  def __init__(
    self,
    name: Optional[str] = None,
    host: Optional[str] = None,
    port: int = MicroSpinDriver.DEFAULT_PORT,
    simulation: bool = False,
    resource_server: Optional[Union[str, ResourceServer]] = None,
    driver: Optional[MicroSpinDriver] = None,
    microspin_server: Union[str, MicroSpinServer, None] = None,
    reconnect_attempts: int = 5,
    reconnect_delay: float = 1.0,
  ) -> None:
    """
    Args:
      name: what the server calls the device; checked at setup when given.
      host: not given: the server decides how it reaches the device.
      port: not given, as `host`.
      simulation: not given, as `host`.
      resource_server: the resource server the MicroSpin server keeps the device's resources on, or
        its URL.
      driver: not given, as `host`.
      microspin_server: the MicroSpin server, or its URL.
      reconnect_attempts: how many times a dropped spin stream is asked for again.
      reconnect_delay: how long before asking again the first time, in seconds; it doubles each
        time after, up to 30 s.
    """
    if host is not None or simulation or driver is not None:
      raise ValueError(
        "a served MicroSpin is what its server makes it: host, simulation and "
        "driver cannot be given with microspin_server"
      )
    if microspin_server is None:
      raise ValueError("a served MicroSpin needs microspin_server")
    if resource_server is None:
      raise ValueError("a served MicroSpin needs the resource_server its server keeps it on")
    if isinstance(microspin_server, str):
      microspin_server = MicroSpinServer.connect(microspin_server)
    if isinstance(resource_server, str):
      resource_server = ResourceServer.connect(resource_server)
    self.name = name or ""
    self._expected_name = name
    self.server = microspin_server
    self.resource_server = resource_server
    self.reconnect_attempts = reconnect_attempts
    self.reconnect_delay = reconnect_delay
    self.body = None
    self.rotor = None
    self.buckets = {}
    self._settings: Optional[mpb.Settings] = None

  @property
  def driver(self) -> MicroSpinDriver:
    raise RuntimeError("a served MicroSpin's driver is on its server")

  @property
  def settings(self) -> mpb.Settings:
    """The defaults the server's device uses where a call names none."""
    if self._settings is None:
      raise RuntimeError("call setup() or create_resources() first")
    return self._settings

  # -- the device's resources -------------------------------------------------------------------

  async def create_resources(self) -> None:
    """Take up the resources the server keeps the device's parts as."""
    described = await self.server.service.describe(mpb.Empty())
    if self._expected_name is not None and described.name != self._expected_name:
      raise ValueError(f"the server serves '{described.name}', not '{self._expected_name}'")
    get = self.resource_server.get_by_id
    buckets: Dict[int, PlateHolder] = {}
    for bucket, ref in ((1, described.bucket_1), (2, described.bucket_2)):
      found = await get(ref.id)
      if not isinstance(found, PlateHolder):
        raise ValueError(f"bucket {bucket} on the resource server is not a plate holder")
      buckets[bucket] = found
    self.name = described.name
    self.body = await get(described.body.id)
    self.rotor = await get(described.rotor.id)
    self.buckets = buckets
    self._settings = described.settings

  # -- lifecycle ---------------------------------------------------------------------------------

  async def setup(self) -> None:
    await self.server.service.setup(mpb.Empty())
    await self.create_resources()

  async def stop(self) -> None:
    """Nothing to stop here: the device is the server's, and stays set up."""

  # -- what the device reports ---------------------------------------------------------------------

  async def request_version(self) -> Dict[str, str]:
    return dict((await self.server.service.request_version(mpb.Empty())).fields)

  async def request_homed(self) -> bool:
    return (await self.server.service.request_homed(mpb.Empty())).homed

  async def request_status(self, timeout: Optional[float] = None) -> MicroSpinStatus:
    return _status(
      await self.server.service.request_status(mpb.RequestStatusRequest(timeout=timeout))
    )

  async def request_errors(self, count: int = 10) -> List[ErrorEntry]:
    stack = await self.server.service.request_errors(mpb.RequestErrorsRequest(count=count))
    return [
      ErrorEntry(index=e.index, time=e.time, command_id=e.command_id, message=e.message)
      for e in stack.entries
    ]

  async def request_command_status(self, command_id: int) -> CommandStatus:
    request = mpb.RequestCommandStatusRequest(command_id=command_id)
    return _COMMAND_STATUSES[(await self.server.service.request_command_status(request)).status]

  async def request_spindle_velocity(self) -> float:
    return (await self.server.service.request_spindle_velocity(mpb.Empty())).rpm

  async def wait_for_spindle_stopped(
    self, timeout: Optional[float] = None, poll_interval: Optional[float] = None
  ) -> None:
    request = mpb.WaitForSpindleStoppedRequest(timeout=timeout, poll_interval=poll_interval)
    await self.server.service.wait_for_spindle_stopped(request)

  # -- motion --------------------------------------------------------------------------------------

  async def home(self) -> None:
    await self.server.service.home(mpb.Empty())

  async def present_bucket(self, bucket: Bucket) -> None:
    await self.server.service.present_bucket(mpb.PresentBucketRequest(bucket=bucket))

  async def stream_spin(
    self,
    g: float,
    duration: float,
    acceleration: Optional[float] = None,
    deceleration: Optional[float] = None,
    timeout: Optional[float] = None,
    request_id: Optional[bytes] = None,
  ) -> AsyncIterator[mpb.SpinUpdate]:
    """Spin, yielding what the spin is doing as the server reads the spindle; the last update is
    the spin finished. A stream that drops is asked for again by its request id.

    Args:
      request_id: 1 to 16 bytes naming this spin; a new UUID's when not given. Give one to make a
        spin asked for again, from anywhere, the same spin.

    Raises:
      ConnectionError: The stream dropped more than `reconnect_attempts` times in a row.
      ConnectError: The server refused it: the request id was used for another spin, say.
    """
    request = mpb.SpinRequest(
      request_id=request_id or uuid.uuid4().bytes,
      g=g,
      duration=duration,
      acceleration=acceleration,
      deceleration=deceleration,
      timeout=timeout,
    )
    attempts = 0
    while True:
      try:
        async for update in self.server.service.spin(request):
          attempts = 0
          yield update
          if update.phase == mpb.SPIN_PHASE_FINISHED:
            return
      except ConnectError as error:
        if error.code not in _RECONNECT_CODES:
          raise
        if attempts >= self.reconnect_attempts:
          raise ConnectionError(f"the spin stream dropped: {error.message}") from error
        attempts += 1
        logger.info("[microspin] spin stream dropped (%s); asking again", error.message)
        await asyncio.sleep(min(self.reconnect_delay * 2 ** (attempts - 1), 30.0))
        continue
      raise ConnectionError("the spin stream ended before the spin finished")

  async def spin(
    self,
    g: float,
    duration: float,
    acceleration: Optional[float] = None,
    deceleration: Optional[float] = None,
    timeout: Optional[float] = None,
  ) -> None:
    async for update in self.stream_spin(
      g, duration, acceleration=acceleration, deceleration=deceleration, timeout=timeout
    ):
      if update.phase == mpb.SPIN_PHASE_FINISHED and update.HasField("error"):
        raise from_error(update.error)

  async def watch_spin(self, request_id: bytes) -> AsyncIterator[mpb.SpinUpdate]:
    """The spin with this request id, as `stream_spin` yields it, from wherever it was started."""
    async for update in self.server.service.watch_spin(mpb.WatchSpinRequest(request_id=request_id)):
      yield update

  async def abort(self) -> None:
    await self.server.service.abort(mpb.Empty())

  async def clear_abort(self) -> None:
    await self.server.service.clear_abort(mpb.Empty())

  async def reset(self, timeout: Optional[float] = None) -> MicroSpinStatus:
    return _status(await self.server.service.reset(mpb.ResetRequest(timeout=timeout)))
