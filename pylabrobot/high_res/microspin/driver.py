"""Driver for the HighRes Biosolutions MicroSpin, a two-bucket microplate centrifuge.

The MicroSpin answers a text protocol on TCP port 1000. Each command is a line ending `\\r\\n`; the
device answers `ACK! <command> <id>`, then any data lines, then exactly one of `OK!`, `ERROR!` or
`ABORTED!`, each followed by the command and its id.

The device answers one command at a time on each connection, and keeps one state across all of
them. `home`, `open`, `spin` and `status` wait their turn on the machine and do not finish until
the rotor and door have stopped, so this driver holds two connections: one for those, and one for
the commands answered at once, so that `abort` reaches the device while a spin is running.

After an `abort` the rotor coasts to a stop: about 40 s from 320 rpm and 110 s from 500 x g on a
device. A command sent to the machine in that time can leave the device answering nothing that
waits its turn until it is power-cycled, so this driver sends none until the spindle reads stopped.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Protocol

from pylabrobot.io.socket import Socket

from .errors import (
  ErrorEntry,
  MicroSpinAbortedError,
  MicroSpinError,
  MicroSpinProtocolError,
  MicroSpinTimeoutError,
  error_for,
  parse_error_entry,
)

logger = logging.getLogger(__name__)

# A bucket, as the device numbers them.
Bucket = Literal[1, 2]

# What the device says of a command it was asked about with `cstat`.
CommandStatus = Literal["OK", "ERROR", "ABORTED", "FAIL", "RUNNING"]
_COMMAND_STATUSES: Dict[str, CommandStatus] = {
  "OK!": "OK",
  "ERROR!": "ERROR",
  "ABORTED!": "ABORTED",
  "FAIL!": "FAIL",
  "RUNNING!": "RUNNING",
}
# The spindle's amplifier, and its register holding the spindle's velocity in 0.1 counts/s.
_SPINDLE_AMPLIFIER = 1
_VELOCITY_REGISTER = 24
_CGET = re.compile(
  r"^Copley (?P<amplifier>\d+) variable (?P<register>\d+) is: (?P<value>[0-9a-fA-F]+)$"
)
_CSTAT = re.compile(r"^\s*(?P<id>\d+) (?P<status>[A-Z]+!)\s+- (?P<command>.*)$")

_ACK = re.compile(r"^ACK! (?P<command>.*) (?P<id>\d+)$")
_END = re.compile(r"^(?P<status>OK!|ERROR!|ABORTED!) (?P<command>.*) (?P<id>\d+)$")

# Python 3.10's `asyncio.wait_for` raises `asyncio.TimeoutError`, which is not yet `TimeoutError`.
_TIMEOUTS = (TimeoutError, asyncio.TimeoutError)
# A transport given no read timeout uses its own, 30 s for a `Socket`, and a spin sends nothing for
# longer than that; so a read with no limit asks for a year.
_NO_LIMIT = 365 * 24 * 3600.0


class Transport(Protocol):
  """What a connection is sent and read over: a `Socket`, or a simulated device."""

  async def setup(self) -> None: ...

  async def stop(self) -> None: ...

  async def write(self, data: bytes, timeout: Optional[float] = None) -> None: ...

  async def readline(self, timeout: Optional[float] = None) -> bytes: ...


@dataclass(frozen=True)
class MicroSpinStatus:
  """What `status` reports.

  Attributes:
    spindle_position: the rotor's angle, in the spindle drive's counts.
    door_position: the door's position, in the door drive's counts.
  """

  spindle_position: int
  door_position: int


def parse_key_values(lines: List[str]) -> Dict[str, str]:
  """`Key: value` lines as a dict, split at the first colon."""
  out: Dict[str, str] = {}
  for line in lines:
    key, separator, value = line.partition(":")
    if separator:
      out[key.strip()] = value.strip()
  return out


class _Connection:
  """One connection to the device, carrying one command at a time.

  A command given up on before its last line arrived leaves that line to come. The next command
  first reads it away, so that it reads only its own answer.
  """

  def __init__(self, io: Transport, name: str) -> None:
    self.io = io
    self.name = name
    self.lock = asyncio.Lock()
    self._unfinished = 0
    # The id the device acknowledged the command under way with.
    self._acked_id: Optional[int] = None

  async def _readline(self, deadline: Optional[float]) -> str:
    """The next line, waiting until `deadline` on the loop's clock; None waits without limit."""
    if deadline is None:
      timeout = _NO_LIMIT
    else:
      timeout = max(0.0, deadline - asyncio.get_running_loop().time())
    raw = await self.io.readline(timeout=timeout)
    if not raw:
      raise ConnectionError(f"the MicroSpin closed its {self.name} connection")
    return raw.decode("ascii", errors="replace").rstrip("\r\n")

  async def _read_away_unfinished(self, deadline: Optional[float]) -> None:
    """Read up to the last line of each command given up on."""
    while self._unfinished > 0:
      line = await self._readline(deadline)
      if _END.match(line):
        self._unfinished -= 1
        logger.debug("[microspin] read away %r on the %s connection", line, self.name)

  async def _exchange(self, command: str, deadline: Optional[float]) -> List[str]:
    await self._read_away_unfinished(deadline)
    self._acked_id = None
    logger.debug("[microspin] %s >>> %s", self.name, command)
    await self.io.write(command.encode("ascii") + b"\r\n")
    # Counted as unfinished until its own last line is read.
    self._unfinished += 1
    ack = await self._readline(deadline)
    acked = _ACK.match(ack)
    if acked is None or acked.group("command") != command:
      raise MicroSpinProtocolError(command, ack, "expected its ACK!")
    command_id = int(acked.group("id"))
    self._acked_id = command_id
    lines: List[str] = []
    while True:
      line = await self._readline(deadline)
      end = _END.match(line)
      if end is None or int(end.group("id")) != command_id:
        lines.append(line)
        continue
      self._unfinished -= 1
      status = end.group("status")
      logger.debug("[microspin] %s <<< %s (%d lines)", self.name, status, len(lines))
      if status == "OK!":
        return lines
      if status == "ABORTED!":
        raise MicroSpinAbortedError(command)
      raise error_for(command, command_id, lines)

  async def send(self, command: str, timeout: Optional[float]) -> List[str]:
    """Send a command and return the lines between its `ACK!` and its `OK!`.

    Args:
      command: the command, without its line ending.
      timeout: how long to wait for the whole answer, in seconds; None waits for as long as it takes.

    Raises:
      MicroSpinError: The device ended it with `ERROR!`.
      MicroSpinAbortedError: The device ended it with `ABORTED!`.
      MicroSpinProtocolError: The device answered with a line this driver cannot read.
      MicroSpinTimeoutError: The answer did not finish within `timeout`.
    """
    async with self.lock:
      deadline = None if timeout is None else asyncio.get_running_loop().time() + timeout
      try:
        return await asyncio.wait_for(self._exchange(command, deadline), timeout=timeout)
      except _TIMEOUTS as error:
        raise MicroSpinTimeoutError(command, self._acked_id, timeout) from error


