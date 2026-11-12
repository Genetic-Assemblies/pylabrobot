"""A thermocycler backend without hardware, timed: its lid takes time to move, its block and lid
heat and cool at steady rates, and a protocol runs step by step in the background.

Unlike `ThermocyclerChatterboxBackend`, which reaches every temperature at once, this one runs on a
clock that may run faster than the real one, so a run, its status queries and
`Thermocycler.wait_for_profile_completion` behave as they would against a device. Its rates and
times are plausible for a 96- or 384-well block, not measured from any model.
"""

import asyncio
import math
import time
from typing import List, Optional

from pylabrobot.legacy.thermocycling.backend import ThermocyclerBackend
from pylabrobot.legacy.thermocycling.standard import BlockStatus, LidStatus, Protocol

# How near its target a temperature is to be holding at it, in Celsius.
_AT_TARGET = 0.5

# What a run that is between two steps says is left of the one it is on, in seconds.
_BETWEEN_STEPS = 0.001


class Clock:
  """Time for a simulator: `speed` times faster than the real one."""

  def __init__(self, speed: float = 1.0):
    if speed <= 0:
      raise ValueError(f"speed must be more than 0, not {speed}")
    self.speed = speed
    self._start = time.monotonic()

  def now(self) -> float:
    """Simulated seconds since it was made."""
    return (time.monotonic() - self._start) * self.speed

  async def sleep(self, seconds: float) -> None:
    """Wait `seconds` of simulated time."""
    await asyncio.sleep(max(0.0, seconds) / self.speed)


class Heater:
  """A heater that moves toward its target at a steady rate, and toward the room when it is off."""

  def __init__(self, clock: Clock, heat_rate: float, cool_rate: float, ambient: float = 25.0):
    self.clock = clock
    self.heat_rate = heat_rate
    self.cool_rate = cool_rate
    self.ambient = ambient
    self.target: Optional[float] = None
    self._from = ambient
    self._at = clock.now()

  def _goal(self) -> float:
    return self.ambient if self.target is None else self.target

  def temperature(self) -> float:
    goal, elapsed = self._goal(), self.clock.now() - self._at
    rate = self.heat_rate if goal > self._from else self.cool_rate
    return self._from + math.copysign(
      min(abs(goal - self._from), rate * elapsed), goal - self._from
    )

  def set(self, target: Optional[float]) -> None:
    self._from, self._at = self.temperature(), self.clock.now()
    self.target = target

  def seconds_to_goal(self) -> float:
    """Simulated seconds until it is at its target, or the room's temperature when off."""
    now, goal = self.temperature(), self._goal()
    return abs(goal - now) / (self.heat_rate if goal > now else self.cool_rate)


