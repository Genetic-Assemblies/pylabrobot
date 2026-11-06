"""A simulated MicroSpin, answering each connection line by line as the device does.

`MicroSpinSimulator` is the driver with its connections run over a `SimulatedMicroSpin` in place of
sockets, so everything above the wire runs as it does against a device. What it answers was read
off a device: the `ACK!` / data / end-line shape, command ids counted across connections, the error
stack printed whole before `ERROR!` with each entry carrying the id of the command it was raised
for, the refusals before homing, `hss`, `cstat` and the spindle's velocity answered during motion,
`status` held until the rotor has stopped, `abort` setting the rotor coasting, where `home` and
`open` leave the spindle and door, and how long each takes.
"""

import asyncio
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Deque, Dict, List, Optional, Tuple, Union

from .driver import MicroSpinDriver, Transport

# The door's position closed and open, in the door drive's counts.
DOOR_CLOSED = -451
DOOR_OPEN = 19240
# Where homing leaves the spindle, and where each bucket is at the door, in the spindle's counts.
SPINDLE_HOME = 1958
SPINDLE_AT_DOOR = {1: 8186, 2: 4087}
# Counts per turn of the spindle.
SPINDLE_COUNTS = 8192
# How long each takes on a device, in seconds.
HOME_SECONDS = 10.0
OPEN_SECONDS = 10.0
SPIN_UP_SECONDS = 8.0
SPIN_DOWN_SECONDS = 45.0
# The buckets' radius, in m, as the device's `CENTRIFUGE_BUCKET_RADIUS_M` setting has it.
BUCKET_RADIUS = 0.12


def rpm_at(g: float) -> float:
  """The spindle speed, in rpm, that gives `g` x g at the buckets."""
  return math.sqrt(g * 9.81 / BUCKET_RADIUS) * 60 / (2 * math.pi)


def coast_seconds(rpm: float) -> float:
  """How long the rotor coasts from `rpm` to a stop after an abort: a line through the 40 s from
  320 rpm and the 110 s from 1936 rpm a device took."""
  return 0.0 if rpm < 1 else 26.0 + 0.0434 * rpm


@dataclass(frozen=True)
class _Spin:
  """The rotor on a spin's profile: up, at speed for `duration`, down."""

  started: float
  rpm: float
  duration: float

  def rpm_after(self, seconds: float) -> float:
    if seconds < SPIN_UP_SECONDS:
      return self.rpm * seconds / SPIN_UP_SECONDS
    if seconds < SPIN_UP_SECONDS + self.duration:
      return self.rpm
    down = seconds - SPIN_UP_SECONDS - self.duration
    return max(0.0, self.rpm * (1 - down / SPIN_DOWN_SECONDS))


@dataclass(frozen=True)
class _Coast:
  """The rotor coasting to a stop after an abort."""

  started: float
  rpm: float
  seconds: float

  def rpm_after(self, seconds: float) -> float:
    if self.seconds <= 0:
      return 0.0
    return max(0.0, self.rpm * (1 - seconds / self.seconds))


class _Refused(Exception):
  """A simulated command ends with `ERROR!`."""

  def __init__(self, message: str, warnings: Tuple[str, ...] = ()) -> None:
    self.message = message
    self.warnings = warnings
    super().__init__(message)


class _Aborted(Exception):
  """A simulated command ends with `ABORTED!`."""


@dataclass
class _Failure:
  """An `ERROR!` a command is to end with, the next time it is sent."""

  message: str
  warnings: Tuple[str, ...]


