"""The LightCycler 480 II's wire format, and the commands that define and start an experiment.

The instrument listens on five TCP ports, each carrying its own messages. Every message, either
way, is a 2-byte big-endian message type, a 2-byte big-endian payload length, and an ASCII payload
of fields separated by newlines. Reverse-engineered from captures of the Roche software and of
flo4's Go driver (koeng101/flo4, `robots/roche/lightcycler/lc480`), which this is a port of.
"""

import struct
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

# -- message types ---------------------------------------------------------------------------------

KEEPALIVE = 0x0000
VERSION_QUERY = 0x0001
STATUS_4 = 0x0004
SYS_INFO = 0x000C
CTRL_INFO = 0x000D
EVENT = 0x000E
TRACE = 0x0010
LOG_ENTRY_2 = 0x0012
LOG_ENTRY = 0x0013
SUBSYS_STATUS = 0x002F
SUBSYS_QUERY = 0x0030
STATUS_QUERY = 0x0033
CALIBRATION = 0x0046
START_RUN = 0x00C9
CREATE_EXPERIMENT = 0x012D
FINALIZE_EXPERIMENT = 0x012E
DEFINE_PROGRAM = 0x012F
FINALIZE_PROGRAM = 0x0130
THERMAL_PARAMS = 0x0131
PROTOCOL_STEP = 0x0132
GET_RESULT_DATA = 0x044D
ACK_RESULT = 0x044E
QUERY_RESULT_INFO = 0x044F
QUERY_LOAD_STATE = 0x047F
SET_PARAMETER = 0x04B0

MESSAGE_NAMES: Dict[int, str] = {
  KEEPALIVE: "Keepalive",
  VERSION_QUERY: "VersionQuery",
  STATUS_4: "Status4",
  SYS_INFO: "SysInfo",
  CTRL_INFO: "CtrlInfo",
  EVENT: "Event",
  TRACE: "Trace",
  LOG_ENTRY_2: "LogEntry2",
  LOG_ENTRY: "LogEntry",
  SUBSYS_STATUS: "SubsysStatus",
  SUBSYS_QUERY: "SubsysQuery",
  STATUS_QUERY: "StatusQuery",
  CALIBRATION: "Calibration",
  START_RUN: "StartRun",
  CREATE_EXPERIMENT: "CreateExperiment",
  FINALIZE_EXPERIMENT: "FinalizeExperiment",
  DEFINE_PROGRAM: "DefineProgram",
  FINALIZE_PROGRAM: "FinalizeProgram",
  THERMAL_PARAMS: "ThermalParams",
  PROTOCOL_STEP: "ProtocolStep",
  GET_RESULT_DATA: "GetResultData",
  ACK_RESULT: "AckResult",
  QUERY_RESULT_INFO: "QueryResultInfo",
  QUERY_LOAD_STATE: "QueryLoadState",
  SET_PARAMETER: "SetParameter",
}

# -- ports -----------------------------------------------------------------------------------------

# The connections, by index: each is the base port plus its offset. Port base + 3 is not used.
KEEPALIVE_PORT, EVENTS_PORT, COMMANDS_PORT, RESULTS_PORT, STATUS_PORT = range(5)
PORT_OFFSETS: Tuple[int, ...] = (0, 1, 2, 4, 5)
PORT_NAMES: Tuple[str, ...] = ("keepalive", "events", "commands", "results", "status")

_PORT_FOR_MESSAGE: Dict[int, int] = {
  KEEPALIVE: KEEPALIVE_PORT,
  VERSION_QUERY: KEEPALIVE_PORT,
  STATUS_4: KEEPALIVE_PORT,
  SYS_INFO: KEEPALIVE_PORT,
  CTRL_INFO: KEEPALIVE_PORT,
  EVENT: EVENTS_PORT,
  TRACE: EVENTS_PORT,
  START_RUN: COMMANDS_PORT,
  CREATE_EXPERIMENT: COMMANDS_PORT,
  FINALIZE_EXPERIMENT: COMMANDS_PORT,
  DEFINE_PROGRAM: COMMANDS_PORT,
  FINALIZE_PROGRAM: COMMANDS_PORT,
  THERMAL_PARAMS: COMMANDS_PORT,
  PROTOCOL_STEP: COMMANDS_PORT,
  GET_RESULT_DATA: RESULTS_PORT,
  ACK_RESULT: RESULTS_PORT,
  QUERY_RESULT_INFO: RESULTS_PORT,
  QUERY_LOAD_STATE: RESULTS_PORT,
  SET_PARAMETER: RESULTS_PORT,
  SUBSYS_STATUS: STATUS_PORT,
  SUBSYS_QUERY: STATUS_PORT,
  STATUS_QUERY: STATUS_PORT,
  CALIBRATION: STATUS_PORT,
}


