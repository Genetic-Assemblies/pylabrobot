"""A simulated a4S: the serial port of one, answering as the sealer would, under the real `A4S`.

`SimulatedA4S` is an `A4S` whose port is an `A4SPortSimulator`, so every one of its methods runs as
it does against hardware. The simulated sealer streams its status, as an a4S does, one message for
each that is read; takes the commands the driver sends (`DH`, `H0`/`H1`, `DT`, `GS`, `MO`, `MC`,
`SR`); moves its shuttle, heats, and runs a seal cycle in time, on a clock that may run faster than
the real one.

What is not the a4S's own: the timings, which are plausible, not measured; the two characters
before `zz` that end a status message, which the driver drops and this fills with `00`; that `DH`
alone turns the heater on, as the driver assumes; that a seal cycle takes the shuttle in, presses
and brings it out again; and that the sealer says `finish` for a second after a cycle before it is
`idle` again.
"""

from __future__ import annotations

import asyncio
import math
import time
from typing import List, Optional

from pylabrobot.azenta.a4s.a4s import A4S, A4SStatus

SystemStatus = A4SStatus.SystemStatus
HeaterBlockStatus = A4SStatus.HeaterBlockStatus


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


class A4SPortSimulator:
  """The serial port of a simulated a4S: what is written to it are commands, what is read from it
  the sealer's status, streamed.

  Attributes:
    written: every command written, decoded, in order.
    fault: an error code the sealer reports from now on; 0 is none. A system reset clears it.
    sealed: how many seal cycles it has finished.
  """

  SHUTTLE_SECONDS = 4.0
  HEAT_RATE = 2.0  # Celsius a second
  COOL_RATE = 0.3  # Celsius a second
  FINISH_SECONDS = 1.0
  # How long, in real seconds, the sealer takes to send one status message.
  MESSAGE_SECONDS = 0.002

  def __init__(self, speed: float = 1.0):
    """
    Args:
      speed: how many times faster than a real one it runs.
    """
    self.clock = Clock(speed)
    self.heater = Heater(self.clock, self.HEAT_RATE, self.COOL_RATE)
    self.set_temperature = 0.0
    self.seal_deciseconds = 0
    self.written: List[str] = []
    self.fault = 0
    self.sealed = 0
    self._buffer = b""
    # Where the shuttle is: open, and since when it has been moving toward where it is going.
    self._shuttle_open = True
    self._shuttle_moved_at: Optional[float] = None
    # When the running seal cycle started, and when the last one finished.
    self._cycle_at: Optional[float] = None
    self._finished_at: Optional[float] = None
    self._cycle_from_open = False

  # -- the port --

  async def setup(self) -> None:
    pass

  async def stop(self) -> None:
    pass

  async def write(self, data: bytes) -> None:
    command = data.decode()
    self.written.append(command)
    self._command(command)

  async def read(self, num_bytes: int = 1) -> bytes:
    if not self._buffer:
      await asyncio.sleep(self.MESSAGE_SECONDS)
      self._buffer = self._status_message().encode() + b"\r"
    data, self._buffer = self._buffer[:num_bytes], self._buffer[num_bytes:]
    return data

  # -- the sealer --

  def _command(self, command: str) -> None:
    """Act on a command: `*00DH=0165zz!` say."""
    body = command[3:] if command.startswith("*00") else command
    code, value = body[:2], body[2:].lstrip("=").rstrip("!").rstrip("zZ")
    if code == "SR":
      self.fault = 0
      self._cycle_at = None
      self._finished_at = None
    elif code == "DH":
      self.set_temperature = float(int(value))
      self.heater.set(self.set_temperature)
    elif code == "H1":
      self.heater.set(self.set_temperature or None)
    elif code == "H0":
      self.heater.set(None)
    elif code == "DT":
      self.seal_deciseconds = int(value)
    elif code == "GS":
      if self._cycle_at is None:
        self._cycle_from_open = self._shuttle_at_open()
        self._cycle_at = self.clock.now()
    elif code in ("MO", "MC"):
      if self._cycle_at is None:
        self._move_shuttle(code == "MO")

  def _shuttle_at_open(self) -> bool:
    return self._shuttle_open and self._shuttle_moved_at is None

  def _settle_shuttle(self) -> None:
    if self._shuttle_moved_at is not None:
      if self.clock.now() - self._shuttle_moved_at >= self.SHUTTLE_SECONDS:
        self._shuttle_moved_at = None

  def _move_shuttle(self, open: bool) -> None:
    self._settle_shuttle()
    if self._shuttle_open != open:
      self._shuttle_open = open
      self._shuttle_moved_at = self.clock.now()

  def _cycle(self) -> SystemStatus:
    """Move a running seal cycle on: in, press, out."""
    now = self.clock.now()
    if self._cycle_at is None:
      if self._finished_at is not None and now - self._finished_at < self.FINISH_SECONDS:
        return SystemStatus.finish
      return SystemStatus.idle
    elapsed = now - self._cycle_at
    going_in = self.SHUTTLE_SECONDS if self._cycle_from_open else 0.0
    pressing = self.seal_deciseconds / 10
    if elapsed < going_in:
      self._shuttle_open, self._shuttle_moved_at = False, self._cycle_at
    elif elapsed < going_in + pressing:
      self._shuttle_open, self._shuttle_moved_at = False, None
    elif elapsed < going_in + pressing + self.SHUTTLE_SECONDS:
      self._shuttle_open, self._shuttle_moved_at = True, self._cycle_at + going_in + pressing
    else:
      self._shuttle_open, self._shuttle_moved_at = True, None
      self._cycle_at, self._finished_at = None, now
      self.sealed += 1
      return SystemStatus.finish
    return SystemStatus.single_cycle

  def remaining_time(self) -> int:
    """Seconds left of the running seal cycle; 0 when none runs."""
    if self._cycle_at is None:
      return 0
    going_in = self.SHUTTLE_SECONDS if self._cycle_from_open else 0.0
    total = going_in + self.seal_deciseconds / 10 + self.SHUTTLE_SECONDS
    return max(0, math.ceil(total - (self.clock.now() - self._cycle_at)))

  def _heater_status(self) -> HeaterBlockStatus:
    if self.heater.target is None:
      return HeaterBlockStatus.heater_off
    difference = self.heater.temperature() - self.heater.target
    if abs(difference) < 0.5:
      return HeaterBlockStatus.ready
    return HeaterBlockStatus.heating if difference < 0 else HeaterBlockStatus.cooling

  def _sensors(self) -> int:
    self._settle_shuttle()
    moving = self._shuttle_moved_at is not None
    bits = 0
    if moving:
      bits |= 0x0001
    elif self._shuttle_open:
      bits |= 0x0002
    else:
      bits |= 0x0004
    bits |= 0x0010  # a seal roll is in
    bits |= 0x0020  # the heater is up
    return bits

  def _status_message(self) -> str:
    system = SystemStatus.error if self.fault else self._cycle()
    parameters = [
      f"{round(self.heater.temperature() * 10):04d}",
      str(system.value),
      str(self._heater_status().value),
      f"{self.fault:02d}",
      "00",
      f"{self._sensors():04d}",
      f"{self.remaining_time():04d}",
    ]
    return f"*T00={','.join(parameters)}00zz!"


class SimulatedA4S(A4S):
  """An `A4S` on a simulated sealer's port: the driver's own methods, without hardware.

  Attributes:
    simulator: the simulated sealer, which is its port.
  """

  def __init__(self, port: str = "simulated", timeout: int = 20, speed: float = 1.0):
    """
    Args:
      port: what to call its port.
      timeout: as `A4S`'s.
      speed: how many times faster than a real one the simulated sealer runs. Above about 50, a
        seal cycle is over within the tenth of a second the driver pauses after a command, so it
        never sees the cycle run and waits for it until its timeout.
    """
    # Not A4S.__init__: that opens a serial port.
    self.port = port
    self.timeout = timeout
    self.simulator = A4SPortSimulator(speed)
    self.io = self.simulator  # type: ignore[assignment]
