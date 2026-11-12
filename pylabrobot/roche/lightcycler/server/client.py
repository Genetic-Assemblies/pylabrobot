"""A LightCycler served elsewhere, driven with the same methods as one in this process.

`LightCycler480(lightcycler_server=url)` is a `RemoteLightCycler480`: every public coroutine is a
call to the LightCycler server, and what a call raises on the server, the client raises, as the same
class.

An experiment's id is made here when none is given, before the server is asked, so a start retried
is the same start. `run_experiment` and `wait_for_experiment` stream the experiment, and if the
stream drops they ask for it again by its id, which the server does not start twice; so an
experiment is never lost or doubled by a network that comes and goes, and the reads it took while
the client was away arrive with the next update.
"""

import asyncio
import logging
from typing import (
  Any,
  AsyncIterator,
  Awaitable,
  Callable,
  List,
  Mapping,
  Optional,
  TypeVar,
  Union,
)

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext
from pyqwest import Client

from pylabrobot.legacy.thermocycling.standard import Protocol
from pylabrobot.resources.server.asgi_transport import ASGITransport

from ..device import (
  Acquisition,
  Experiment,
  ExperimentSummary,
  LightCycler480,
  LightCyclerStatus,
  _experiment_id,
)
from ..driver import LightCycler480Driver, LogEntry, TrayState
from ..errors import ExperimentFailedError
from ..tray_button import TrayButton
from .errors import from_connect_error
from .serve import (
  acquisition_from,
  experiment_from,
  log_from,
  protocol_message,
  status_from,
  summary_from,
  tray_from,
)
from .v1 import lightcycler_pb2 as pb
from .v1.lightcycler_connect import LightCycler480ServiceClient

logger = logging.getLogger(__name__)

REQ = TypeVar("REQ")
RES = TypeVar("RES")

_IN_PROCESS = "http://in-process"

# The codes a dropped connection comes as, after which an experiment is asked for again.
_RECONNECT_CODES = (Code.UNAVAILABLE, Code.UNKNOWN)


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


class LightCyclerServer:
  """A connection to a LightCycler server.

  Attributes:
    service: the server's `LightCycler480Service`.
  """

  def __init__(self, address: str, http: Client, headers: Optional[Mapping[str, str]] = None):
    interceptors: List[Any] = [_Errors()]
    if headers:
      interceptors.append(_Headers(headers))
    self.service = LightCycler480ServiceClient(address, http_client=http, interceptors=interceptors)

  @classmethod
  def connect(cls, url: str, headers: Optional[Mapping[str, str]] = None) -> "LightCyclerServer":
    """A LightCycler server served at `url`, "http://lab-qpcr:8097" say.

    Args:
      headers: sent with every call: the credentials whatever the server sits behind asks for.
    """
    return cls(url, Client(), headers=headers)

  @classmethod
  def in_process(cls, app: Any) -> "LightCyclerServer":
    """A LightCycler server's application in this process, spoken to without a socket."""
    return cls(_IN_PROCESS, Client(transport=ASGITransport(app)))

  async def close(self) -> None:
    await self.service.close()


