"""Serving a MicroSpin: one Connect application for its service.

The server owns every spin it starts. A spin runs as a task of the server's, not of the call that
asked for it, so a client that goes away does not stop it; the spin is kept by its request id, and
`Spin` or `WatchSpin` with that id streams it again, or its result once it has finished.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import OrderedDict
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Tuple, cast

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext
from google.protobuf import json_format

from pylabrobot.resources.server.memory import asgi_app as resource_server_app
from pylabrobot.resources.server.v1 import types_pb2 as pb

from ..device import MicroSpin
from ..driver import MicroSpinDriver
from .errors import to_connect_error, to_error
from .v1 import microspin_pb2 as mpb
from .v1.microspin_connect import MicroSpinServiceASGIApplication

logger = logging.getLogger(__name__)

# An ASGI 3 application.
ASGIApp = Callable[[Dict[str, Any], Any, Any], Awaitable[None]]

# How many finished spins are kept for `WatchSpin`, newest last.
KEPT_SPINS = 64
# How often a running spin's stream reads the spindle, in seconds.
DEFAULT_PROGRESS_INTERVAL = 2.0

_COMMAND_STATUSES: Dict[str, mpb.CommandStatus] = {
  "OK": mpb.COMMAND_STATUS_OK,
  "ERROR": mpb.COMMAND_STATUS_ERROR,
  "ABORTED": mpb.COMMAND_STATUS_ABORTED,
  "FAIL": mpb.COMMAND_STATUS_FAIL,
  "RUNNING": mpb.COMMAND_STATUS_RUNNING,
}


# -- settings ------------------------------------------------------------------------------------


def read_settings(path: str) -> mpb.Settings:
  """The settings in a JSON file, by their proto names: `{"default_acceleration": 0.8}`."""
  with open(path) as f:
    return json_format.ParseDict(json.load(f), mpb.Settings())


def put_in_place(driver: MicroSpinDriver, settings: Optional[mpb.Settings]) -> None:
  """Set the driver's defaults from `settings`; those not given keep the code's."""
  if settings is None:
    return
  if settings.HasField("default_acceleration"):
    driver.default_acceleration = settings.default_acceleration
  if settings.HasField("default_deceleration"):
    driver.default_deceleration = settings.default_deceleration
  if settings.HasField("default_timeout"):
    driver.default_timeout = settings.default_timeout
  if settings.HasField("default_home_timeout"):
    driver.default_home_timeout = settings.default_home_timeout
  if settings.HasField("default_present_timeout"):
    driver.default_present_timeout = settings.default_present_timeout
  if settings.HasField("default_spin_timeout_margin"):
    driver.default_spin_timeout_margin = settings.default_spin_timeout_margin
  if settings.HasField("default_abort_timeout"):
    driver.default_abort_timeout = settings.default_abort_timeout
  if settings.HasField("default_spindle_stop_timeout"):
    driver.default_spindle_stop_timeout = settings.default_spindle_stop_timeout
  if settings.HasField("default_spindle_poll_interval"):
    driver.default_spindle_poll_interval = settings.default_spindle_poll_interval


def settings_in_force(driver: MicroSpinDriver) -> mpb.Settings:
  """Every default the driver uses now."""
  return mpb.Settings(
    default_acceleration=driver.default_acceleration,
    default_deceleration=driver.default_deceleration,
    default_timeout=driver.default_timeout,
    default_home_timeout=driver.default_home_timeout,
    default_present_timeout=driver.default_present_timeout,
    default_spin_timeout_margin=driver.default_spin_timeout_margin,
    default_abort_timeout=driver.default_abort_timeout,
    default_spindle_stop_timeout=driver.default_spindle_stop_timeout,
    default_spindle_poll_interval=driver.default_spindle_poll_interval,
  )


# -- spins ---------------------------------------------------------------------------------------


class _SpinJob:
  """One spin the server started: the task running it, and what it has done so far."""

  def __init__(self, microspin: MicroSpin, request: mpb.SpinRequest, interval: float) -> None:
    self.request = request
    self._microspin = microspin
    self._interval = interval
    loop = asyncio.get_running_loop()
    self._started = loop.time()
    self._changed = asyncio.Condition()
    self._revision = 0
    self.latest = mpb.SpinUpdate(request=request, phase=mpb.SPIN_PHASE_RUNNING)
    self.task = asyncio.create_task(self._run())

  @property
  def finished(self) -> bool:
    return self.latest.phase == mpb.SPIN_PHASE_FINISHED

  async def _publish(self, update: mpb.SpinUpdate) -> None:
    async with self._changed:
      self.latest = update
      self._revision += 1
      self._changed.notify_all()

  def _update(self, rpm: float) -> mpb.SpinUpdate:
    elapsed = asyncio.get_running_loop().time() - self._started
    return mpb.SpinUpdate(
      request=self.request, phase=mpb.SPIN_PHASE_RUNNING, elapsed=elapsed, rpm=rpm
    )

  async def _sample(self, stop: asyncio.Event) -> None:
    """Read the spindle every interval and publish it, until `stop` is set.

    Stopped by an event, not by cancelling: on Python 3.10 a cancel that lands as a read completes
    can be lost inside `asyncio.wait_for`, and the sampler would run on.
    """
    while True:
      try:
        await asyncio.wait_for(stop.wait(), timeout=self._interval)
        return
      except asyncio.TimeoutError:
        pass
      try:
        rpm = await self._microspin.request_spindle_velocity()
      except Exception as error:
        logger.debug("[microspin server] could not read the spindle: %s", error)
        continue
      if stop.is_set():
        return
      await self._publish(self._update(rpm))

  async def _run(self) -> None:
    request = self.request
    stop = asyncio.Event()
    sampler = asyncio.create_task(self._sample(stop))
    error: Optional[BaseException] = None
    try:
      await self._microspin.spin(
        request.g,
        request.duration,
        acceleration=request.acceleration if request.HasField("acceleration") else None,
        deceleration=request.deceleration if request.HasField("deceleration") else None,
        timeout=request.timeout if request.HasField("timeout") else None,
      )
    except Exception as raised:
      error = raised
    finally:
      stop.set()
      await asyncio.gather(sampler, return_exceptions=True)
    last = self._update(self.latest.rpm)
    last.phase = mpb.SPIN_PHASE_FINISHED
    if error is not None:
      last.error.CopyFrom(to_error(error))
    else:
      last.rpm = 0.0
    await self._publish(last)

  async def stream(self) -> AsyncIterator[mpb.SpinUpdate]:
    """The spin as it is, then each change, ending once it has finished."""
    seen = -1
    while True:
      async with self._changed:
        if self._revision == seen:
          await self._changed.wait()
        seen = self._revision
        update = self.latest
      yield update
      if update.phase == mpb.SPIN_PHASE_FINISHED:
        return


def _same_spin(a: mpb.SpinRequest, b: mpb.SpinRequest) -> bool:
  return a.SerializeToString(deterministic=True) == b.SerializeToString(deterministic=True)


# -- the service ---------------------------------------------------------------------------------


def _ref(resource_id: bytes) -> pb.ResourceRef:
  return pb.ResourceRef(id=resource_id)


class MicroSpinService:
  """Each call made on one `MicroSpin`."""

  def __init__(
    self,
    microspin: MicroSpin,
    settings: Optional[mpb.Settings] = None,
    progress_interval: float = DEFAULT_PROGRESS_INTERVAL,
  ) -> None:
    self.microspin = microspin
    self.settings = settings
    self.progress_interval = progress_interval
    self._spins: "OrderedDict[bytes, _SpinJob]" = OrderedDict()
    put_in_place(microspin.driver, settings)

  async def _call(self, work: Callable[[], Awaitable[Any]]) -> Any:
    try:
      return await work()
    except ConnectError:
      raise
    except Exception as error:
      raise to_connect_error(error) from error

  async def describe(self, request: mpb.Empty, ctx: RequestContext) -> mpb.Description:
    microspin = self.microspin
    if microspin.body is None or microspin.rotor is None:
      await self._call(microspin.create_resources)
    assert microspin.body is not None and microspin.rotor is not None
    return mpb.Description(
      name=microspin.name,
      body=_ref(microspin.body.id),
      rotor=_ref(microspin.rotor.id),
      bucket_1=_ref(microspin.buckets[1].id),
      bucket_2=_ref(microspin.buckets[2].id),
      settings=settings_in_force(microspin.driver),
    )

  async def setup(self, request: mpb.Empty, ctx: RequestContext) -> mpb.Empty:
    await self._call(self.microspin.setup)
    put_in_place(self.microspin.driver, self.settings)
    return mpb.Empty()

  async def request_version(self, request: mpb.Empty, ctx: RequestContext) -> mpb.Version:
    fields = await self._call(self.microspin.request_version)
    return mpb.Version(fields=fields)

  async def request_homed(self, request: mpb.Empty, ctx: RequestContext) -> mpb.Homed:
    return mpb.Homed(homed=await self._call(self.microspin.request_homed))

  async def request_status(
    self, request: mpb.RequestStatusRequest, ctx: RequestContext
  ) -> mpb.Status:
    timeout = request.timeout if request.HasField("timeout") else None
    status = await self._call(lambda: self.microspin.request_status(timeout=timeout))
    return mpb.Status(spindle_position=status.spindle_position, door_position=status.door_position)

  async def request_errors(
    self, request: mpb.RequestErrorsRequest, ctx: RequestContext
  ) -> mpb.ErrorStack:
    count = request.count if request.HasField("count") else 10
    entries = await self._call(lambda: self.microspin.request_errors(count))
    return mpb.ErrorStack(
      entries=[
        mpb.ErrorEntry(
          index=entry.index, time=entry.time, command_id=entry.command_id, message=entry.message
        )
        for entry in entries
      ]
    )

  async def request_command_status(
    self, request: mpb.RequestCommandStatusRequest, ctx: RequestContext
  ) -> mpb.CommandStatusResponse:
    status = await self._call(lambda: self.microspin.request_command_status(request.command_id))
    return mpb.CommandStatusResponse(status=_COMMAND_STATUSES[status])

  async def request_spindle_velocity(
    self, request: mpb.Empty, ctx: RequestContext
  ) -> mpb.SpindleVelocity:
    return mpb.SpindleVelocity(rpm=await self._call(self.microspin.request_spindle_velocity))

  async def wait_for_spindle_stopped(
    self, request: mpb.WaitForSpindleStoppedRequest, ctx: RequestContext
  ) -> mpb.Empty:
    timeout = request.timeout if request.HasField("timeout") else None
    interval = request.poll_interval if request.HasField("poll_interval") else None
    await self._call(
      lambda: self.microspin.wait_for_spindle_stopped(timeout=timeout, poll_interval=interval)
    )
    return mpb.Empty()

  async def home(self, request: mpb.Empty, ctx: RequestContext) -> mpb.Empty:
    await self._call(self.microspin.home)
    return mpb.Empty()

  async def present_bucket(
    self, request: mpb.PresentBucketRequest, ctx: RequestContext
  ) -> mpb.Empty:
    bucket = request.bucket
    if bucket == 1:
      await self._call(lambda: self.microspin.present_bucket(1))
    elif bucket == 2:
      await self._call(lambda: self.microspin.present_bucket(2))
    else:
      raise to_connect_error(ValueError(f"bucket must be 1 or 2, got {bucket}"))
    return mpb.Empty()

  def _job(self, request: mpb.SpinRequest) -> _SpinJob:
    """The spin with this request id, started when there is none."""
    request_id = request.request_id
    if not 1 <= len(request_id) <= 16:
      raise to_connect_error(ValueError("request_id must be 1 to 16 bytes"))
    job = self._spins.get(request_id)
    if job is not None:
      if not _same_spin(job.request, request):
        raise ConnectError(
          Code.ALREADY_EXISTS, "this request_id was used for a spin with other arguments"
        )
      return job
    job = _SpinJob(self.microspin, request, self.progress_interval)
    self._spins[request_id] = job
    finished = [key for key, kept in self._spins.items() if kept.finished]
    for key in finished[: max(0, len(finished) - KEPT_SPINS)]:
      del self._spins[key]
    return job

  async def spin(
    self, request: mpb.SpinRequest, ctx: RequestContext
  ) -> AsyncIterator[mpb.SpinUpdate]:
    async for update in self._job(request).stream():
      yield update

  async def watch_spin(
    self, request: mpb.WatchSpinRequest, ctx: RequestContext
  ) -> AsyncIterator[mpb.SpinUpdate]:
    job = self._spins.get(request.request_id)
    if job is None:
      raise ConnectError(Code.NOT_FOUND, "no spin with this request_id")
    async for update in job.stream():
      yield update

  async def abort(self, request: mpb.Empty, ctx: RequestContext) -> mpb.Empty:
    await self._call(self.microspin.abort)
    return mpb.Empty()

  async def clear_abort(self, request: mpb.Empty, ctx: RequestContext) -> mpb.Empty:
    await self._call(self.microspin.clear_abort)
    return mpb.Empty()

  async def reset(self, request: mpb.ResetRequest, ctx: RequestContext) -> mpb.Status:
    timeout = request.timeout if request.HasField("timeout") else None
    status = await self._call(lambda: self.microspin.reset(timeout=timeout))
    return mpb.Status(spindle_position=status.spindle_position, door_position=status.door_position)


def microspin_server_app(
  microspin: MicroSpin,
  settings: Optional[mpb.Settings] = None,
  progress_interval: float = DEFAULT_PROGRESS_INTERVAL,
) -> ASGIApp:
  """The ASGI application serving one MicroSpin.

  Args:
    microspin: the device to serve.
    settings: the defaults it uses where a call names none; those not given keep the code's.
    progress_interval: how often a spin's stream reads the spindle, in seconds.
  """
  service = MicroSpinService(microspin, settings, progress_interval)
  return cast(ASGIApp, MicroSpinServiceASGIApplication(service))


async def serve(
  microspin: MicroSpin,
  host: str = "127.0.0.1",
  port: int = 8082,
  resource_port: Optional[int] = None,
  settings: Optional[mpb.Settings] = None,
) -> None:
  """Serve a MicroSpin until cancelled. Needs uvicorn, the `resource-server` extra.

  Args:
    microspin: the device to serve.
    host: the address to listen on.
    port: the port the MicroSpin server listens on.
    resource_port: a port to serve the device's resource server on as well, when it is held in this
      process; not served when not given.
    settings: as `microspin_server_app` takes them.

  Raises:
    ValueError: Given a `resource_port` for a resource server that is not held in this process.
  """
  import uvicorn

  apps: List[Tuple[ASGIApp, int]] = [(microspin_server_app(microspin, settings), port)]
  if resource_port is not None:
    memory = microspin.resource_server.memory
    if memory is None:
      raise ValueError("only a resource server held in this process can be served with it")
    apps.append((resource_server_app(memory), resource_port))
  await asyncio.gather(
    *(uvicorn.Server(uvicorn.Config(app, host=host, port=p)).serve() for app, p in apps)
  )