class MicroSpinDriver:
  """The HighRes Biosolutions MicroSpin: home it, present a bucket, spin, abort.

  A spin needs the device homed, both buckets seated on the rotor pins and balanced, and the door
  able to close; the device closes and locks the door itself. Presenting a bucket opens the door.

  The defaults below are used where a call names none. Assign one on an instance to tune that
  device, or on the class to tune every device.
  """

  # The device's factory port.
  DEFAULT_PORT = 1000
  # The highest relative centrifugal force the device spins at, in x g.
  MAX_G = 3000
  # Encoder counts per turn of the spindle.
  SPINDLE_COUNTS_PER_TURN = 8192
  # Below this speed the spindle counts as stopped, in rpm. A stopped spindle reads 0.
  STOPPED_RPM = 0.5

  # Below this g, the spindle-stopped sensor has failed to latch at the end of a spin, so the spin
  # never finished.
  LOW_G_WARNING = 30.0
  # Below this deceleration a spin-down is slow: one from `spin 1000 100 20 10` took about 7 min.
  SLOW_DECELERATION_WARNING = 0.4
  # Below this deceleration a spin-down has never finished: `spin 1000 100 10 10` ran for over
  # 30 min.
  STUCK_DECELERATION_WARNING = 0.2

  # The acceleration and deceleration of a spin, as fractions of the device's maximum.
  default_acceleration: float = 1.0
  default_deceleration: float = 1.0
  # How long a command answered at once may take, in seconds.
  default_timeout: float = 30.0
  # How long `home` may take, in seconds.
  default_home_timeout: float = 120.0
  # How long presenting a bucket may take, in seconds.
  default_present_timeout: float = 60.0
  # How much longer than its time at speed a spin may take, for both ramps, in seconds.
  default_spin_timeout_margin: float = 180.0
  # How long `abort` may take, in seconds. A device answered within 2 s, the rotor still coasting.
  default_abort_timeout: float = 30.0
  # How long `wait_for_spindle_stopped` waits in all, and between readings, in seconds.
  default_spindle_stop_timeout: float = 1800.0
  default_spindle_poll_interval: float = 2.0

  def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
    """
    Args:
      host: the device's IP address or name. The factory address is 192.168.127.60.
      port: its remote-control port.
    """
    self.host = host
    self.port = port
    self._motion = _Connection(self._make_transport("motion"), "motion")
    self._control = _Connection(self._make_transport("control"), "control")
    # Whether this driver set the abort latch and has not released it. The device reports no way
    # to read it, and a latch set at the front panel is not seen here.
    self._abort_latched = False

  @property
  def abort_latched(self) -> bool:
    """Whether this driver set the abort latch and has not released it."""
    return self._abort_latched

  def _make_transport(self, name: str) -> Transport:
    """What one connection runs over."""
    return Socket(
      human_readable_device_name=f"HighRes MicroSpin ({name})",
      host=self.host,
      port=self.port,
    )

  # -- lifecycle --------------------------------------------------------------------------------

  async def request_version(self) -> Dict[str, str]:
    """The device's product name, serial number and firmware versions, by the names it gives."""
    return parse_key_values(await self._control.send("version", self.default_timeout))

  async def setup(self) -> None:
    """Open both connections and read the device's version.

    Raises:
      ConnectionError: The device did not accept a connection.
    """
    logger.warning(
      "MicroSpinDriver has been run on one MicroSpin (firmware MS-1.3.3), with empty buckets at "
      "500 x g only. If it works on yours, or under other loads, please say so on "
      "discuss.pylabrobot.org or in a pull request."
    )
    await self._motion.io.setup()
    try:
      await self._control.io.setup()
    except BaseException:
      await self._motion.io.stop()
      raise
    version = await self.request_version()
    logger.info(
      "[microspin] connected to %s, serial %s, version %s",
      version.get("Product Name"),
      version.get("Serial Number"),
      version.get("Version"),
    )

  async def stop(self) -> None:
    """Close both connections."""
    try:
      await self._motion.io.stop()
    finally:
      await self._control.io.stop()

  # -- what the device reports --------------------------------------------------------------------

  async def request_homed(self) -> bool:
    """Whether the device is homed. Answered at once, during motion too."""
    lines = await self._control.send("homedstatus", self.default_timeout)
    return bool(lines) and lines[0].strip().lower() == "homed"

  async def request_errors(self, count: int = 10) -> List[ErrorEntry]:
    """The newest entries of the device's error stack, oldest first.

    Args:
      count: how many.
    """
    if count < 1:
      raise ValueError(f"count must be at least 1, got {count}")
    lines = await self._control.send(f"errors {count}", self.default_timeout)
    return [entry for entry in map(parse_error_entry, lines) if entry is not None]

  async def request_command_status(self, command_id: int) -> CommandStatus:
    """What the device says of a command, by the id it acknowledged it with. Answered at once.

    A command can end without its last line reaching the client: one the device gave up on is
    `FAIL`, one still going is `RUNNING`. `MicroSpinTimeoutError.command_id` is the id to ask about.

    Raises:
      MicroSpinError: The device has no record of the command.
    """
    lines = await self._control.send(f"cstat {command_id}", self.default_timeout)
    for line in lines:
      match = _CSTAT.match(line)
      if match is not None and int(match.group("id")) == command_id:
        status = _COMMAND_STATUSES.get(match.group("status"))
        if status is not None:
          return status
    raise MicroSpinProtocolError(f"cstat {command_id}", "\n".join(lines), "expected its status")

  async def request_spindle_velocity(self) -> float:
    """The spindle's speed, in rpm, read from its amplifier. Answered at once, during a spin or a
    coast too.

    Raises:
      MicroSpinProtocolError: The device did not report it.
    """
    command = f"cget {_SPINDLE_AMPLIFIER} {_VELOCITY_REGISTER}"
    lines = await self._control.send(command, self.default_timeout)
    for line in lines:
      match = _CGET.match(line.strip())
      if match is not None and int(match.group("register")) == _VELOCITY_REGISTER:
        value = int(match.group("value"), 16)
        if value & (1 << 31):
          value -= 1 << 32
        return value * 0.1 / self.SPINDLE_COUNTS_PER_TURN * 60
    raise MicroSpinProtocolError(command, "\n".join(lines), "expected the spindle's velocity")

  async def wait_for_spindle_stopped(
    self,
    timeout: Optional[float] = None,
    poll_interval: Optional[float] = None,
  ) -> None:
    """Wait until the spindle reads stopped, reading its velocity each `poll_interval`.

    Sends nothing that waits its turn on the machine, so it is safe while the rotor coasts after an
    `abort`. A spin that has been sent but not yet started turning reads stopped too.

    Args:
      timeout: how long to wait in all, in seconds; `default_spindle_stop_timeout` when not given.
      poll_interval: how long between readings, in seconds; `default_spindle_poll_interval` when not
        given.

    Raises:
      TimeoutError: The spindle had not stopped within `timeout`.
    """
    timeout = self.default_spindle_stop_timeout if timeout is None else timeout
    poll_interval = self.default_spindle_poll_interval if poll_interval is None else poll_interval
    if poll_interval <= 0:
      raise ValueError(f"poll_interval must be positive, got {poll_interval}")
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
      rpm = await self.request_spindle_velocity()
      if abs(rpm) < self.STOPPED_RPM:
        return
      if loop.time() + poll_interval > deadline:
        raise TimeoutError(f"the spindle was still turning at {rpm:.0f} rpm after {timeout} s")
      logger.debug("[microspin] spindle at %.0f rpm; waiting", rpm)
      await asyncio.sleep(poll_interval)

  def _require_not_latched(self) -> None:
    if self._abort_latched:
      raise RuntimeError(
        "the abort latch is set; call wait_for_spindle_stopped() and clear_abort() first"
      )

  async def request_status(self, timeout: Optional[float] = None) -> MicroSpinStatus:
    """Where the rotor and the door are.

    The device answers once any motion has finished, so a status during a spin returns when the
    rotor has stopped.

    Args:
      timeout: how long to wait, in seconds; `default_timeout` when not given.

    Raises:
      RuntimeError: The abort latch is set; nothing is sent.
      MicroSpinProtocolError: The device did not report both positions.
    """
    self._require_not_latched()
    timeout = self.default_timeout if timeout is None else timeout
    lines = await self._motion.send("status", timeout)
    values = parse_key_values(lines)
    try:
      return MicroSpinStatus(
        spindle_position=int(values["Spindle Position"]),
        door_position=int(values["Door Position"]),
      )
    except (KeyError, ValueError) as error:
      raise MicroSpinProtocolError("status", "\n".join(lines), "expected both positions") from error

  # -- motion -------------------------------------------------------------------------------------

  async def home(self, timeout: Optional[float] = None) -> None:
    """Home the door and the spindle. The device needs this after power-on before it moves.

    Args:
      timeout: how long it may take, in seconds; `default_home_timeout` when not given.
    """
    self._require_not_latched()
    timeout = self.default_home_timeout if timeout is None else timeout
    await self._motion.send("home", timeout)

  async def present_bucket(self, bucket: Bucket, timeout: Optional[float] = None) -> None:
    """Open the door and turn the rotor so `bucket` is at the door, ready for a plate.

    Args:
      bucket: 1 or 2.
      timeout: how long it may take, in seconds; `default_present_timeout` when not given.
    """
    if bucket not in (1, 2):
      raise ValueError(f"bucket must be 1 or 2, got {bucket}")
    self._require_not_latched()
    timeout = self.default_present_timeout if timeout is None else timeout
    await self._motion.send(f"open {bucket}", timeout)

  def _warn_about_spin(self, g: float, deceleration: float) -> None:
    """Log what is known to go wrong with a spin like this one."""
    if g < self.LOW_G_WARNING:
      logger.warning(
        "[microspin] spinning at %s x g, below %s x g: the spin may never finish",
        g,
        self.LOW_G_WARNING,
      )
    if deceleration < self.STUCK_DECELERATION_WARNING:
      logger.warning(
        "[microspin] deceleration %s, below %s: the spin-down may never finish",
        deceleration,
        self.STUCK_DECELERATION_WARNING,
      )
    elif deceleration < self.SLOW_DECELERATION_WARNING:
      logger.warning(
        "[microspin] deceleration %s, below %s: the spin-down may take several minutes",
        deceleration,
        self.SLOW_DECELERATION_WARNING,
      )

  async def spin(
    self,
    g: float,
    duration: float,
    acceleration: Optional[float] = None,
    deceleration: Optional[float] = None,
    timeout: Optional[float] = None,
  ) -> None:
    """Close the door, spin, and return once the rotor has stopped.

    Args:
      g: the relative centrifugal force at speed, in x g, from 1 to `MAX_G`. Sent rounded to whole
        x g.
      duration: the time at speed, in seconds, at least 1. Sent rounded to whole seconds.
      acceleration: as a fraction of the device's maximum, above 0 and at most 1. Sent as a whole
        percent. `default_acceleration` when not given.
      deceleration: as for `acceleration`; `default_deceleration` when not given.
      timeout: how long the spin may take in all, in seconds; `duration` plus
        `default_spin_timeout_margin` when not given.

    Raises:
      ValueError: An argument is out of range; nothing is sent.
      RuntimeError: The abort latch is set; nothing is sent.
      DoorLockPinError: The device could not confirm the door was locked.
      MicroSpinAbortedError: An `abort` stopped it.
    """
    acceleration = self.default_acceleration if acceleration is None else acceleration
    deceleration = self.default_deceleration if deceleration is None else deceleration
    if not 1 <= g <= self.MAX_G:
      raise ValueError(f"g must be from 1 to {self.MAX_G}, got {g}")
    if duration < 1:
      raise ValueError(f"duration must be at least 1 s, got {duration}")
    if not 0 < acceleration <= 1:
      raise ValueError(f"acceleration must be above 0 and at most 1, got {acceleration}")
    if not 0 < deceleration <= 1:
      raise ValueError(f"deceleration must be above 0 and at most 1, got {deceleration}")
    self._require_not_latched()
    self._warn_about_spin(g, deceleration)
    timeout = duration + self.default_spin_timeout_margin if timeout is None else timeout
    accel_percent = max(1, round(acceleration * 100))
    decel_percent = max(1, round(deceleration * 100))
    command = f"spin {round(g)} {accel_percent} {decel_percent} {round(duration)}"
    await self._motion.send(command, timeout)

  # -- stopping -----------------------------------------------------------------------------------

  async def abort(self, timeout: Optional[float] = None) -> None:
    """Stop whatever is moving, and set the abort latch. The rotor then coasts to a stop.

    A command the abort stopped ends with `MicroSpinAbortedError`. Until `clear_abort`, this driver
    sends nothing that waits its turn on the machine (`home`, `open`, `spin`, `status`): on a
    device, an `open` sent 1.7 s after an abort never answered, and from then on nothing that waits
    its turn answered until the device was power-cycled. `wait_for_spindle_stopped`, then
    `clear_abort`, and `reset` does both.

    Args:
      timeout: how long it may take, in seconds; `default_abort_timeout` when not given.
    """
    timeout = self.default_abort_timeout if timeout is None else timeout
    self._abort_latched = True
    await self._control.send("abort", timeout)

  async def clear_abort(self) -> None:
    """Release the abort latch, set by `abort` or the front-panel button.

    Raises:
      RuntimeError: The spindle is still turning; nothing is sent.
    """
    rpm = await self.request_spindle_velocity()
    if abs(rpm) >= self.STOPPED_RPM:
      raise RuntimeError(
        f"the spindle is still turning at {rpm:.0f} rpm; call wait_for_spindle_stopped() first"
      )
    await self._control.send("clearbuttonabort", self.default_timeout)
    self._abort_latched = False

  async def reset(self, timeout: Optional[float] = None) -> MicroSpinStatus:
    """Abort, wait for the rotor to coast to a stop, release the latch, and read the status.

    An `abort` refused by the device is logged and passed over. Reset does not home;
    `request_homed` says whether the device needs it.

    Args:
      timeout: how long to wait for the rotor, in seconds; `default_spindle_stop_timeout` when not
        given.

    Returns:
      The status once the rotor has stopped.

    Raises:
      TimeoutError: The spindle had not stopped within `timeout`.
    """
    try:
      await self.abort()
    except MicroSpinError as error:
      logger.info("[microspin] abort refused during reset, passed over: %s", error)
    await self.wait_for_spindle_stopped(timeout=timeout)
    await self.clear_abort()
    return await self.request_status()
