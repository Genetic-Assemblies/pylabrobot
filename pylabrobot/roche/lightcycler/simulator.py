"""A simulated LightCycler 480 II, listening on five TCP ports and answering as the instrument does.

`SimulatedLightCycler480` is the instrument: a port of flo4's mock (`lc480/mock.go`), answering the
handshake, the status queries, the commands that define and start a run, and the reads, with the
payloads a device sends. It serves any number of runs, one after another, each run's steps taking
`step_delay` seconds plus `seconds_per_second` of each second they hold. `LightCycler480Simulator`
is the driver connected to one over loopback sockets, so everything above the wire runs as it does
against an instrument.

The tray is pressed open and shut by a button; `SimulatedTrayButton` presses this one's.
"""

import asyncio
import datetime
import logging
import random
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from .driver import STATE_IDLE, STATE_NOT_READY, STATE_RUNNING, LightCycler480Driver
from .wire import (
  ACK_RESULT,
  CREATE_EXPERIMENT,
  CTRL_INFO,
  EVENT,
  EVENTS_PORT,
  GET_RESULT_DATA,
  HEADER_SIZE,
  KEEPALIVE,
  KEEPALIVE_PORT,
  PROTOCOL_STEP,
  QUERY_LOAD_STATE,
  QUERY_RESULT_INFO,
  SET_PARAMETER,
  START_RUN,
  STATUS_4,
  STATUS_QUERY,
  SUBSYS_QUERY,
  SUBSYS_STATUS,
  SYS_INFO,
  THERMAL_PARAMS,
  TRACE,
  VERSION_QUERY,
  Packet,
  WireStep,
  decode_header,
)

logger = logging.getLogger(__name__)

CONTROLLER = "8/HTC"
FIRMWARE_VERSION = "1.8.6.1501"

# What a device answers `StatusQuery` with: counters, lamp intensities and the like.
_STATUS = (
  "248671\n1495261\n293098\n67\n58\n4064\n4057\n1\n20\n0\n"
  "45\n16946\n8250\n2277\n51\n555043\n6\n6674\n6477\n2500\n"
  "0\n1625644356\n1065064231\n1129670778\n1200000\n"
)
# `SysInfo`, with a made-up serial number and MAC address.
_HARDWARE_INFO = (
  "\n".join(
    [
      "12345678",
      "1",
      "0",
      "1200",
      "00DEADBEEF42",
      "168034304",
      "917504",
      "131072",
      "45356",
      "134217728",
      "134217728",
      "131072",
      "45356",
      "2147483648",
      "2097152",
      "0",
      "0",
      "0",
      "134217728",
      "0",
      "0",
      "0",
      "0",
      "0",
      "0",
      "11111111",
      "8",
    ]
  )
  + "\n"
)
# `CtrlInfo`: each controller, and its firmware.
_CONTROLLER_INFO = (
  "1 1 3\n4\n"
  "BlockThermoCycler Ctrl\n0\n1\n0\n0\n"
  "HTCCntrl\n1.02.00\n1526   \n22775\n"
  "HTCCntrl\n1.02.00\n1526   \n22775\n"
  "CYG_BOOT\n1.00.00\n0517   \n00076579\n"
  "04513754\n L\n04513754001\n"
  "DC Motors Ctrl\n0\n2\n0\n0\n"
  "DC-SLAVE\n1.00.03\n0711   \n63108\n"
  "DC-SLAVE\n1.00.03\n0711   \n63108\n"
  "CYG_BOOT\n1.00.00\n0517   \n00076579\n"
  "04513754\n L\n04513754001\n"
  "DetectionControl Ctrl\n0\n4\n0\n0\n"
  "DETCTRL \n1.02.00\n1137   \n740\n"
  "DETCTRL \n1.02.00\n1137   \n740\n"
  "CYG_BOOT\n1.00.00\n0517   \n00071773\n"
  "04479785\nH \n04479785001\n"
  "RawdataReduction Ctrl\n0\n3\n0\n0\n"
  "DrDspApp\n1.04.02\n1322   \n-779133962\n"
  "DrDspApp\n1.04.02\n1322   \n-779133962\n"
  "AppLoade\n2.00.00\n0508   \n00071651\n"
  "04479807\nF \n04479807001\n"
)