def port_for_message(message_type: int) -> int:
  """The connection a message type is sent on; the commands port for one not known."""
  return _PORT_FOR_MESSAGE.get(message_type, COMMANDS_PORT)


# -- packets ---------------------------------------------------------------------------------------

HEADER_SIZE = 4
_HEADER = struct.Struct(">HH")


def message_name(message_type: int) -> str:
  return MESSAGE_NAMES.get(message_type, f"0x{message_type:04X}")


@dataclass(frozen=True)
class Packet:
  """One message: its type and its ASCII payload."""

  type: int
  payload: bytes = b""

  def encode(self) -> bytes:
    if len(self.payload) > 0xFFFF:
      raise ValueError(f"a payload holds at most 65535 bytes, not {len(self.payload)}")
    return _HEADER.pack(self.type, len(self.payload)) + self.payload

  def fields(self) -> List[str]:
    """The payload's fields, split on newlines after trailing newlines are trimmed."""
    return self.payload.decode("ascii", errors="replace").rstrip("\n").split("\n")

  @property
  def name(self) -> str:
    return message_name(self.type)


def decode_header(header: bytes) -> Tuple[int, int]:
  """A header's message type and payload length."""
  message_type, length = _HEADER.unpack(header)
  return message_type, length


def decode_packet(data: bytes) -> Packet:
  """The one packet `data` holds whole."""
  message_type, length = decode_header(data[:HEADER_SIZE])
  payload = data[HEADER_SIZE : HEADER_SIZE + length]
  if len(payload) != length:
    raise ValueError(f"packet says {length} payload bytes, has {len(payload)}")
  return Packet(message_type, payload)


# -- results ---------------------------------------------------------------------------------------


def _int(text: str) -> int:
  try:
    return int(text.strip())
  except ValueError:
    return 0


@dataclass(frozen=True)
class ResultData:
  """One fluorescence read, as `GetResultData` answers it.

  Attributes:
    status: 0 when the read is there; 99 when it is not (yet).
    guid: the experiment it was read in.
    program: the program it was read in, from 1.
    cycle: unknown; 1 in every capture, none of which repeated a program.
    step: the step of the program it was read at, from 1.
    time_centiseconds: since the run started.
    temperature_centidegrees: the block's temperature as it was read.
    ref_channel: the reference channel's value; the trace log's `RefChannelValue`.
    values: one raw fluorescence value per well, in the instrument's order.
  """

  status: int
  format_version: int
  data_type: int
  block_id: int
  guid: str
  program: int
  cycle: int
  step: int
  time_centiseconds: int
  temperature_centidegrees: int
  exposure: int
  ref_channel: int
  reserved: int
  well_count: int
  values: Tuple[int, ...]

  @property
  def temperature(self) -> float:
    """In Celsius."""
    return self.temperature_centidegrees / 100.0

  @property
  def time(self) -> float:
    """In seconds since the run started."""
    return self.time_centiseconds / 100.0


def parse_result_data(fields: Sequence[str]) -> ResultData:
  """A `GetResultData` answer.

  Raises:
    ValueError: It has fewer than the 14 header fields.
  """
  if len(fields) < 14:
    raise ValueError(f"result data needs at least 14 fields, got {len(fields)}")
  well_count = _int(fields[13])
  values = tuple(_int(v) for v in fields[14 : 14 + well_count])
  return ResultData(
    status=_int(fields[0]),
    format_version=_int(fields[1]),
    data_type=_int(fields[2]),
    block_id=_int(fields[3]),
    guid=fields[4],
    program=_int(fields[5]),
    cycle=_int(fields[6]),
    step=_int(fields[7]),
    time_centiseconds=_int(fields[8]),
    temperature_centidegrees=_int(fields[9]),
    exposure=_int(fields[10]),
    ref_channel=_int(fields[11]),
    reserved=_int(fields[12]),
    well_count=well_count,
    values=values + (0,) * (well_count - len(values)),
  )


