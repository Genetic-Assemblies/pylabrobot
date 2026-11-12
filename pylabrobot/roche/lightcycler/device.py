"""The Roche LightCycler 480 II: its tray, and experiments run on it from a thermocycling protocol.

An experiment is a PLR thermocycling `Protocol`: stages run one after another, each its steps
`repeats` times. A step that is a `LightCyclerStep` with `acquire=True` reads every well's
fluorescence once the block is at its temperature. On the wire each repeat of a stage is a program
of its own, and a program holds all its steps for one time, so the steps of a stage must hold for
the same time.

An experiment runs on the device, not in the call that started it: `start_experiment` returns its
id at once, and `wait_for_experiment`, `watch_experiment` and `get_experiment` follow it by that id.
`run_experiment` does both. One runs at a time.
"""

import asyncio
import dataclasses
import logging
import re
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import (
  TYPE_CHECKING,
  Any,
  AsyncIterator,
  Dict,
  List,
  Literal,
  Optional,
  Sequence,
  Tuple,
  Union,
)

from pylabrobot.legacy.thermocycling.standard import Protocol, Stage, Step

from .driver import STATE_RUNNING, LightCycler480Driver, LogEntry, TrayState
from .errors import ExperimentFailedError
from .simulator import LightCycler480Simulator, SimulatedTrayButton
from .tray_button import TrayButton
from .wire import DEFAULT_EXPOSURE, DEFAULT_RAMP_RATE, ExperimentConfig, ResultData, WireStep

if TYPE_CHECKING:
  from .server.client import LightCyclerServer

logger = logging.getLogger(__name__)

# The filter sets flo4 names, by their code on the wire. Only SYBR Green (1) has been seen in a
# capture; what the others select on a device is unverified.
FilterSet = Literal["sybr_green", "hex", "rox", "cy5"]
FILTER_CODES: Dict[str, int] = {"sybr_green": 1, "hex": 2, "rox": 3, "cy5": 4}

ExperimentStatus = Literal["pending", "running", "complete", "error"]

# Where the block is taken to start when estimating how long a run ramps, in Celsius.
_START_TEMPERATURE = 25.0
_HEX_ID = re.compile(r"^[0-9A-Fa-f]{32}$")


@dataclass
class LightCyclerStep(Step):
  """A step that may read fluorescence once the block is at its temperature.

  Attributes:
    temperature: the block's temperature, in Celsius: one value, the LightCycler has one zone.
    hold_seconds: how long to hold it.
    rate: how fast to ramp to it, in Celsius per second; 5.0 when not given.
    acquire: whether to read every well's fluorescence at this step.
    filter_set: what to read with.
    exposure: in the instrument's units; 4800 in every capture.
  """

  acquire: bool = False
  filter_set: FilterSet = "sybr_green"
  exposure: int = DEFAULT_EXPOSURE

  def serialize(self) -> dict:
    return {
      **super().serialize(),
      "acquire": self.acquire,
      "filter_set": self.filter_set,
      "exposure": self.exposure,
    }


@dataclass(frozen=True)
class Acquisition:
  """One fluorescence read of every well.

  Attributes:
    number: counting from 1 in the experiment.
    stage_index: the stage it was read in, from 0.
    cycle: which repeat of that stage, from 0.
    step_index: the step of the stage it was read at, from 0.
    temperature: the block's temperature as it was read, in Celsius.
    time: since the run started, in seconds.
    filter_set: what it was read with.
    ref_channel: the instrument's reference channel value.
    values: each well's raw fluorescence, in the instrument's well order; that order has not been
      checked against well names on a device.
  """

  number: int
  stage_index: int
  cycle: int
  step_index: int
  temperature: float
  time: float
  filter_set: str
  ref_channel: int
  values: Tuple[int, ...]


