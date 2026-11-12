"""Serving a LightCycler 480: one Connect application for its service.

An experiment runs on the device, not in the call that asked for it, so a client that goes away does
not stop it. It is kept by its id, and `RunExperiment` or `WatchExperiment` with that id streams it
again, or its result once it has finished. A stream sends the experiment each time it changes and
every few seconds besides, so nothing between the server and a client sees an idle call and cuts it.
"""

import asyncio
import logging
from typing import (
  Any,
  AsyncIterator,
  Awaitable,
  Callable,
  Dict,
  Literal,
  Optional,
  Sequence,
  TypeVar,
  cast,
)

from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext

from pylabrobot.legacy.thermocycling.standard import Protocol, Stage, Step

from ..device import (
  Acquisition,
  Experiment,
  ExperimentStatus,
  ExperimentSummary,
  LightCycler480,
  LightCyclerStatus,
  LightCyclerStep,
  as_lightcycler_protocol,
)
from ..driver import LogEntry, TrayState
from .errors import to_connect_error
from .v1 import lightcycler_pb2 as pb
from .v1.lightcycler_connect import LightCycler480ServiceASGIApplication

logger = logging.getLogger(__name__)

# An ASGI 3 application.
ASGIApp = Callable[[Dict[str, Any], Any, Any], Awaitable[None]]

DEFAULT_PORT = 8097
# How often a stream sends an experiment that has not changed, in seconds.
DEFAULT_PROGRESS_INTERVAL = 5.0

T = TypeVar("T")

# -- messages, both ways ---------------------------------------------------------------------------

_STATUSES: Dict[str, "pb.ExperimentStatus"] = {
  "pending": pb.EXPERIMENT_STATUS_PENDING,
  "running": pb.EXPERIMENT_STATUS_RUNNING,
  "complete": pb.EXPERIMENT_STATUS_COMPLETE,
  "error": pb.EXPERIMENT_STATUS_ERROR,
}
_STATUS_NAMES: Dict[int, ExperimentStatus] = {
  pb.EXPERIMENT_STATUS_PENDING: "pending",
  pb.EXPERIMENT_STATUS_RUNNING: "running",
  pb.EXPERIMENT_STATUS_COMPLETE: "complete",
  pb.EXPERIMENT_STATUS_ERROR: "error",
}


def protocol_message(protocol: Protocol) -> pb.Protocol:
  message = pb.Protocol()
  for stage in as_lightcycler_protocol(protocol).stages:
    stage_message = message.stages.add(repeats=stage.repeats)
    for step in stage.steps:
      assert isinstance(step, LightCyclerStep)
      stage_message.steps.add(
        temperature=step.temperature,
        hold_seconds=step.hold_seconds,
        rate=step.rate,
        acquire=step.acquire,
        filter_set=step.filter_set,
        exposure=step.exposure,
      )
  return message


def protocol_from(message: pb.Protocol) -> Protocol:
  stages = []
  for stage in message.stages:
    steps: list[Step] = []
    for step in stage.steps:
      made = LightCyclerStep(
        temperature=list(step.temperature),
        hold_seconds=step.hold_seconds,
        rate=step.rate if step.HasField("rate") else None,
        acquire=step.acquire,
      )
      if step.HasField("filter_set"):
        made.filter_set = step.filter_set  # type: ignore[assignment]
      if step.HasField("exposure"):
        made.exposure = step.exposure
      steps.append(made)
    stages.append(Stage(steps=steps, repeats=stage.repeats))
  return Protocol(stages=stages)


def acquisition_message(acquisition: Acquisition) -> pb.Acquisition:
  return pb.Acquisition(
    number=acquisition.number,
    stage_index=acquisition.stage_index,
    cycle=acquisition.cycle,
    step_index=acquisition.step_index,
    temperature=acquisition.temperature,
    time=acquisition.time,
    filter_set=acquisition.filter_set,
    ref_channel=acquisition.ref_channel,
    values=acquisition.values,
  )


def acquisition_from(message: pb.Acquisition) -> Acquisition:
  return Acquisition(
    number=message.number,
    stage_index=message.stage_index,
    cycle=message.cycle,
    step_index=message.step_index,
    temperature=message.temperature,
    time=message.time,
    filter_set=message.filter_set,
    ref_channel=message.ref_channel,
    values=tuple(message.values),
  )