@dataclass
class SimulatedMicroSpin:
  """The state of one simulated device, shared by every connection to it.

  Attributes:
    seconds_per_second: how long simulated motion takes, per second it takes on a device; 0 moves
      at once.
    received: every command sent, with the name of the connection it came on.
  """

  seconds_per_second: float = 0.0
  homed: bool = False
  spindle_position: int = 8191
  door_position: int = 0
  presented: Optional[int] = None
  abort_latched: bool = False
  spinning: bool = False
  errors: List[str] = field(default_factory=list)
  received: List[Tuple[str, str]] = field(default_factory=list)
  _next_id: int = 1
  # How each command ended, or `RUNNING!`, and what it was, by id.
  _history: Dict[int, Tuple[str, str]] = field(default_factory=dict)
  # Set while nothing moves; cleared for the length of each motion.
  _idle: asyncio.Event = field(default_factory=asyncio.Event)
  # Set by an abort, to stop the motion under way.
  _stop: asyncio.Event = field(default_factory=asyncio.Event)
  # Set while the rotor is at rest; cleared for a spin and the coast after an abort.
  _still: asyncio.Event = field(default_factory=asyncio.Event)
  _rotor: Optional[Union[_Spin, _Coast]] = None
  _failures: Dict[str, _Failure] = field(default_factory=dict)

  def __post_init__(self) -> None:
    self._idle.set()
    self._still.set()

  def spindle_rpm(self) -> float:
    """How fast the rotor turns now, in rpm."""
    rotor = self._rotor
    if rotor is None or self.seconds_per_second <= 0:
      return 0.0
    elapsed = (asyncio.get_running_loop().time() - rotor.started) / self.seconds_per_second
    return rotor.rpm_after(elapsed)

  def _end_coast(self) -> None:
    self._rotor = None
    self._still.set()

  def _begin_coast(self) -> None:
    """Leave the rotor coasting from where it is, as an abort does."""
    rpm = self.spindle_rpm()
    loop = asyncio.get_running_loop()
    seconds = coast_seconds(rpm)
    self._rotor = _Coast(started=loop.time(), rpm=rpm, seconds=seconds)
    self._still.clear()
    loop.call_later(seconds * self.seconds_per_second, self._end_coast)

  def fail_next(self, command: str, message: str, warnings: Tuple[str, ...] = ()) -> None:
    """End the next `command` sent (`spin`, `open`, ...) with `ERROR!`, adding `message` to the
    stack."""
    self._failures[command] = _Failure(message, warnings)

  def _push_error(self, command_id: int, message: str) -> None:
    stamp = time.strftime("%H:%M:%S", time.gmtime())
    self.errors.append(f"Error {len(self.errors) + 1}: ({stamp}) {command_id}: {message}")

  async def _move(self, seconds: float, done: Callable[[], None]) -> None:
    """Run one motion: wait, then apply what it did, unless an abort stops it on the way."""
    self._idle.clear()
    self._stop.clear()
    try:
      try:
        await asyncio.wait_for(self._stop.wait(), timeout=seconds * self.seconds_per_second)
      except asyncio.TimeoutError:
        done()
        return
      raise _Aborted()
    finally:
      self._idle.set()

  def _require_not_latched(self) -> None:
    if self.abort_latched:
      raise _Aborted()

  async def _version(self, args: List[str]) -> List[str]:
    return [
      "Product Name: RandomServe",
      "Serial Number: SIMULATED",
      "Firmware Revision:     4290",
      "Version:               MS-1.3.3",
    ]

  async def _homedstatus(self, args: List[str]) -> List[str]:
    return ["homed" if self.homed else "not homed"]

  async def _errors(self, args: List[str]) -> List[str]:
    count = int(args[0]) if args else 10
    return list(self.errors[-count:])

  async def _commandstat(self, args: List[str]) -> List[str]:
    command_id = int(args[0])
    known = self._history.get(command_id)
    if known is None:
      raise _Refused(f"Command id {command_id} not in recorded history.")
    status, command = known
    return [f"   {command_id} {status}  - {command}"]

  async def _cget(self, args: List[str]) -> List[str]:
    amplifier, register = args
    value = 0
    if amplifier == "1" and register == "24":
      value = round(self.spindle_rpm() / 60 * SPINDLE_COUNTS * 10)
    return [f"Copley {amplifier} variable {register} is: {value & 0xFFFFFFFF:x}"]

  async def _status(self, args: List[str]) -> List[str]:
    await self._idle.wait()
    await self._still.wait()
    return [f"Spindle Position: {self.spindle_position}", f"Door Position: {self.door_position}"]

  async def _abort(self, args: List[str]) -> List[str]:
    if not self._idle.is_set():
      self._stop.set()
      await self._idle.wait()
    self.abort_latched = True
    return ['Issue the "clearbuttonabort" (cba) command to re-enable the machine']

  async def _clearbuttonabort(self, args: List[str]) -> List[str]:
    self.abort_latched = False
    return []

  async def _home(self, args: List[str]) -> List[str]:
    self._require_not_latched()
    await self._still.wait()

    def done() -> None:
      self.homed = True
      self.spindle_position = SPINDLE_HOME
      self.door_position = DOOR_CLOSED
      self.presented = None

    await self._move(HOME_SECONDS, done)
    return []

  async def _open(self, args: List[str]) -> List[str]:
    self._require_not_latched()
    if len(args) != 1 or args[0] not in ("1", "2"):
      raise _Refused(f"bad bucket: {' '.join(args)!r}")
    if not self.homed:
      raise _Refused("Machine must be homed")
    bucket = int(args[0])
    await self._still.wait()

    def done() -> None:
      self.presented = bucket
      self.spindle_position = SPINDLE_AT_DOOR[bucket]
      self.door_position = DOOR_OPEN

    await self._move(OPEN_SECONDS, done)
    return []

  async def _spin(self, args: List[str]) -> List[str]:
    if len(args) != 4:
      raise _Refused(
        f'Abnormal number of parameters ({len(args)}) for command "spin".  Min: 4, Max: 4'
      )
    g, _, _, duration = (int(arg) for arg in args)
    if not self.homed:
      raise _Refused("Device must be homed before spinning")
    self._require_not_latched()
    await self._still.wait()
    loop = asyncio.get_running_loop()
    self.door_position = DOOR_CLOSED
    self.presented = None
    self.spinning = True
    self._rotor = _Spin(started=loop.time(), rpm=rpm_at(g), duration=duration)
    self._still.clear()

    def done() -> None:
      self.spindle_position = (self.spindle_position + g) % SPINDLE_COUNTS
      self._rotor = None
      self._still.set()

    try:
      await self._move(SPIN_UP_SECONDS + duration + SPIN_DOWN_SECONDS, done)
    except _Aborted:
      self._begin_coast()
      raise
    finally:
      self.spinning = False
    return []

  def _handler(self, name: str) -> Optional[Callable[[List[str]], Awaitable[List[str]]]]:
    handlers: Dict[str, Callable[[List[str]], Awaitable[List[str]]]] = {
      "version": self._version,
      "v": self._version,
      "homedstatus": self._homedstatus,
      "hss": self._homedstatus,
      "errors": self._errors,
      "commandstat": self._commandstat,
      "copleyget": self._cget,
      "cget": self._cget,
      "cstat": self._commandstat,
      "status": self._status,
      "abort": self._abort,
      "clearbuttonabort": self._clearbuttonabort,
      "cba": self._clearbuttonabort,
      "home": self._home,
      "open": self._open,
      "spin": self._spin,
    }
    return handlers.get(name)

  async def answer(self, command: str, connection: str, emit: Callable[[str], None]) -> None:
    """Answer `command` as the device does: `ACK!` at once, the rest once it has run.

    Args:
      command: the command received.
      connection: the name of the connection it came on.
      emit: sends one line back on that connection.
    """
    self.received.append((connection, command))
    command_id = self._next_id
    self._next_id += 1
    self._history[command_id] = ("RUNNING!", command)
    name, *args = command.split()
    emit(f"ACK! {command} {command_id}")
    lines: List[str] = []
    handler = self._handler(name)
    try:
      if handler is None:
        raise _Refused(f'Command "{name}" not recognized!')
      failure = self._failures.pop(name, None)
      if failure is not None:
        raise _Refused(failure.message, failure.warnings)
      lines += await handler(args)
      end = "OK!"
    except _Aborted:
      end = "ABORTED!"
    except _Refused as refused:
      self._push_error(command_id, refused.message)
      lines += list(refused.warnings) + self.errors
      end = "ERROR!"
    self._history[command_id] = (end, command)
    for line in lines:
      emit(line)
    emit(f"{end} {command} {command_id}")