@dataclass(frozen=True)
class Experiment:
  """An experiment, as it is now.

  Attributes:
    id: 32 hex digits; the instrument tags each read with it.
    status: `pending` until its run is sent, `running`, then `complete` or `error`.
    protocol: what it runs, each step a `LightCyclerStep`.
    well_count: 96 or 384.
    volume: the reaction volume, in uL.
    created_at: when it was started, in seconds since the epoch.
    finished_at: when it finished; None until it has.
    error: why it did not finish, for one whose status is `error`.
    acquisitions_total: how many reads it takes.
    acquisitions: the reads taken so far.
  """

  id: str
  status: ExperimentStatus
  protocol: Protocol
  well_count: int
  volume: int
  created_at: float
  finished_at: Optional[float]
  error: Optional[str]
  acquisitions_total: int
  acquisitions: Tuple[Acquisition, ...]

  @property
  def finished(self) -> bool:
    return self.status in ("complete", "error")


@dataclass(frozen=True)
class ExperimentSummary:
  """An experiment without its reads, as `list_experiments` gives it."""

  id: str
  status: ExperimentStatus
  created_at: float
  finished_at: Optional[float]
  error: Optional[str]
  acquisitions_done: int
  acquisitions_total: int


@dataclass(frozen=True)
class LightCyclerStatus:
  """What the LightCycler is doing.

  Attributes:
    state: the instrument's state: 6 not ready (the tray open, or no plate), 7 running, 10 idle.
    controller: what the instrument named itself in the handshake.
    firmware_version: its firmware.
    running_experiment: the id of the experiment running, or None.
  """

  state: int
  controller: str
  firmware_version: str
  running_experiment: Optional[str]


# -- protocols -------------------------------------------------------------------------------------


def as_lightcycler_protocol(protocol: Protocol) -> Protocol:
  """`protocol` with every step a `LightCyclerStep`; a plain `Step` reads nothing."""
  stages = []
  for stage in protocol.stages:
    steps: List[Step] = []
    for step in stage.steps:
      if isinstance(step, LightCyclerStep):
        steps.append(dataclasses.replace(step, temperature=list(step.temperature)))
      else:
        steps.append(
          LightCyclerStep(
            temperature=list(step.temperature), hold_seconds=step.hold_seconds, rate=step.rate
          )
        )
    stages.append(Stage(steps=steps, repeats=stage.repeats))
  return Protocol(stages=stages)


@dataclass(frozen=True)
class _Slot:
  """Where a read is taken in the protocol."""

  stage_index: int
  cycle: int
  step_index: int
  filter_set: str


def _wire_step(stage_index: int, step_index: int, step: LightCyclerStep) -> WireStep:
  where = f"stage {stage_index} step {step_index}"
  temperatures = set(step.temperature)
  if len(temperatures) != 1:
    raise ValueError(
      f"{where}: the LightCycler's block has one zone, so a step has one temperature, "
      f"not {step.temperature}"
    )
  temperature = temperatures.pop()
  if not 0 < temperature <= 100:
    raise ValueError(f"{where}: temperature must be above 0 and at most 100 C, not {temperature}")
  if step.hold_seconds < 0:
    raise ValueError(f"{where}: hold_seconds must be at least 0, not {step.hold_seconds}")
  if step.rate is not None and step.rate <= 0:
    raise ValueError(f"{where}: rate must be above 0, not {step.rate}")
  if step.filter_set not in FILTER_CODES:
    raise ValueError(f"{where}: filter_set must be one of {sorted(FILTER_CODES)}")
  if step.exposure <= 0:
    raise ValueError(f"{where}: exposure must be above 0, not {step.exposure}")
  return WireStep(
    temperature=temperature,
    hold_seconds=step.hold_seconds,
    filter_code=FILTER_CODES[step.filter_set] if step.acquire else 0,
    exposure=step.exposure,
    ramp_rate=DEFAULT_RAMP_RATE if step.rate is None else step.rate,
  )