class ThermocyclerSimulatorBackend(ThermocyclerBackend):
  """A simulated thermocycler: a motorized lid, a heated lid, and a block of `num_zones` zones.

  `run_protocol` starts the run and returns, as the Opentrons and ODTC backends' do; the run goes
  on in the background, each step ramping to its temperatures and then holding them, and ends held
  at its last step's. Each zone ramps at the block's rate; a step's own `rate` is not used. While a
  run goes on, the lid does not move and another run does not start (RuntimeError);
  `set_block_temperature`, `deactivate_block` and `stop` end the run.

  Attributes:
    ran: each protocol it ran to its end.
  """

  LID_SECONDS = 10.0
  BLOCK_HEAT_RATE = 4.0  # Celsius a second
  BLOCK_COOL_RATE = 3.0
  LID_HEAT_RATE = 1.0
  LID_COOL_RATE = 0.2

  def __init__(self, num_zones: int = 1, speed: float = 1.0):
    """
    Args:
      num_zones: how many temperature zones its block has.
      speed: how many times faster than a real one it runs.
    """
    super().__init__()
    if num_zones < 1:
      raise ValueError(f"a block has at least one zone, not {num_zones}")
    self.num_zones = num_zones
    self.clock = Clock(speed)
    self.block = [
      Heater(self.clock, self.BLOCK_HEAT_RATE, self.BLOCK_COOL_RATE) for _ in range(num_zones)
    ]
    self.lid = Heater(self.clock, self.LID_HEAT_RATE, self.LID_COOL_RATE)
    self.lid_open = False
    self.ran: List[Protocol] = []
    self._run: Optional["asyncio.Task[None]"] = None
    # Where the run is: its stage, the stage's repeat, the step, and when the step ends.
    self._stage = self._cycle = self._step = 0
    self._total_cycles = self._total_steps = 0
    self._hold_until: Optional[float] = None
    self._last_step = False

  def serialize(self) -> dict:
    return {**super().serialize(), "num_zones": self.num_zones, "speed": self.clock.speed}

  def _running(self) -> bool:
    """Whether a run goes on: not once its last step is over, though its task may not yet have
    seen that it is."""
    if self._run is None or self._run.done():
      return False
    over = self._hold_until is not None and self.clock.now() >= self._hold_until
    return not (self._last_step and over)

  async def _end_run(self) -> None:
    if self._run is not None:
      self._run.cancel()
      try:
        await self._run
      except asyncio.CancelledError:
        pass
      self._run = None

  def _check_idle(self, what: str) -> None:
    if self._running():
      raise RuntimeError(f"a protocol is running: stop it before you {what}")

  def _check_zones(self, temperature: List[float], what: str) -> None:
    if len(temperature) != self.num_zones:
      raise ValueError(
        f"Expected {self.num_zones} {what} temperatures, got {len(temperature)}: {temperature}"
      )

  async def setup(self):
    pass

  async def stop(self):
    await self._end_run()
    for zone in self.block:
      zone.set(None)
    self.lid.set(None)

  async def _move_lid(self, open: bool) -> None:
    self._check_idle("move the lid")
    if self.lid_open != open:
      await self.clock.sleep(self.LID_SECONDS)
      self.lid_open = open

  async def open_lid(self):
    await self._move_lid(True)

  async def close_lid(self):
    await self._move_lid(False)

  async def set_block_temperature(self, temperature: List[float]):
    self._check_zones(temperature, "block")
    await self._end_run()
    for zone, target in zip(self.block, temperature):
      zone.set(target)

  async def set_lid_temperature(self, temperature: List[float]):
    if len(temperature) < 1:
      raise ValueError("Expected a lid temperature, got none")
    self.lid.set(temperature[0])

  async def deactivate_block(self):
    await self._end_run()
    for zone in self.block:
      zone.set(None)

  async def deactivate_lid(self):
    self.lid.set(None)

  async def run_protocol(self, protocol: Protocol, block_max_volume: float):
    self._check_idle("run another")
    if self.lid_open:
      raise RuntimeError("the lid is open: close it before running a protocol")
    if not (math.isfinite(block_max_volume) and block_max_volume > 0):
      raise ValueError(f"block_max_volume must be more than 0 uL, not {block_max_volume}")
    if not protocol.stages:
      raise ValueError("a protocol needs at least one stage")
    for stage in protocol.stages:
      if stage.repeats < 1:
        raise ValueError(f"a stage runs at least once, not {stage.repeats} times")
      if not stage.steps:
        raise ValueError("a stage needs at least one step")
      for step in stage.steps:
        self._check_zones(step.temperature, "step")
        if not (math.isfinite(step.hold_seconds) and step.hold_seconds >= 0):
          raise ValueError(f"a hold is a finite number of seconds, not {step.hold_seconds}")
    self._stage = self._cycle = self._step = 0
    self._total_cycles, self._total_steps = (
      protocol.stages[0].repeats,
      len(protocol.stages[0].steps),
    )
    self._hold_until, self._last_step = None, False
    self._run = asyncio.ensure_future(self._run_protocol(protocol))
    # Let the run begin its first step, so it says it is running once this returns.
    await asyncio.sleep(0)

  async def _run_protocol(self, protocol: Protocol) -> None:
    last = (
      len(protocol.stages) - 1,
      protocol.stages[-1].repeats - 1,
      len(protocol.stages[-1].steps) - 1,
    )
    for i, stage in enumerate(protocol.stages):
      self._stage, self._total_cycles, self._total_steps = i, stage.repeats, len(stage.steps)
      for cycle in range(stage.repeats):
        for j, step in enumerate(stage.steps):
          self._cycle, self._step = cycle, j
          self._last_step = (i, cycle, j) == last
          for zone, target in zip(self.block, step.temperature):
            zone.set(target)
          seconds = max(zone.seconds_to_goal() for zone in self.block) + step.hold_seconds
          self._hold_until = self.clock.now() + seconds
          await self.clock.sleep(seconds)
    self._hold_until = None
    self.ran.append(protocol)

  def _block_targets(self) -> List[float]:
    targets = [zone.target for zone in self.block]
    if any(target is None for target in targets):
      raise RuntimeError("Block target temperature is not set.")
    return [float(target) for target in targets if target is not None]

  async def get_block_current_temperature(self) -> List[float]:
    return [round(zone.temperature(), 1) for zone in self.block]

  async def get_block_target_temperature(self) -> List[float]:
    return self._block_targets()

  async def get_lid_current_temperature(self) -> List[float]:
    return [round(self.lid.temperature(), 1)]

  async def get_lid_target_temperature(self) -> List[float]:
    if self.lid.target is None:
      raise RuntimeError("Lid target temperature is not set.")
    return [self.lid.target]

  async def get_lid_open(self) -> bool:
    return self.lid_open

  async def get_lid_status(self) -> LidStatus:
    target = self.lid.target
    if target is not None and abs(self.lid.temperature() - target) < _AT_TARGET:
      return LidStatus.HOLDING_AT_TARGET
    return LidStatus.IDLE

  async def get_block_status(self) -> BlockStatus:
    if all(
      zone.target is not None and abs(zone.temperature() - zone.target) < _AT_TARGET
      for zone in self.block
    ):
      return BlockStatus.HOLDING_AT_TARGET
    return BlockStatus.IDLE

  async def get_hold_time(self) -> float:
    """The seconds left of the running step: its ramp, if it is still ramping, and its hold. A
    step that ramps is still running, so `Thermocycler.is_profile_running` says so.

    Between a stage's last step and the next stage's first, the step and cycle say the stage is
    done, and `is_profile_running` only looks at the stage it is in: so until the protocol's last
    step, a run that is going says some time is left, as a device counting on would."""
    if not self._running() or self._hold_until is None:
      return 0.0
    left = max(0.0, self._hold_until - self.clock.now())
    if not self._last_step:
      return max(left, _BETWEEN_STEPS)
    return left

  async def get_current_cycle_index(self) -> int:
    return self._cycle

  async def get_total_cycle_count(self) -> int:
    return self._total_cycles

  async def get_current_step_index(self) -> int:
    return self._step

  async def get_total_step_count(self) -> int:
    return self._total_steps
