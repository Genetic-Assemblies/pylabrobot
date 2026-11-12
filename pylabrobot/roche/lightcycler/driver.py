"""Driver for the Roche LightCycler 480 II, a 96- or 384-well qPCR instrument, over TCP.

The instrument listens on five ports from a base port, 5100: keepalive (+0), events (+1),
commands (+2), results (+4) and status (+5). `wire` has the framing. After a handshake on the
keepalive port, the host sends `hi` there every second; the instrument sends events and trace lines
on the events port, each of which the host acknowledges with its sequence number; every other
message is a command, answered on the port it was sent on with a message of the same type.

A port of flo4's Go driver (koeng101/flo4, `robots/roche/lightcycler/lc480`), which ran experiments
on a LightCycler 480 II with firmware 1.8.6.1501.
"""

import asyncio
import datetime
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Literal, Optional, Protocol, Tuple

from pylabrobot.io.socket import Socket

from .errors import CommandFailedError, LightCyclerProtocolError, LightCyclerTimeoutError
from .wire import (
  ACK_RESULT,
  CTRL_INFO,
  EVENT,
  EVENTS_PORT,
  GET_RESULT_DATA,
  HEADER_SIZE,
  KEEPALIVE,
  KEEPALIVE_PORT,
  LOG_ENTRY,
  LOG_ENTRY_2,
  PORT_NAMES,
  PORT_OFFSETS,
  QUERY_LOAD_STATE,
  QUERY_RESULT_INFO,
  SET_PARAMETER,
  STATUS_4,
  STATUS_QUERY,
  SUBSYS_QUERY,
  SUBSYS_STATUS,
  SYS_INFO,
  TRACE,
  VERSION_QUERY,
  ExperimentConfig,
  Packet,
  ResultData,
  build_commands,
  decode_header,
  message_name,
  parse_result_data,
  port_for_message,
)

logger = logging.getLogger(__name__)

# Python 3.10's `asyncio.wait_for` raises `asyncio.TimeoutError`, which is not yet `TimeoutError`.
_TIMEOUTS = (TimeoutError, asyncio.TimeoutError)
# A read with no limit: the reader of each port waits as long as the connection is open.
_NO_LIMIT = 365 * 24 * 3600.0

# The instrument's states, as `SubsysStatus` reports them.
STATE_NOT_READY = 6
STATE_RUNNING = 7
STATE_IDLE = 10

# `SubsysQuery`'s eighth field: the tray and what is on it.
_TRAY_OPEN = "5"
_TRAY_CLOSED_WITH_PLATE = "4"


class Transport(Protocol):
  """What a connection is sent and read over: a `Socket`."""

  async def setup(self) -> None: ...

  async def stop(self) -> None: ...

  async def write(self, data: bytes, timeout: Optional[float] = None) -> None: ...

  async def read_exact(self, num_bytes: int, timeout: Optional[float] = None) -> bytes: ...


@dataclass(frozen=True)
class InstrumentInfo:
  """What the instrument says of itself in the handshake.

  Attributes:
    controller: what `VersionQuery` names first, `8/HTC` on a device.
    firmware_version: `1.8.6.1501` on a device.
    timestamp: the instrument's clock.
    hardware_info: the `SysInfo` fields.
    controller_info: the `CtrlInfo` fields: each controller and its firmware.
  """

  controller: str
  firmware_version: str
  timestamp: str
  event_state: Tuple[str, ...]
  hardware_info: Tuple[str, ...]
  controller_info: Tuple[str, ...]


@dataclass(frozen=True)
class TrayState:
  """Where the plate tray is and what is on it.

  Attributes:
    open: whether the tray is out.
    plate_loaded: whether the tray is in with a plate on it.
    barcode: the loaded plate's barcode; empty when it has none, or none was read.
  """

  open: bool
  plate_loaded: bool
  barcode: str = ""


@dataclass(frozen=True)
class LogEntry:
  """One event or trace line the instrument sent.

  Attributes:
    id: counting from 1 in the order received, since the driver was made.
    received_at: when it arrived, in seconds since the epoch.
    kind: `event` (message 0x000E: state changes, reads done, temperatures) or `trace` (0x0010:
      the firmware's own log).
    timestamp: the instrument's clock, `DD.MM.YYYY_HH:MM:SS`.
    code: the event or trace code: 11 a state change, 201 a read done, 202 temperatures, ...
    data: the fields after the code.
  """

  id: int
  received_at: float
  kind: Literal["event", "trace"]
  timestamp: str
  code: int
  data: Tuple[str, ...]

  @property
  def message(self) -> str:
    return " ".join(part.strip() for part in self.data if part.strip())