def plan_experiment(
  protocol: Protocol, guid: str, well_count: int, volume: int
) -> Tuple[ExperimentConfig, List[_Slot]]:
  """The experiment `protocol` goes on the wire as, a program per repeat of a stage, and where each
  read is taken.

  Raises:
    ValueError: The LightCycler cannot run it as given.
  """
  if well_count not in (96, 384):
    raise ValueError(f"well_count must be 96 or 384, not {well_count}")
  if volume < 1:
    raise ValueError(f"volume must be at least 1 uL, not {volume}")
  if not protocol.stages:
    raise ValueError("the protocol has no stages")
  programs: List[Tuple[WireStep, ...]] = []
  slots: List[_Slot] = []
  for stage_index, stage in enumerate(as_lightcycler_protocol(protocol).stages):
    if stage.repeats < 1:
      raise ValueError(f"stage {stage_index}: repeats must be at least 1, not {stage.repeats}")
    if not stage.steps:
      raise ValueError(f"stage {stage_index} has no steps")
    holds = {step.hold_seconds for step in stage.steps}
    if len(holds) > 1:
      raise ValueError(
        f"stage {stage_index}: the LightCycler holds every step of a stage for one time; this "
        f"stage's steps hold for {sorted(holds)} s. Put steps that hold differently in stages of "
        "their own."
      )
    steps = []
    for step_index, step in enumerate(stage.steps):
      assert isinstance(step, LightCyclerStep)
      steps.append(_wire_step(stage_index, step_index, step))
    for cycle in range(stage.repeats):
      programs.append(tuple(steps))
      for step_index, step in enumerate(stage.steps):
        assert isinstance(step, LightCyclerStep)
        if step.acquire:
          slots.append(_Slot(stage_index, cycle, step_index, step.filter_set))
  config = ExperimentConfig(
    guid=guid, well_count=well_count, volume=volume, programs=tuple(programs)
  )
  return config, slots


def expected_seconds(config: ExperimentConfig) -> float:
  """About how long `config` runs: each step's ramp at its rate, and its hold."""
  seconds = 0.0
  temperature = _START_TEMPERATURE
  for program in config.programs:
    for step in program:
      seconds += abs(step.temperature - temperature) / step.ramp_rate + step.hold_seconds
      temperature = step.temperature
  return seconds


def _experiment_id(experiment_id: Optional[str]) -> str:
  if experiment_id is None:
    return uuid.uuid4().hex.upper()
  if not _HEX_ID.match(experiment_id):
    raise ValueError(f"an experiment id is 32 hex digits, a UUID's, not '{experiment_id}'")
  return experiment_id.upper()


# -- experiments the device runs ---------------------------------------------------------------------


class _Run:
  """One experiment the device started: its task, and what it has done so far."""

  def __init__(
    self, experiment_id: str, protocol: Protocol, well_count: int, volume: int, total: int
  ) -> None:
    self.id = experiment_id
    self.protocol = protocol
    self.well_count = well_count
    self.volume = volume
    self.total = total
    self.status: ExperimentStatus = "pending"
    self.created_at = time.time()
    self.finished_at: Optional[float] = None
    self.error: Optional[str] = None
    self.acquisitions: List[Acquisition] = []
    self.task: Optional["asyncio.Task[None]"] = None
    self.changed = asyncio.Condition()
    self.revision = 0
    self.done = asyncio.Event()

  def same_as(self, protocol: Protocol, well_count: int, volume: int) -> bool:
    return (protocol, well_count, volume) == (self.protocol, self.well_count, self.volume)

  @property
  def finished(self) -> bool:
    return self.status in ("complete", "error")

  def snapshot(self) -> Experiment:
    return Experiment(
      id=self.id,
      status=self.status,
      protocol=self.protocol,
      well_count=self.well_count,
      volume=self.volume,
      created_at=self.created_at,
      finished_at=self.finished_at,
      error=self.error,
      acquisitions_total=self.total,
      acquisitions=tuple(self.acquisitions),
    )

  def summary(self) -> ExperimentSummary:
    return ExperimentSummary(
      id=self.id,
      status=self.status,
      created_at=self.created_at,
      finished_at=self.finished_at,
      error=self.error,
      acquisitions_done=len(self.acquisitions),
      acquisitions_total=self.total,
    )

  async def _publish(self) -> None:
    async with self.changed:
      self.revision += 1
      self.changed.notify_all()

  async def set_status(self, status: ExperimentStatus) -> None:
    self.status = status
    await self._publish()

  async def add(self, acquisition: Acquisition) -> None:
    self.acquisitions.append(acquisition)
    await self._publish()

  async def finish(self, error: Optional[str]) -> None:
    self.status = "error" if error is not None else "complete"
    self.error = error
    self.finished_at = time.time()
    self.done.set()
    await self._publish()