class _SimulatedConnection:
  """One connection to a simulated device: commands answered one at a time, in order.

  Lines wait in a buffer, as a socket's do, so a read given up on loses none of them.
  """

  def __init__(self, device: SimulatedMicroSpin, name: str, read_timeout: float) -> None:
    self.device = device
    self.name = name
    self.read_timeout = read_timeout
    self._commands: "Optional[asyncio.Queue[str]]" = None
    self._lines: Deque[bytes] = deque()
    self._arrived: Optional[asyncio.Event] = None
    self._worker: "Optional[asyncio.Task[None]]" = None

  def _emit(self, line: str) -> None:
    """Send one line back, at once."""
    self._lines.append(line.encode("ascii") + b"\r\n")
    if self._arrived is not None:
      self._arrived.set()

  async def _serve(self) -> None:
    commands = self._commands
    assert commands is not None
    while True:
      await self.device.answer(await commands.get(), self.name, self._emit)

  async def setup(self) -> None:
    self._commands = asyncio.Queue()
    self._lines.clear()
    self._arrived = asyncio.Event()
    self._worker = asyncio.create_task(self._serve())

  async def stop(self) -> None:
    if self._worker is not None:
      self._worker.cancel()
      await asyncio.gather(self._worker, return_exceptions=True)
      self._worker = None

  async def write(self, data: bytes, timeout: Optional[float] = None) -> None:
    if self._commands is None:
      raise RuntimeError(f"simulated {self.name} connection not set up; call setup() first")
    self._commands.put_nowait(data.decode("ascii").rstrip("\r\n"))

  async def readline(self, timeout: Optional[float] = None) -> bytes:
    arrived = self._arrived
    if arrived is None:
      raise RuntimeError(f"simulated {self.name} connection not set up; call setup() first")
    timeout = self.read_timeout if timeout is None else timeout

    async def next_line() -> bytes:
      while not self._lines:
        arrived.clear()
        await arrived.wait()
      return self._lines.popleft()

    try:
      return await asyncio.wait_for(next_line(), timeout=timeout)
    except asyncio.TimeoutError as error:
      raise TimeoutError(f"no line within {timeout} s") from error


class MicroSpinSimulator(MicroSpinDriver):
  """The driver, run over a simulated device.

  Attributes:
    device: the simulated device both connections reach.
  """

  def __init__(
    self, device: Optional[SimulatedMicroSpin] = None, read_timeout: float = 30.0
  ) -> None:
    """
    Args:
      device: the simulated device to run over; a new one, moving at once, when not given.
      read_timeout: how long a read given no timeout waits for a line, in seconds, as a `Socket`'s
        own read timeout does.
    """
    self.device = SimulatedMicroSpin() if device is None else device
    self._read_timeout = read_timeout
    super().__init__(host="simulated")

  def _make_transport(self, name: str) -> Transport:
    return _SimulatedConnection(self.device, name, self._read_timeout)