def experiment_message(
  experiment: Experiment, acquisitions: Optional[Sequence[Acquisition]] = None
) -> pb.Experiment:
  """`experiment` as a message, with `acquisitions` in place of its reads when given."""
  reads = experiment.acquisitions if acquisitions is None else acquisitions
  return pb.Experiment(
    id=experiment.id,
    status=_STATUSES[experiment.status],
    protocol=protocol_message(experiment.protocol),
    well_count=experiment.well_count,
    volume=experiment.volume,
    created_at=experiment.created_at,
    finished_at=experiment.finished_at,
    error=experiment.error,
    acquisitions_total=experiment.acquisitions_total,
    acquisitions=[acquisition_message(a) for a in reads],
  )


def experiment_from(
  message: pb.Experiment, acquisitions: Optional[Sequence[Acquisition]] = None
) -> Experiment:
  """The experiment a message holds, with `acquisitions` in place of its reads when given."""
  reads = (
    tuple(acquisition_from(a) for a in message.acquisitions)
    if acquisitions is None
    else tuple(acquisitions)
  )
  return Experiment(
    id=message.id,
    status=_STATUS_NAMES[message.status],
    protocol=protocol_from(message.protocol),
    well_count=message.well_count,
    volume=message.volume,
    created_at=message.created_at,
    finished_at=message.finished_at if message.HasField("finished_at") else None,
    error=message.error if message.HasField("error") else None,
    acquisitions_total=message.acquisitions_total,
    acquisitions=reads,
  )


def summary_message(summary: ExperimentSummary) -> pb.ExperimentSummary:
  return pb.ExperimentSummary(
    id=summary.id,
    status=_STATUSES[summary.status],
    created_at=summary.created_at,
    finished_at=summary.finished_at,
    error=summary.error,
    acquisitions_done=summary.acquisitions_done,
    acquisitions_total=summary.acquisitions_total,
  )


def summary_from(message: pb.ExperimentSummary) -> ExperimentSummary:
  return ExperimentSummary(
    id=message.id,
    status=_STATUS_NAMES[message.status],
    created_at=message.created_at,
    finished_at=message.finished_at if message.HasField("finished_at") else None,
    error=message.error if message.HasField("error") else None,
    acquisitions_done=message.acquisitions_done,
    acquisitions_total=message.acquisitions_total,
  )


def status_message(status: LightCyclerStatus) -> pb.Status:
  return pb.Status(
    state=status.state,
    controller=status.controller,
    firmware_version=status.firmware_version,
    running_experiment=status.running_experiment,
  )


def status_from(message: pb.Status) -> LightCyclerStatus:
  return LightCyclerStatus(
    state=message.state,
    controller=message.controller,
    firmware_version=message.firmware_version,
    running_experiment=(
      message.running_experiment if message.HasField("running_experiment") else None
    ),
  )


def tray_message(tray: TrayState) -> pb.TrayState:
  return pb.TrayState(open=tray.open, plate_loaded=tray.plate_loaded, barcode=tray.barcode)


def tray_from(message: pb.TrayState) -> TrayState:
  return TrayState(open=message.open, plate_loaded=message.plate_loaded, barcode=message.barcode)


def log_message(entry: LogEntry) -> pb.LogEntry:
  return pb.LogEntry(
    id=entry.id,
    received_at=entry.received_at,
    kind=entry.kind,
    timestamp=entry.timestamp,
    code=entry.code,
    data=entry.data,
  )


def log_from(message: pb.LogEntry) -> LogEntry:
  kind: Literal["event", "trace"] = "event" if message.kind == "event" else "trace"
  return LogEntry(
    id=message.id,
    received_at=message.received_at,
    kind=kind,
    timestamp=message.timestamp,
    code=message.code,
    data=tuple(message.data),
  )


# -- the service ---------------------------------------------------------------------------------