def _clock() -> str:
  return datetime.datetime.now().strftime("%d.%m.%Y_%H:%M:%S")


def _int(text: str) -> int:
  try:
    return int(text.strip())
  except ValueError:
    return 0


class SimulatedLightCycler480:
  """One simulated instrument: its tray, plate, state, and the run it was last given.

  Attributes:
    seconds_per_second: how long a step's hold takes here, per second it holds; 0 runs at once.
    step_delay: how long each step takes besides its hold, in seconds.
    tray_open: whether the tray is out. It starts out, empty, as flo4's mock does.
    plate_present: whether a plate is on the tray.
    barcode: the plate's barcode; empty for one without.
    received: every message the host sent, with the index of the port it came on.
    runs_started: how many runs `StartRun` has started.
  """

  def __init__(self, seconds_per_second: float = 0.0, step_delay: float = 0.01) -> None:
    self.seconds_per_second = seconds_per_second
    self.step_delay = step_delay
    self.tray_open = True
    self.plate_present = False
    self.barcode = ""
    self.state = STATE_NOT_READY
    self.received: List[Tuple[int, Packet]] = []
    self.runs_started = 0
    self.ports: List[int] = []
    self._servers: List[asyncio.Server] = []
    self._writers: Dict[int, List[asyncio.StreamWriter]] = defaultdict(list)
    self._event_writers: List[asyncio.StreamWriter] = []
    self._event_seq = 100
    # The experiment defined last.
    self.guid = ""
    self.well_count = 384
    self.volume = 20
    self._holds: Dict[int, int] = {}
    self._steps: Dict[int, Dict[int, WireStep]] = {}
    # Its reads, by number, and those the host has acknowledged.
    self._results: Dict[int, bytes] = {}
    self._acknowledged: Set[int] = set()
    self._last_read = 0
    self._run: Optional["asyncio.Task[None]"] = None

  # -- serving ------------------------------------------------------------------------------------

  @property
  def started(self) -> bool:
    return bool(self._servers)

  async def start(self, host: str = "127.0.0.1") -> List[int]:
    """Listen on five ports of `host`, each the next free one; the ports, in the driver's order."""
    for index in range(5):

      async def serve(r: asyncio.StreamReader, w: asyncio.StreamWriter, index: int = index) -> None:
        await self._serve(index, r, w)

      server = await asyncio.start_server(serve, host, 0)
      self._servers.append(server)
      self.ports.append(server.sockets[0].getsockname()[1])
    return list(self.ports)

  async def stop(self) -> None:
    """Close every connection and stop listening."""
    if self._run is not None:
      self._run.cancel()
      await asyncio.gather(self._run, return_exceptions=True)
    for writers in self._writers.values():
      for writer in list(writers):
        writer.close()
    for server in self._servers:
      server.close()
      await server.wait_closed()
    self._servers, self.ports = [], []

  async def _serve(
    self, index: int, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
  ) -> None:
    self._writers[index].append(writer)
    try:
      while True:
        header = await reader.readexactly(HEADER_SIZE)
        message_type, length = decode_header(header)
        payload = await reader.readexactly(length) if length else b""
        packet = Packet(message_type, payload)
        self.received.append((index, packet))
        if index == EVENTS_PORT and message_type == VERSION_QUERY:
          self._event_writers.append(writer)
          continue
        for answer in self._answer(index, packet):
          writer.write(answer.encode())
        await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionError):
      pass
    finally:
      self._writers[index].remove(writer)
      if writer in self._event_writers:
        self._event_writers.remove(writer)
      writer.close()

  def _emit_event(self, code: int, *data: str) -> None:
    """Send an event, as the instrument does unasked, on the events port."""
    self._event_seq += 1
    payload = "\n".join([str(self._event_seq), _clock(), str(code), *data]) + "\n\n"
    for writer in self._event_writers:
      writer.write(Packet(EVENT, payload.encode()).encode())

  # -- the tray -----------------------------------------------------------------------------------

  def _update_state(self) -> None:
    if self.state == STATE_RUNNING:
      return
    state = STATE_IDLE if not self.tray_open and self.plate_present else STATE_NOT_READY
    if state != self.state:
      self.state = state
      self._emit_event(11, str(state))

  def set_tray(self, is_open: bool) -> None:
    """Move the tray out or in."""
    self.tray_open = is_open
    self._emit_event(301, "5" if is_open else "4")
    self._update_state()

  def set_plate(self, present: bool, barcode: str = "") -> None:
    """Put a plate on the tray, with a barcode or none, or take it off."""
    self.plate_present = present
    self.barcode = barcode if present else ""
    if present:
      self._emit_event(303, "1 ")
    self._update_state()

  def _tray_code(self) -> str:
    if self.tray_open:
      return "5"
    return "4" if self.plate_present else "3"

  # -- answers ------------------------------------------------------------------------------------

  @staticmethod
  def _ok(message_type: int, seq: str, *extra: str) -> Packet:
    return Packet(message_type, ("\n".join(["0", seq, "0", *extra]) + "\n").encode())

  def _not_there(self) -> Packet:
    payload = f"99\n1\n0\n0\n{self.guid}\n0\n0\n0\n0\n0\n0\n0\n0\n0\n"
    return Packet(GET_RESULT_DATA, payload.encode())

  def _answer(self, index: int, packet: Packet) -> List[Packet]:
    """What the instrument sends back for `packet`."""
    kind = packet.type
    fields = packet.fields()
    seq = fields[0] if fields else "0"
    if kind == KEEPALIVE:
      return [Packet(KEEPALIVE, b"Connection")]
    if index == KEEPALIVE_PORT:
      if kind == VERSION_QUERY:
        return [Packet(kind, f"{CONTROLLER}\n{FIRMWARE_VERSION}\n{_clock()}".encode())]
      if kind == EVENT:
        return [Packet(kind, b"3\n1\n1\n1\n1\n1\n")]
      if kind == STATUS_4:
        return [Packet(kind, b"1")]
      if kind == SYS_INFO:
        return [Packet(kind, _HARDWARE_INFO.encode())]
      if kind == CTRL_INFO:
        return [Packet(kind, _CONTROLLER_INFO.encode())]
    if kind in (EVENT, TRACE, SYS_INFO, CTRL_INFO):
      return []  # the host acknowledging what was sent it
    if kind == SUBSYS_QUERY:
      payload = f"{self.state}\n3\n3\n3\n3\n3\n3\n{self._tray_code()}\n3\n3\n7589\n9467\n4\n1\n"
      return [Packet(kind, payload.encode())]
    if kind == QUERY_LOAD_STATE:
      if not self.tray_open and self.plate_present and self.barcode:
        return [Packet(kind, f"0\nCode 128\n{self.barcode}\n".encode())]
      return [Packet(kind, b"0\n")]
    if kind == SET_PARAMETER:
      return [Packet(kind, b"0\n")]
    if kind == STATUS_QUERY:
      return [Packet(kind, _STATUS.encode())]
    if kind == SUBSYS_STATUS:
      return [Packet(kind, f"{self.state}\n".encode())]
    if kind == CREATE_EXPERIMENT:
      if len(fields) > 3:
        self.guid = fields[1]
        self.well_count = _int(fields[2])
        self.volume = _int(fields[3])
      self._holds, self._steps = {}, {}
      return [self._ok(kind, seq)]
    if kind == THERMAL_PARAMS:
      if len(fields) > 8:
        self._holds[_int(fields[1])] = _int(fields[8])
      return [self._ok(kind, seq)]
    if kind == PROTOCOL_STEP:
      if len(fields) > 10:
        program, step = _int(fields[1]), _int(fields[2])
        self._steps.setdefault(program, {})[step] = WireStep(
          temperature=_int(fields[3]) / 100,
          hold_seconds=self._holds.get(program, 100) / 100,
          filter_code=_int(fields[10]),
          exposure=_int(fields[5]),
          ramp_rate=_int(fields[6]) / 100,
        )
      return [self._ok(kind, seq)]
    if kind == START_RUN:
      self._start_run()
      return [self._ok(kind, seq, "1")]
    if kind == GET_RESULT_DATA:
      number = _int(seq)
      result = self._results.get(number)
      if result is None or number in self._acknowledged:
        return [self._not_there()]
      self._last_read = number
      return [Packet(kind, result)]
    if kind == QUERY_RESULT_INFO:
      return [Packet(kind, f"0\n1\n{self._last_read}\n{self.well_count}\n".encode())]
    if kind == ACK_RESULT:
      self._acknowledged.add(_int(seq))
      return [Packet(kind, b"0\n")]
    return [self._ok(kind, seq)]

  # -- runs ---------------------------------------------------------------------------------------

  def _start_run(self) -> None:
    self.runs_started += 1
    self._results, self._acknowledged, self._last_read = {}, set(), 0
    self.state = STATE_RUNNING
    self._emit_event(11, str(STATE_RUNNING))
    programs = [
      [steps[number] for number in sorted(steps)]
      for _, steps in sorted(self._steps.items(), key=lambda item: item[0])
    ]
    self._run = asyncio.get_running_loop().create_task(self._execute(programs))

  async def _execute(self, programs: List[List[WireStep]]) -> None:
    loop = asyncio.get_running_loop()
    started = loop.time()
    number = 0
    for program_index, steps in enumerate(programs):
      for step_index, step in enumerate(steps):
        await asyncio.sleep(self.step_delay + self.seconds_per_second * step.hold_seconds)
        if not step.acquires:
          continue
        number += 1
        elapsed = loop.time() - started
        self._results[number] = self._read(number, program_index + 1, step_index + 1, step, elapsed)
        self._emit_event(201, f"{self.well_count} {program_index + 1} {step_index + 1} 1")
    self.state = STATE_IDLE if not self.tray_open and self.plate_present else STATE_NOT_READY
    self._emit_event(11, str(self.state))
    self._emit_event(101, "0")

  def _read(self, number: int, program: int, step: int, wire: WireStep, elapsed: float) -> bytes:
    """A read's `GetResultData` payload: background values, with a hot pixel every 48 wells."""
    rng = random.Random(number)
    values = [25 + rng.randrange(46) for _ in range(self.well_count)]
    for well in range(0, self.well_count, 48):
      values[well] = 80 + rng.randrange(121)
    time_cs = 10000 + round(elapsed * 100)
    temperature_cd = round(wire.temperature * 100) + rng.randrange(21) - 10
    header = (
      f"0\n1\n2\n1\n{self.guid}\n{program}\n1\n{step}\n{time_cs}\n{temperature_cd}\n"
      f"389949\n12765\n0\n{self.well_count}\n"
    )
    return (header + "\n".join(map(str, values)) + "\n").encode()