def _acquisition(number: int, slot: _Slot, result: ResultData) -> Acquisition:
  return Acquisition(
    number=number,
    stage_index=slot.stage_index,
    cycle=slot.cycle,
    step_index=slot.step_index,
    temperature=result.temperature,
    time=result.time,
    filter_set=slot.filter_set,
    ref_channel=result.ref_channel,
    values=result.values,
  )


class LightCycler480:
  """A Roche LightCycler 480 II.

  Given `lightcycler_server`, a LightCycler server or its URL, it is the LightCycler that server
  serves instead, driven over the network with the same methods; see `RemoteLightCycler480`.

  The defaults below are used where a call names none. Assign one on an instance to tune that
  device, or on the class to tune every device.

  Attributes:
    tray_button: what presses the tray button; None when the tray is moved by hand.
  """

  # How long the tray may take to move after its button is pressed, in seconds, and how often it
  # is read meanwhile.
  default_tray_timeout: float = 10.0
  tray_poll_interval: float = 0.5
  # How long, past the time the protocol is expected to take, a read may take to come, in seconds.
  default_acquisition_margin: float = 300.0
  # How long, past the time the protocol is expected to take, the run may take to end, in seconds.
  default_finish_margin: float = 60.0
  # How long a run that reads nothing may take to start, in seconds.
  default_start_timeout: float = 10.0
  # How many finished experiments are kept, newest last.
  kept_experiments: int = 64

  def __new__(cls, *args: Any, **kwargs: Any) -> "LightCycler480":
    if cls is LightCycler480 and kwargs.get("lightcycler_server") is not None:
      from .server.client import RemoteLightCycler480

      return super().__new__(RemoteLightCycler480)
    return super().__new__(cls)

  def __init__(
    self,
    host: Optional[str] = None,
    port: int = LightCycler480Driver.DEFAULT_PORT,
    simulation: bool = False,
    driver: Optional[LightCycler480Driver] = None,
    tray_button: Optional[TrayButton] = None,
    lightcycler_server: Union[str, "LightCyclerServer", None] = None,
  ) -> None:
    """
    Args:
      host: the instrument's IP address; not needed for a simulated one or a given driver.
      port: its base port.
      simulation: drive a `LightCycler480Simulator` in place of an instrument, with a
        `SimulatedTrayButton` when no tray button is given.
      driver: the driver to use, in place of one made from the arguments above.
      tray_button: what presses the tray button, a `SwitchBotBot` say; without one, `open_tray` and
        `close_tray` only say where the tray is, and refuse to move it.
      lightcycler_server: the LightCycler server to drive the instrument through, or its URL; see
        `RemoteLightCycler480`.
    """
    if driver is None:
      if simulation:
        simulator = LightCycler480Simulator()
        driver = simulator
        if tray_button is None:
          tray_button = SimulatedTrayButton(simulator.instrument)
      elif host is None:
        raise ValueError("a LightCycler480 needs a host, simulation=True, or a driver")
      else:
        driver = LightCycler480Driver(host=host, port=port)
    self._driver = driver
    self.tray_button = tray_button
    self._runs: "OrderedDict[str, _Run]" = OrderedDict()
    self._starting = asyncio.Lock()

  @property
  def driver(self) -> LightCycler480Driver:
    """What talks to the instrument."""
    return self._driver

  # -- lifecycle ---------------------------------------------------------------------------------

  async def setup(self) -> None:
    """Connect, and read away whatever a past run left unread. Does nothing once connected."""
    if self.driver.connected:
      return
    await self.driver.setup()
    await self.driver.drain_stale_results()

  async def stop(self) -> None:
    """Close the connections. An experiment running is left running on the instrument, and ends
    here in error, its reads no longer collected."""
    for run in self._runs.values():
      if run.task is not None and not run.task.done():
        run.task.cancel()
        await asyncio.gather(run.task, return_exceptions=True)
    await self.driver.stop()

  # -- what the instrument reports ------------------------------------------------------------------

  def _running(self) -> Optional[_Run]:
    for run in self._runs.values():
      if not run.finished:
        return run
    return None

  async def request_status(self) -> LightCyclerStatus:
    """The instrument's state, what it is, and the experiment running."""
    state = await self.driver.request_instrument_state()
    info = self.driver.info
    running = self._running()
    return LightCyclerStatus(
      state=state,
      controller=info.controller if info else "",
      firmware_version=info.firmware_version if info else "",
      running_experiment=running.id if running else None,
    )

  async def request_tray_state(self) -> TrayState:
    """Where the tray is, whether a plate is loaded, and its barcode."""
    return await self.driver.request_tray_state()

  async def request_logs(self, since_id: int = 0, limit: int = 100) -> List[LogEntry]:
    """The events and trace lines the instrument sent after `since_id`, oldest first, at most
    `limit`."""
    return self.driver.logs(since_id=since_id, limit=limit)

  # -- the tray ---------------------------------------------------------------------------------------

  async def _move_tray(self, to_open: bool, timeout: Optional[float]) -> None:
    where = "open" if to_open else "closed"
    if (await self.request_tray_state()).open == to_open:
      return
    running = self._running()
    if running is not None:
      raise RuntimeError(f"experiment {running.id} is running; the tray stays closed")
    if self.tray_button is None:
      raise RuntimeError(
        f"the tray is not {where}, and there is no tray button to press: press the LightCycler's "
        "own"
      )
    timeout = self.default_tray_timeout if timeout is None else timeout
    await self.tray_button.press()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
      if (await self.request_tray_state()).open == to_open:
        logger.info("[lightcycler] the tray is %s", where)
        return
      if loop.time() + self.tray_poll_interval > deadline:
        raise TimeoutError(f"the tray was not {where} within {timeout} s of pressing its button")
      await asyncio.sleep(self.tray_poll_interval)

  async def open_tray(self, timeout: Optional[float] = None) -> None:
    """Have the tray out, for a plate to be put on or taken off: press its button if it is in, and
    wait until it is out.

    Args:
      timeout: how long it may take to come out, in seconds; `default_tray_timeout` when not given.

    Raises:
      RuntimeError: It is in and an experiment is running, or there is no tray button.
      TimeoutError: It was not out within `timeout` of pressing the button.
    """
    await self._move_tray(True, timeout)

  async def close_tray(self, timeout: Optional[float] = None) -> None:
    """Have the tray in: press its button if it is out, and wait until it is in.

    Args:
      timeout: as `open_tray`'s.

    Raises:
      RuntimeError: It is out and there is no tray button.
      TimeoutError: It was not in within `timeout` of pressing the button.
    """
    await self._move_tray(False, timeout)

  # -- experiments --------------------------------------------------------------------------------

  async def start_experiment(
    self,
    protocol: Protocol,
    well_count: int = 384,
    volume: int = 20,
    experiment_id: Optional[str] = None,
  ) -> str:
    """Start an experiment and return its id; it runs on after this returns.

    An experiment started again with the id of one already started is not started again, so a
    start can be retried safely: its id is returned, and the one started is the one that runs.

    Args:
      protocol: what to run. Steps that are `LightCyclerStep`s with `acquire=True` read.
      well_count: 96 or 384, the plate's.
      volume: the reaction volume, in uL.
      experiment_id: 32 hex digits naming it; a new UUID's when not given.

    Raises:
      ValueError: The protocol cannot run on the LightCycler, or the id names another experiment.
      RuntimeError: Another experiment is running, here or on the instrument; the tray is open;
        or no plate is loaded.
    """
    experiment_id = _experiment_id(experiment_id)
    protocol = as_lightcycler_protocol(protocol)
    config, slots = plan_experiment(protocol, experiment_id, well_count, volume)
    async with self._starting:
      existing = self._runs.get(experiment_id)
      if existing is not None:
        if not existing.same_as(protocol, well_count, volume):
          raise ValueError(f"experiment {experiment_id} was started with another protocol")
        return experiment_id
      running = self._running()
      if running is not None:
        raise RuntimeError(f"experiment {running.id} is running")
      tray = await self.request_tray_state()
      if tray.open:
        raise RuntimeError("the tray is open: close it before running an experiment")
      if not tray.plate_loaded:
        raise RuntimeError("no plate is loaded: put one on the tray and close it")
      if await self.driver.request_instrument_state() == STATE_RUNNING:
        raise RuntimeError("the instrument is running a run this LightCycler480 did not start")
      run = _Run(experiment_id, protocol, well_count, volume, config.total_acquisitions)
      self._runs[experiment_id] = run
      self._forget_old()
      run.task = asyncio.get_running_loop().create_task(self._execute(run, config, slots))
    logger.info("[lightcycler] experiment %s started", experiment_id)
    return experiment_id

  def _forget_old(self) -> None:
    finished = [key for key, run in self._runs.items() if run.finished]
    for key in finished[: max(0, len(finished) - self.kept_experiments)]:
      del self._runs[key]

  async def _execute(self, run: _Run, config: ExperimentConfig, slots: Sequence[_Slot]) -> None:
    """Send the run, collect each read as it comes, and wait for the instrument to finish."""
    driver = self.driver
    expected = expected_seconds(config)
    try:
      await driver.drain_stale_results()
      await driver.prepare_run()
      await driver.send_experiment(config)
      await run.set_status("running")
      if not slots:
        await driver.wait_until_running(self.default_start_timeout)
      for number, slot in enumerate(slots, start=1):
        result = await driver.wait_for_result(
          number, config.guid, timeout=self.default_acquisition_margin + expected
        )
        await driver.acknowledge_result(number)
        await run.add(_acquisition(number, slot, result))
        logger.info(
          "[lightcycler] experiment %s: read %d of %d at %.2f C",
          run.id,
          number,
          len(slots),
          result.temperature,
        )
      await driver.wait_idle(timeout=self.default_finish_margin + expected)
      await driver.finish_run()
    except asyncio.CancelledError:
      await run.finish("the LightCycler was stopped before the experiment finished")
      raise
    except Exception as error:
      logger.error("[lightcycler] experiment %s failed: %s", run.id, error)
      await run.finish(f"{type(error).__name__}: {error}")
      return
    await run.finish(None)
    logger.info("[lightcycler] experiment %s complete", run.id)

  def _run(self, experiment_id: str) -> _Run:
    run = self._runs.get(experiment_id.upper())
    if run is None:
      raise KeyError(f"no experiment {experiment_id}")
    return run

  async def get_experiment(self, experiment_id: str) -> Experiment:
    """The experiment as it is now, with the reads taken so far.

    Raises:
      KeyError: No experiment has this id; only the last `kept_experiments` finished are kept.
    """
    return self._run(experiment_id).snapshot()

  async def list_experiments(self, limit: int = 50) -> List[ExperimentSummary]:
    """The experiments kept, newest first, at most `limit`."""
    runs = list(self._runs.values())[::-1][: max(0, limit)]
    return [run.summary() for run in runs]

  async def wait_for_experiment(
    self, experiment_id: str, timeout: Optional[float] = None
  ) -> Experiment:
    """Wait until the experiment has finished, and return it.

    Args:
      timeout: how long to wait, in seconds; as long as it takes when not given. The experiment
        runs on when this times out.

    Raises:
      KeyError: No experiment has this id.
      ExperimentFailedError: It ended in error.
      TimeoutError: It had not finished within `timeout`.
    """
    run = self._run(experiment_id)
    try:
      await asyncio.wait_for(run.done.wait(), timeout=timeout)
    except asyncio.TimeoutError as error:
      raise TimeoutError(
        f"experiment {run.id} had not finished within {timeout} s; it runs on"
      ) from error
    experiment = run.snapshot()
    if experiment.status == "error":
      raise ExperimentFailedError(run.id, experiment.error or "unknown")
    return experiment

  async def run_experiment(
    self,
    protocol: Protocol,
    well_count: int = 384,
    volume: int = 20,
    experiment_id: Optional[str] = None,
  ) -> Experiment:
    """Start an experiment, as `start_experiment`, and wait for it to finish.

    Raises:
      ExperimentFailedError: It ended in error.
    """
    started = await self.start_experiment(
      protocol, well_count=well_count, volume=volume, experiment_id=experiment_id
    )
    return await self.wait_for_experiment(started)

  async def watch_experiment(self, experiment_id: str) -> AsyncIterator[Experiment]:
    """The experiment as it is, then again each time it changes, ending once it has finished.

    Raises:
      KeyError: No experiment has this id.
    """
    run = self._run(experiment_id)
    seen = -1
    while True:
      async with run.changed:
        if run.revision == seen:
          await run.changed.wait()
        seen = run.revision
        experiment = run.snapshot()
      yield experiment
      if experiment.finished:
        return