class RemoteLightCycler480(LightCycler480):
  """A LightCycler served by a LightCycler server: the same methods, each a call to it.

  How the server reaches the instrument and presses its tray button is the server's.
  """

  def __init__(
    self,
    host: Optional[str] = None,
    port: int = LightCycler480Driver.DEFAULT_PORT,
    simulation: bool = False,
    driver: Optional[LightCycler480Driver] = None,
    tray_button: Optional[TrayButton] = None,
    lightcycler_server: Union[str, LightCyclerServer, None] = None,
    reconnect_attempts: int = 5,
    reconnect_delay: float = 1.0,
  ) -> None:
    """
    Args:
      host: not given: the server decides how it reaches the instrument.
      port: not given, as `host`.
      simulation: not given, as `host`.
      driver: not given, as `host`.
      tray_button: not given, as `host`.
      lightcycler_server: the LightCycler server, or its URL.
      reconnect_attempts: how many times in a row a dropped experiment stream is asked for again.
      reconnect_delay: how long before asking again the first time, in seconds; it doubles each
        time after, up to 30 s.
    """
    if (
      host is not None
      or simulation
      or driver is not None
      or tray_button is not None
      or port != LightCycler480Driver.DEFAULT_PORT
    ):
      raise ValueError(
        "a served LightCycler is what its server makes it: host, port, simulation, driver and "
        "tray_button cannot be given with lightcycler_server"
      )
    if lightcycler_server is None:
      raise ValueError("a served LightCycler needs lightcycler_server")
    if isinstance(lightcycler_server, str):
      lightcycler_server = LightCyclerServer.connect(lightcycler_server)
    self.server = lightcycler_server
    self.tray_button = None
    self.reconnect_attempts = reconnect_attempts
    self.reconnect_delay = reconnect_delay

  @property
  def driver(self) -> LightCycler480Driver:
    raise RuntimeError("a served LightCycler's driver is on its server")

  # -- lifecycle ---------------------------------------------------------------------------------

  async def setup(self) -> None:
    await self.server.service.setup(pb.Empty())

  async def stop(self) -> None:
    """Nothing to stop here: the instrument is the server's, and stays connected."""

  # -- what the instrument reports ------------------------------------------------------------------

  async def request_status(self) -> LightCyclerStatus:
    return status_from(await self.server.service.request_status(pb.Empty()))

  async def request_tray_state(self) -> TrayState:
    return tray_from(await self.server.service.request_tray_state(pb.Empty()))

  async def request_logs(self, since_id: int = 0, limit: int = 100) -> List[LogEntry]:
    request = pb.RequestLogsRequest(since_id=since_id, limit=limit)
    return [log_from(e) for e in (await self.server.service.request_logs(request)).entries]

  # -- the tray ---------------------------------------------------------------------------------------

  async def open_tray(self, timeout: Optional[float] = None) -> None:
    await self.server.service.open_tray(pb.MoveTrayRequest(timeout=timeout))

  async def close_tray(self, timeout: Optional[float] = None) -> None:
    await self.server.service.close_tray(pb.MoveTrayRequest(timeout=timeout))

  # -- experiments --------------------------------------------------------------------------------

  def _request(
    self, protocol: Protocol, well_count: int, volume: int, experiment_id: Optional[str]
  ) -> pb.ExperimentRequest:
    return pb.ExperimentRequest(
      protocol=protocol_message(protocol),
      well_count=well_count,
      volume=volume,
      experiment_id=_experiment_id(experiment_id),
    )

  async def start_experiment(
    self,
    protocol: Protocol,
    well_count: int = 384,
    volume: int = 20,
    experiment_id: Optional[str] = None,
  ) -> str:
    request = self._request(protocol, well_count, volume, experiment_id)
    return (await self.server.service.start_experiment(request)).experiment_id

  async def _follow(
    self, stream: Callable[[], AsyncIterator[pb.ExperimentUpdate]]
  ) -> AsyncIterator[Experiment]:
    """Each update `stream` gives, as the experiment with every read so far, asking again when it
    drops; the first update of each stream holds every read so far."""
    attempts = 0
    while True:
      acquisitions: List[Acquisition] = []
      try:
        async for update in stream():
          attempts = 0
          acquisitions.extend(acquisition_from(a) for a in update.experiment.acquisitions)
          experiment = experiment_from(update.experiment, acquisitions)
          yield experiment
          if experiment.finished:
            return
      except ConnectError as error:
        if error.code not in _RECONNECT_CODES:
          raise
        if attempts >= self.reconnect_attempts:
          raise ConnectionError(f"the experiment stream dropped: {error.message}") from error
        attempts += 1
        logger.info("[lightcycler] experiment stream dropped (%s); asking again", error.message)
        await asyncio.sleep(min(self.reconnect_delay * 2 ** (attempts - 1), 30.0))
        continue
      raise ConnectionError("the experiment stream ended before the experiment finished")

  @staticmethod
  async def _last(updates: AsyncIterator[Experiment]) -> Experiment:
    last: Optional[Experiment] = None
    async for experiment in updates:
      last = experiment
    assert last is not None
    if last.status == "error":
      raise ExperimentFailedError(last.id, last.error or "unknown")
    return last

  async def run_experiment(
    self,
    protocol: Protocol,
    well_count: int = 384,
    volume: int = 20,
    experiment_id: Optional[str] = None,
  ) -> Experiment:
    request = self._request(protocol, well_count, volume, experiment_id)
    return await self._last(self._follow(lambda: self.server.service.run_experiment(request)))

  async def watch_experiment(self, experiment_id: str) -> AsyncIterator[Experiment]:
    request = pb.ExperimentId(experiment_id=experiment_id)
    async for experiment in self._follow(lambda: self.server.service.watch_experiment(request)):
      yield experiment

  async def wait_for_experiment(
    self, experiment_id: str, timeout: Optional[float] = None
  ) -> Experiment:
    waiting = asyncio.ensure_future(self._last(self.watch_experiment(experiment_id)))
    done, _ = await asyncio.wait({waiting}, timeout=timeout)
    if not done:
      waiting.cancel()
      await asyncio.gather(waiting, return_exceptions=True)
      raise TimeoutError(
        f"experiment {experiment_id} had not finished within {timeout} s; it runs on"
      )
    return waiting.result()

  async def get_experiment(self, experiment_id: str) -> Experiment:
    request = pb.ExperimentId(experiment_id=experiment_id)
    return experiment_from(await self.server.service.get_experiment(request))

  async def list_experiments(self, limit: int = 50) -> List[ExperimentSummary]:
    response = await self.server.service.list_experiments(pb.ListExperimentsRequest(limit=limit))
    return [summary_from(s) for s in response.experiments]