class SimulatedTrayButton:
  """The tray's button on a simulated instrument, pressed as flo4's mock Fingerbot presses it:
  closing the tray loads a plate and opening it takes the plate off, as when a robot hands plates
  in and out with the tray open.

  Attributes:
    presses: how many times it was pressed.
  """

  def __init__(self, instrument: SimulatedLightCycler480, plate_on_close: bool = True) -> None:
    self.instrument = instrument
    self.plate_on_close = plate_on_close
    self.presses = 0

  async def press(self) -> None:
    self.presses += 1
    now_open = not self.instrument.tray_open
    self.instrument.set_tray(now_open)
    if self.plate_on_close:
      self.instrument.set_plate(not now_open)


class LightCycler480Simulator(LightCycler480Driver):
  """The driver, connected over loopback sockets to a `SimulatedLightCycler480`.

  Polls quicker than against a device, since the simulated instrument answers at once.
  """

  _warn_untested = False
  result_poll_interval = 0.01
  idle_poll_interval = 0.01

  def __init__(self, instrument: Optional[SimulatedLightCycler480] = None) -> None:
    """
    Args:
      instrument: the instrument to connect to; one made, started and stopped with the driver when
        not given.
    """
    super().__init__(host="127.0.0.1", port=0)
    self.instrument = instrument or SimulatedLightCycler480()
    self._owns_instrument = instrument is None

  async def setup(self) -> None:
    if not self.instrument.started:
      await self.instrument.start(self.host)
    self.ports = list(self.instrument.ports)
    await super().setup()

  async def stop(self) -> None:
    await super().stop()
    if self._owns_instrument and self.instrument.started:
      await self.instrument.stop()