def _int(text: str) -> int:
  try:
    return int(text.strip())
  except ValueError:
    return 0


def _registration_timestamp() -> str:
  """What the host sends to register for events: its clock as `DD.MM.YY_HH.MM.SS_4`, as the Roche
  software does."""
  return datetime.datetime.now().strftime("%d.%m.%y_%H.%M.%S") + "_4"


class LightCycler480Driver:
  """The LightCycler 480 II's TCP protocol: commands and their answers, events, and reads.

  The defaults below are used where a call names none. Assign one on an instance to tune that
  device, or on the class to tune every device.
  """

  DEFAULT_PORT = 5100

  # How long a command may take to be answered, in seconds.
  default_timeout: float = 10.0
  # How long a status query may take, in seconds.
  default_query_timeout: float = 3.0
  # How long the handshake may take, in seconds.
  default_handshake_timeout: float = 30.0
  # How often the host says `hi`, in seconds.
  keepalive_interval: float = 1.0
  # How often a read not yet there is asked for again, in seconds.
  result_poll_interval: float = 2.0
  # How often the state is read while waiting for the instrument to be idle, in seconds.
  idle_poll_interval: float = 1.0
  # How many events and trace lines are kept, newest last.
  kept_log_entries: int = 10_000

  # Whether `setup` warns that this driver is not yet known to work on a device.
  _warn_untested = True

  def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
    """
    Args:
      host: the instrument's IP address; a device's static address is 192.168.95.41.
      port: the base port; the others are counted from it.
    """
    self.host = host
    self.port = port
    self.ports: List[int] = [port + offset for offset in PORT_OFFSETS]
    self.info: Optional[InstrumentInfo] = None
    self._io: List[Transport] = []
    self._tasks: List["asyncio.Task[None]"] = []
    self._waiters: Dict[int, "asyncio.Future[Packet]"] = {}
    self._type_locks: Dict[int, asyncio.Lock] = {}
    self._log: Deque[LogEntry] = deque(maxlen=self.kept_log_entries)
    self._next_log_id = 1
    self._lost_with: Optional[BaseException] = None

  def _make_transport(self, index: int, port: int) -> Transport:
    """What the connection to one port runs over."""
    return Socket(
      human_readable_device_name=f"Roche LightCycler 480 ({PORT_NAMES[index]})",
      host=self.host,
      port=port,
    )

  @property
  def connected(self) -> bool:
    """Whether every connection is open."""
    return bool(self._io) and self._lost_with is None

  # -- lifecycle --------------------------------------------------------------------------------

  async def setup(self) -> None:
    """Open the five connections, shake hands, and register for events.

    Raises:
      ConnectionError: A port did not accept a connection, or closed during the handshake.
      TimeoutError: The handshake did not finish within `default_handshake_timeout`.
    """
    if self._warn_untested:
      logger.warning(
        "LightCycler480Driver is a Python port of a Go driver that ran on a LightCycler 480 II; "
        "the port itself has not yet run on an instrument. If it works on yours, please say so "
        "on discuss.pylabrobot.org or in a pull request."
      )
    if self._io:
      raise RuntimeError("the LightCycler is already set up; call stop() first")
    transports = [self._make_transport(i, port) for i, port in enumerate(self.ports)]
    opened: List[Transport] = []
    try:
      for transport in transports:
        await transport.setup()
        opened.append(transport)
      self._io = transports
      self._lost_with = None
      self.info = await asyncio.wait_for(self._handshake(), timeout=self.default_handshake_timeout)
    except BaseException as error:
      self._io = []
      for transport in opened:
        try:
          await transport.stop()
        except Exception as closing:
          logger.debug("[lightcycler] closing after a failed setup: %s", closing)
      if isinstance(error, asyncio.TimeoutError) and not isinstance(error, TimeoutError):
        raise TimeoutError("the LightCycler's handshake did not finish") from error
      raise
    loop = asyncio.get_running_loop()
    self._tasks = [loop.create_task(self._read_loop(i)) for i in range(len(self._io))]
    self._tasks.append(loop.create_task(self._keepalive_loop()))
    await self._send(EVENTS_PORT, Packet(VERSION_QUERY, _registration_timestamp().encode()))
    logger.info(
      "[lightcycler] connected to %s: controller %s, firmware %s",
      self.host,
      self.info.controller,
      self.info.firmware_version,
    )

  async def stop(self) -> None:
    """Close the connections. Commands waiting for an answer raise `ConnectionError`."""
    tasks, self._tasks = self._tasks, []
    # On Python 3.10 a cancel that lands as a read completes is lost inside `asyncio.wait_for`, and
    # the reader reads on; so each is cancelled until it has ended.
    pending = set(tasks)
    while pending:
      for task in pending:
        task.cancel()
      _, pending = await asyncio.wait(pending, timeout=0.1)
    self._lost(ConnectionError("the LightCycler driver was stopped"))
    transports, self._io = self._io, []
    for transport in transports:
      try:
        await transport.stop()
      except Exception as error:
        logger.debug("[lightcycler] closing a connection: %s", error)

  # -- the wire ---------------------------------------------------------------------------------

  async def _send(self, index: int, packet: Packet) -> None:
    logger.debug("[lightcycler] %s >>> %s %r", PORT_NAMES[index], packet.name, packet.payload)
    await self._io[index].write(packet.encode())

  @staticmethod
  async def _read_packet(io: Transport, timeout: float) -> Packet:
    header = await io.read_exact(HEADER_SIZE, timeout=timeout)
    message_type, length = decode_header(header)
    payload = await io.read_exact(length, timeout=timeout) if length else b""
    return Packet(message_type, payload)

  async def _handshake(self) -> InstrumentInfo:
    """`hi`, then `?` for the version, event state, status, hardware and controllers, on the
    keepalive port, before anything else reads it."""
    io = self._io[KEEPALIVE_PORT]
    await io.write(Packet(KEEPALIVE, b"hi").encode())
    await self._read_packet(io, _NO_LIMIT)

    async def ask(message_type: int) -> List[str]:
      await io.write(Packet(message_type, b"?").encode())
      while True:
        answer = await self._read_packet(io, _NO_LIMIT)
        if answer.type == message_type:
          return answer.fields()

    version = await ask(VERSION_QUERY) + ["", "", ""]
    event_state = await ask(EVENT)
    await ask(STATUS_4)
    hardware = await ask(SYS_INFO)
    controllers = await ask(CTRL_INFO)
    return InstrumentInfo(
      controller=version[0],
      firmware_version=version[1],
      timestamp=version[2],
      event_state=tuple(event_state),
      hardware_info=tuple(hardware),
      controller_info=tuple(controllers),
    )

  def _lost(self, error: BaseException) -> None:
    """Record that the connection is gone, and fail every command waiting for an answer."""
    if self._lost_with is None:
      self._lost_with = error
    waiters, self._waiters = self._waiters, {}
    for future in waiters.values():
      if not future.done():
        future.set_exception(ConnectionError(str(error)))

  async def _read_loop(self, index: int) -> None:
    io = self._io[index]
    try:
      while True:
        await self._dispatch(index, await self._read_packet(io, _NO_LIMIT))
    except asyncio.CancelledError:
      raise
    except Exception as error:
      logger.warning("[lightcycler] the %s connection closed: %s", PORT_NAMES[index], error)
      self._lost(ConnectionError(f"the LightCycler's {PORT_NAMES[index]} connection closed"))

  async def _keepalive_loop(self) -> None:
    try:
      while True:
        await self._send(KEEPALIVE_PORT, Packet(KEEPALIVE, b"hi"))
        await asyncio.sleep(self.keepalive_interval)
    except asyncio.CancelledError:
      raise
    except Exception as error:
      logger.warning("[lightcycler] keepalive failed: %s", error)
      self._lost(ConnectionError("the LightCycler's keepalive connection closed"))

  async def _acknowledge(self, index: int, packet: Packet, fields: List[str]) -> None:
    """Send back an unsolicited message's sequence number, as the instrument expects."""
    try:
      await self._send(index, Packet(packet.type, fields[0].encode("ascii", errors="replace")))
    except Exception as error:
      logger.warning("[lightcycler] could not acknowledge %s: %s", packet.name, error)

  def _record(self, kind: Literal["event", "trace"], fields: List[str]) -> None:
    fields = fields + [""] * (3 - len(fields))
    entry = LogEntry(
      id=self._next_log_id,
      received_at=time.time(),
      kind=kind,
      timestamp=fields[1],
      code=_int(fields[2]),
      data=tuple(fields[3:]),
    )
    self._next_log_id += 1
    self._log.append(entry)
    logger.debug("[lightcycler] %s %d: %s", kind, entry.code, entry.message)

  async def _dispatch(self, index: int, packet: Packet) -> None:
    if packet.type == KEEPALIVE:
      return
    fields = packet.fields()
    if packet.type in (EVENT, TRACE):
      await self._acknowledge(index, packet, fields)
      self._record("event" if packet.type == EVENT else "trace", fields)
      return
    if packet.type in (SYS_INFO, CTRL_INFO, LOG_ENTRY, LOG_ENTRY_2):
      await self._acknowledge(index, packet, fields)
      return
    future = self._waiters.pop(packet.type, None)
    if future is None or future.done():
      logger.debug("[lightcycler] unasked-for %s on %s: %r", packet.name, PORT_NAMES[index], fields)
      return
    future.set_result(packet)

  # -- commands ---------------------------------------------------------------------------------

  async def command(
    self, message_type: int, payload: bytes, timeout: Optional[float] = None
  ) -> Packet:
    """Send a message on its port, and return the instrument's answer: the next message of the
    same type. Commands of one type wait their turn.

    Args:
      timeout: how long to wait for the answer, in seconds; `default_timeout` when not given.

    Raises:
      ConnectionError: The driver is not set up, or a connection closed.
      LightCyclerTimeoutError: No answer came within `timeout`.
    """
    timeout = self.default_timeout if timeout is None else timeout
    lock = self._type_locks.setdefault(message_type, asyncio.Lock())
    async with lock:
      if not self.connected:
        raise ConnectionError(str(self._lost_with or "the LightCycler is not set up"))
      future: "asyncio.Future[Packet]" = asyncio.get_running_loop().create_future()
      self._waiters[message_type] = future
      try:
        await self._send(port_for_message(message_type), Packet(message_type, payload))
        return await asyncio.wait_for(future, timeout=timeout)
      except _TIMEOUTS as error:
        raise LightCyclerTimeoutError(message_name(message_type), timeout) from error
      finally:
        if self._waiters.get(message_type) is future:
          del self._waiters[message_type]

  async def query(self, message_type: int, timeout: Optional[float] = None) -> Packet:
    """A command whose payload is a single space, as the queries are sent."""
    return await self.command(message_type, b" ", timeout=timeout)

  async def _quietly(self, message_type: int, payload: bytes, timeout: float) -> None:
    """A command whose answer is not needed; a failure is logged, as the Roche software ignores
    these."""
    try:
      await self.command(message_type, payload, timeout=timeout)
    except Exception as error:
      logger.info("[lightcycler] %s went unanswered: %s", message_name(message_type), error)

  @staticmethod
  def _check(packet: Packet) -> List[str]:
    fields = packet.fields()
    if not fields or fields[0] != "0":
      raise CommandFailedError(packet.name, fields)
    return fields

  # -- what the instrument reports ---------------------------------------------------------------

  async def request_instrument_state(self, timeout: Optional[float] = None) -> int:
    """The instrument's state: `STATE_NOT_READY` (6; the tray open, or no plate),
    `STATE_RUNNING` (7) or `STATE_IDLE` (10; a plate in, ready to run).

    Raises:
      LightCyclerProtocolError: The answer held no state.
    """
    timeout = self.default_query_timeout if timeout is None else timeout
    fields = (await self.command(SUBSYS_STATUS, b"0", timeout=timeout)).fields()
    try:
      return int(fields[0])
    except (IndexError, ValueError) as error:
      raise LightCyclerProtocolError(f"SubsysStatus answered {fields}, with no state") from error

  async def request_tray_state(self) -> TrayState:
    """Where the tray is, whether a plate is on it, and, if one is loaded, its barcode.

    Raises:
      LightCyclerProtocolError: `SubsysQuery` answered with fewer than 8 fields.
    """
    fields = (await self.query(SUBSYS_QUERY, timeout=self.default_query_timeout)).fields()
    if len(fields) < 8:
      raise LightCyclerProtocolError(f"SubsysQuery answered {fields}, with no tray state")
    is_open = fields[7] == _TRAY_OPEN
    loaded = fields[7] == _TRAY_CLOSED_WITH_PLATE
    barcode = ""
    if loaded:
      try:
        load = await self.query(QUERY_LOAD_STATE, timeout=self.default_query_timeout)
      except Exception as error:
        logger.info("[lightcycler] could not read the plate's barcode: %s", error)
      else:
        load_fields = load.fields()
        if len(load_fields) >= 3:
          barcode = load_fields[2]
    return TrayState(open=is_open, plate_loaded=loaded, barcode=barcode)

  async def wait_idle(self, timeout: float) -> None:
    """Wait until the instrument is idle, reading its state each `idle_poll_interval`.

    Raises:
      TimeoutError: It was not idle within `timeout` seconds.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
      state = await self.request_instrument_state()
      if state == STATE_IDLE:
        return
      if loop.time() + self.idle_poll_interval > deadline:
        raise TimeoutError(f"the LightCycler was still in state {state} after {timeout} s")
      await asyncio.sleep(self.idle_poll_interval)

  async def wait_until_running(self, timeout: float) -> bool:
    """Wait until the instrument has left idle, as a run it was sent does; whether it did within
    `timeout` seconds."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
      if await self.request_instrument_state() != STATE_IDLE:
        return True
      if loop.time() + self.idle_poll_interval > deadline:
        return False
      await asyncio.sleep(self.idle_poll_interval)

  def logs(self, since_id: int = 0, limit: int = 100) -> List[LogEntry]:
    """The events and trace lines received after `since_id`, oldest first, at most `limit`."""
    entries: List[LogEntry] = []
    for entry in self._log:
      if entry.id > since_id:
        entries.append(entry)
        if len(entries) >= limit:
          break
    return entries

  # -- runs -------------------------------------------------------------------------------------

  async def drain_stale_results(self) -> int:
    """Read and acknowledge reads a past run left behind, so they do not stand in for the next
    run's; how many there were."""
    drained = 0
    for number in range(1, 50):
      try:
        answer = await self.command(GET_RESULT_DATA, f"{number}\n".encode(), timeout=2.0)
      except Exception:
        break
      fields = answer.fields()
      if not fields or fields[0] != "0":
        break
      await self._quietly(QUERY_RESULT_INFO, b" ", self.default_timeout)
      await self._quietly(ACK_RESULT, str(number).encode(), self.default_timeout)
      drained += 1
    if drained:
      logger.info("[lightcycler] drained %d stale read(s)", drained)
    return drained

  async def prepare_run(self) -> None:
    """What the Roche software asks before it defines a run: the load state, parameter 15, and
    the status."""
    await self._quietly(QUERY_LOAD_STATE, b" ", self.default_timeout)
    await self._quietly(SET_PARAMETER, b"15", self.default_timeout)
    await self._quietly(STATUS_QUERY, b" ", self.default_timeout)

  async def send_experiment(self, config: ExperimentConfig) -> None:
    """Define `config` and start it.

    Raises:
      CommandFailedError: The instrument refused a command; those after it are not sent.
    """
    commands = build_commands(config)
    for packet in commands:
      self._check(await self.command(packet.type, packet.payload))
    logger.info(
      "[lightcycler] started experiment %s: %d program(s), %d read(s)",
      config.guid,
      len(config.programs),
      config.total_acquisitions,
    )

  async def request_result(self, number: int) -> ResultData:
    """Read `number`, counting from 1 in the run; its status is 99 while it is not there."""
    answer = await self.command(GET_RESULT_DATA, f"{number}\n".encode())
    try:
      return parse_result_data(answer.fields())
    except ValueError as error:
      raise LightCyclerProtocolError(str(error)) from error

  async def wait_for_result(self, number: int, guid: str, timeout: float) -> ResultData:
    """Ask for read `number` of experiment `guid` each `result_poll_interval` until it is there.

    Raises:
      TimeoutError: It was not there within `timeout` seconds.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
      result = await self.request_result(number)
      if result.status == 0 and result.guid == guid:
        return result
      if loop.time() + self.result_poll_interval > deadline:
        raise TimeoutError(f"read {number} of experiment {guid} was not there after {timeout} s")
      await asyncio.sleep(self.result_poll_interval)

  async def acknowledge_result(self, number: int) -> None:
    """Tell the instrument read `number` was received, so it moves on to the next."""
    await self._quietly(QUERY_RESULT_INFO, b" ", 5.0)
    await self._quietly(ACK_RESULT, str(number).encode(), 5.0)

  async def finish_run(self) -> None:
    """What the Roche software asks once a run is over: the status, and parameter 15."""
    await self._quietly(STATUS_QUERY, b" ", self.default_timeout)
    await self._quietly(SET_PARAMETER, b"15", self.default_timeout)