# -- experiments -----------------------------------------------------------------------------------

# What a step is read with where none is named: the exposure and ramp of every capture.
DEFAULT_EXPOSURE = 4800
DEFAULT_RAMP_RATE = 5.0


@dataclass(frozen=True)
class WireStep:
  """One step of a program, as it goes on the wire.

  Attributes:
    temperature: in Celsius.
    hold_seconds: how long to hold it. One hold goes on the wire per program: the first step's.
    filter_code: 0 for no read; 1 to 4 a filter set to read with (1 SYBR Green / FAM).
    exposure: in the instrument's units.
    ramp_rate: in Celsius per second.
  """

  temperature: float
  hold_seconds: float
  filter_code: int = 0
  exposure: int = DEFAULT_EXPOSURE
  ramp_rate: float = DEFAULT_RAMP_RATE

  @property
  def acquires(self) -> bool:
    return self.filter_code != 0


@dataclass(frozen=True)
class ExperimentConfig:
  """A whole experiment as it goes on the wire: programs run one after the other.

  Attributes:
    guid: 32 hex digits naming it; each read carries it.
    well_count: 96 or 384.
    volume: the reaction volume, in uL.
    programs: each a sequence of steps.
  """

  guid: str
  well_count: int
  volume: int
  programs: Tuple[Tuple[WireStep, ...], ...]

  @property
  def total_acquisitions(self) -> int:
    return sum(1 for program in self.programs for step in program if step.acquires)


def build_commands(config: ExperimentConfig) -> List[Packet]:
  """The commands that define `config` and start it, each numbered in order from 1.

  `CreateExperiment`; then, per program, `DefineProgram`, `ThermalParams`, a `ProtocolStep` per step
  and `FinalizeProgram`; then `FinalizeExperiment` and `StartRun`.
  """
  commands: List[Packet] = []

  def add(message_type: int, payload: str) -> None:
    commands.append(Packet(message_type, payload.encode("ascii")))

  seq = 1
  add(
    CREATE_EXPERIMENT,
    f"{seq}\n{config.guid}\n{config.well_count}\n{config.volume}\n{len(config.programs)}\n",
  )
  seq += 1
  for program_index, steps in enumerate(config.programs):
    program = program_index + 1
    add(DEFINE_PROGRAM, f"{seq}\n{program}\n1\n0\n1\n1\n{len(steps)}\n")
    seq += 1
    hold = round(steps[0].hold_seconds * 100) if steps else 100
    add(THERMAL_PARAMS, f"{seq}\n{program}\n1\n0\n3000\n1\n2\n1\n{hold}\n")
    seq += 1
    for step_index, step in enumerate(steps):
      temperature = round(step.temperature * 100)
      ramp = round(step.ramp_rate * 100) if step.ramp_rate > 0 else round(DEFAULT_RAMP_RATE * 100)
      exposure = step.exposure or DEFAULT_EXPOSURE
      add(
        PROTOCOL_STEP,
        f"{seq}\n{program}\n{step_index + 1}\n{temperature}\n1\n{exposure}\n{ramp}\n0\n0\n0\n"
        f"{step.filter_code}\n",
      )
      seq += 1
    add(FINALIZE_PROGRAM, f"{seq}\n?")
    seq += 1
  add(FINALIZE_EXPERIMENT, f"{seq}\n?")
  seq += 1
  add(START_RUN, f"{seq}\n?")
  return commands


def simple_read(
  temperature: float, hold_seconds: float, reads: int, guid: str, well_count: int = 384
) -> ExperimentConfig:
  """`reads` SYBR Green reads at one temperature, in one program."""
  step = WireStep(temperature=temperature, hold_seconds=hold_seconds, filter_code=1)
  return ExperimentConfig(guid=guid, well_count=well_count, volume=20, programs=((step,) * reads,))