class LightCycler480Service:
  """Each call made on one `LightCycler480`."""

  def __init__(
    self, lightcycler: LightCycler480, progress_interval: float = DEFAULT_PROGRESS_INTERVAL
  ) -> None:
    self.lightcycler = lightcycler
    self.progress_interval = progress_interval

  async def _call(self, work: Callable[[], Awaitable[T]]) -> T:
    try:
      return await work()
    except ConnectError:
      raise
    except Exception as error:
      raise to_connect_error(error) from error

  async def setup(self, request: pb.Empty, ctx: RequestContext) -> pb.Empty:
    await self._call(self.lightcycler.setup)
    return pb.Empty()

  async def request_status(self, request: pb.Empty, ctx: RequestContext) -> pb.Status:
    return status_message(await self._call(self.lightcycler.request_status))

  async def request_tray_state(self, request: pb.Empty, ctx: RequestContext) -> pb.TrayState:
    return tray_message(await self._call(self.lightcycler.request_tray_state))

  async def request_logs(self, request: pb.RequestLogsRequest, ctx: RequestContext) -> pb.Logs:
    since_id = request.since_id if request.HasField("since_id") else 0
    limit = request.limit if request.HasField("limit") else 100
    entries = await self._call(lambda: self.lightcycler.request_logs(since_id, limit))
    return pb.Logs(entries=[log_message(e) for e in entries])

  def _timeout(self, request: pb.MoveTrayRequest) -> Optional[float]:
    return request.timeout if request.HasField("timeout") else None

  async def open_tray(self, request: pb.MoveTrayRequest, ctx: RequestContext) -> pb.Empty:
    await self._call(lambda: self.lightcycler.open_tray(timeout=self._timeout(request)))
    return pb.Empty()

  async def close_tray(self, request: pb.MoveTrayRequest, ctx: RequestContext) -> pb.Empty:
    await self._call(lambda: self.lightcycler.close_tray(timeout=self._timeout(request)))
    return pb.Empty()

  async def _start(self, request: pb.ExperimentRequest) -> str:
    return await self._call(
      lambda: self.lightcycler.start_experiment(
        protocol_from(request.protocol),
        well_count=request.well_count if request.HasField("well_count") else 384,
        volume=request.volume if request.HasField("volume") else 20,
        experiment_id=request.experiment_id if request.HasField("experiment_id") else None,
      )
    )

  async def start_experiment(
    self, request: pb.ExperimentRequest, ctx: RequestContext
  ) -> pb.StartExperimentResponse:
    return pb.StartExperimentResponse(experiment_id=await self._start(request))

  async def _stream(self, experiment_id: str) -> AsyncIterator[pb.ExperimentUpdate]:
    """The experiment as it is, then each change, and again every `progress_interval` seconds,
    ending once it has finished. Each update holds the reads not yet sent on this stream."""
    updates = self.lightcycler.watch_experiment(experiment_id).__aiter__()
    following: Optional["asyncio.Future[Experiment]"] = None
    last: Optional[Experiment] = None
    sent = 0
    try:
      while True:
        if following is None:
          following = asyncio.ensure_future(updates.__anext__())
        done, _ = await asyncio.wait({following}, timeout=self.progress_interval)
        if not done:
          if last is not None:
            yield pb.ExperimentUpdate(experiment=experiment_message(last, ()))
          continue
        try:
          experiment = following.result()
        except StopAsyncIteration:
          return
        except Exception as error:
          raise to_connect_error(error) from error
        following = None
        yield pb.ExperimentUpdate(
          experiment=experiment_message(experiment, experiment.acquisitions[sent:])
        )
        sent, last = len(experiment.acquisitions), experiment
        if experiment.finished:
          return
    finally:
      if following is not None and not following.done():
        following.cancel()
        await asyncio.gather(following, return_exceptions=True)
      await cast(Any, updates).aclose()

  async def run_experiment(
    self, request: pb.ExperimentRequest, ctx: RequestContext
  ) -> AsyncIterator[pb.ExperimentUpdate]:
    experiment_id = await self._start(request)
    async for update in self._stream(experiment_id):
      yield update

  async def watch_experiment(
    self, request: pb.ExperimentId, ctx: RequestContext
  ) -> AsyncIterator[pb.ExperimentUpdate]:
    async for update in self._stream(request.experiment_id):
      yield update

  async def get_experiment(self, request: pb.ExperimentId, ctx: RequestContext) -> pb.Experiment:
    experiment = await self._call(lambda: self.lightcycler.get_experiment(request.experiment_id))
    return experiment_message(experiment)

  async def list_experiments(
    self, request: pb.ListExperimentsRequest, ctx: RequestContext
  ) -> pb.ExperimentList:
    limit = request.limit if request.HasField("limit") else 50
    summaries = await self._call(lambda: self.lightcycler.list_experiments(limit))
    return pb.ExperimentList(experiments=[summary_message(s) for s in summaries])


def lightcycler_server_app(
  lightcycler: LightCycler480, progress_interval: float = DEFAULT_PROGRESS_INTERVAL
) -> ASGIApp:
  """The ASGI application serving one LightCycler.

  Args:
    lightcycler: the instrument to serve.
    progress_interval: how often a stream sends an experiment that has not changed, in seconds.
  """
  service = LightCycler480Service(lightcycler, progress_interval)
  return cast(ASGIApp, LightCycler480ServiceASGIApplication(service))


async def serve(
  lightcycler: LightCycler480, host: str = "127.0.0.1", port: int = DEFAULT_PORT
) -> None:
  """Serve a LightCycler until cancelled. Needs uvicorn, the `resource-server` extra.

  Args:
    lightcycler: the instrument to serve.
    host: the address to listen on.
    port: the port to listen on.
  """
  import uvicorn

  await uvicorn.Server(
    uvicorn.Config(lightcycler_server_app(lightcycler), host=host, port=port)
  ).serve()
