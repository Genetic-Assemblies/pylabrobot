"""The wire format and the driver, checked against a capture from a LightCycler 480 II and against
the simulated instrument. Ported from flo4's `lc480/lc480_test.go`."""

import asyncio
import os
import re
import unittest
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

from pylabrobot.legacy.thermocycling.standard import Protocol, Stage, Step
from pylabrobot.roche.lightcycler import (
  CommandFailedError,
  LightCycler480,
  LightCycler480Simulator,
  LightCyclerStep,
  SimulatedLightCycler480,
)
from pylabrobot.roche.lightcycler.device import plan_experiment
from pylabrobot.roche.lightcycler.wire import (
  ACK_RESULT,
  COMMANDS_PORT,
  CREATE_EXPERIMENT,
  DEFINE_PROGRAM,
  EVENT,
  EVENTS_PORT,
  GET_RESULT_DATA,
  KEEPALIVE,
  PORT_OFFSETS,
  PROTOCOL_STEP,
  RESULTS_PORT,
  START_RUN,
  STATUS_PORT,
  STATUS_QUERY,
  SUBSYS_STATUS,
  THERMAL_PARAMS,
  VERSION_QUERY,
  ExperimentConfig,
  Packet,
  WireStep,
  build_commands,
  decode_packet,
  parse_result_data,
  port_for_message,
  simple_read,
)

CAPTURE = os.path.join(os.path.dirname(__file__), "testdata", "capture_20260409_110929.txt")
BASE_PORT = 5100


@dataclass
class Entry:
  port: int
  direction: str
  data: bytes

  @property
  def packet(self) -> Packet:
    return decode_packet(self.data)


@dataclass
class CapturedExperiment:
  name: str
  guid: str
  acquisitions: int
  entries: List[Entry] = field(default_factory=list)

  def sent_on(self, port: int) -> List[bytes]:
    return [e.data for e in self.entries if e.port == port and e.direction == "TX"]


@dataclass
class Capture:
  host: str = ""
  handshake: List[Entry] = field(default_factory=list)
  experiments: List[CapturedExperiment] = field(default_factory=list)

  def experiment(self, name: str) -> CapturedExperiment:
    return next(e for e in self.experiments if e.name == name)


def load_capture() -> Capture:
  capture = Capture()
  current: Optional[CapturedExperiment] = None
  with open(CAPTURE) as f:
    for line in f:
      line = line.strip()
      if line.startswith("# HOST "):
        capture.host = line[len("# HOST ") :]
      elif line.startswith("# EXPERIMENT "):
        parts = line.split()
        values = dict(p.split("=", 1) for p in parts[3:])
        current = CapturedExperiment(parts[2], values["guid"], int(values["acquisitions"]))
        capture.experiments.append(current)
      elif line and not line.startswith("#"):
        _, port, direction, data = line.split()
        entry = Entry(int(port), direction, bytes.fromhex(data))
        (current.entries if current else capture.handshake).append(entry)
  return capture


def one_step(temperature: float, acquire: bool) -> LightCyclerStep:
  return LightCyclerStep(temperature=[temperature], hold_seconds=1.0, acquire=acquire)


# The experiments of the capture, as protocols.
PROTOCOLS: Dict[str, Protocol] = {
  "single_read": Protocol([Stage([one_step(37, True)], repeats=1)]),
  "triple_read": Protocol([Stage([one_step(37, True)] * 3, repeats=1)]),
  "multi_stage": Protocol([Stage([one_step(37, True)], 1), Stage([one_step(50, True)], 1)]),
  "multi_stage_multi_step": Protocol(
    [Stage([one_step(50, False), one_step(37, True)], 1)] * 2,
  ),
  "thermal_only": Protocol([Stage([Step(temperature=[50], hold_seconds=1.0)], repeats=1)]),
}


class WireTests(unittest.TestCase):
  capture: Capture

  @classmethod
  def setUpClass(cls):
    cls.capture = load_capture()

  def test_a_packet_round_trips(self):
    packet = Packet(KEEPALIVE, b"hi")
    self.assertEqual(packet.encode(), bytes([0, 0, 0, 2, 0x68, 0x69]))
    self.assertEqual(decode_packet(packet.encode()), packet)

  def test_the_handshake_is_as_captured(self):
    hi, version, connection, answer = (e.packet for e in self.capture.handshake[:4])
    self.assertEqual((hi.type, hi.payload), (KEEPALIVE, b"hi"))
    self.assertEqual((version.type, version.payload), (VERSION_QUERY, b"?"))
    self.assertEqual((connection.type, connection.payload), (KEEPALIVE, b"Connection"))
    self.assertEqual(answer.fields()[:2], ["8/HTC", "1.8.6.1501"])

  def test_events_are_registered_for_with_the_clock_and_4(self):
    registration = next(e for e in self.capture.handshake if e.port == BASE_PORT + 1).packet
    self.assertEqual(registration.type, VERSION_QUERY)
    self.assertRegex(registration.payload.decode(), r"^\d\d\.\d\d\.\d\d_\d\d\.\d\d\.\d\d_4$")

  def test_every_captured_packet_decodes_and_encodes_again(self):
    entries = self.capture.handshake + [e for x in self.capture.experiments for e in x.entries]
    for entry in entries:
      self.assertEqual(entry.packet.encode(), entry.data)

  def test_the_capture_holds_five_experiments(self):
    self.assertEqual(self.capture.host, "192.168.95.41")
    self.assertEqual(
      [(e.name, e.acquisitions) for e in self.capture.experiments],
      [
        ("single_read", 1),
        ("triple_read", 3),
        ("multi_stage", 2),
        ("multi_stage_multi_step", 2),
        ("thermal_only", 0),
      ],
    )

  def test_messages_go_on_their_ports(self):
    for message, port in [
      (KEEPALIVE, 0),
      (CREATE_EXPERIMENT, COMMANDS_PORT),
      (DEFINE_PROGRAM, COMMANDS_PORT),
      (THERMAL_PARAMS, COMMANDS_PORT),
      (PROTOCOL_STEP, COMMANDS_PORT),
      (START_RUN, COMMANDS_PORT),
      (GET_RESULT_DATA, RESULTS_PORT),
      (ACK_RESULT, RESULTS_PORT),
      (SUBSYS_STATUS, STATUS_PORT),
      (STATUS_QUERY, STATUS_PORT),
      (EVENT, EVENTS_PORT),
    ]:
      self.assertEqual(port_for_message(message), port)
    # Every captured message was sent on the port its type goes on.
    for experiment in self.capture.experiments:
      for entry in experiment.entries:
        port = BASE_PORT + PORT_OFFSETS[port_for_message(entry.packet.type)]
        self.assertEqual(entry.port, port, entry.packet.name)

  def test_a_protocol_goes_on_the_wire_as_captured(self):
    for name, protocol in PROTOCOLS.items():
      with self.subTest(name):
        experiment = self.capture.experiment(name)
        config, slots = plan_experiment(protocol, experiment.guid, 384, 20)
        sent = [p.encode() for p in build_commands(config)]
        self.assertEqual(sent, experiment.sent_on(BASE_PORT + 2))
        self.assertEqual(len(slots), experiment.acquisitions)

  def test_simple_read_is_the_captured_triple_read(self):
    experiment = self.capture.experiment("triple_read")
    sent = [p.encode() for p in build_commands(simple_read(37.0, 1.0, 3, experiment.guid))]
    self.assertEqual(sent, experiment.sent_on(BASE_PORT + 2))

  def test_reads_parse_as_captured(self):
    experiment = self.capture.experiment("multi_stage")
    reads = []
    for entry in experiment.entries:
      packet = entry.packet
      if entry.direction == "RX" and packet.type == GET_RESULT_DATA:
        result = parse_result_data(packet.fields())
        if result.status == 0 and result.guid == experiment.guid:
          reads.append(result)
    self.assertEqual(len(reads), 2)
    self.assertAlmostEqual(reads[0].temperature, 37.0, delta=1)
    self.assertAlmostEqual(reads[1].temperature, 50.0, delta=1)
    self.assertEqual([r.program for r in reads], [1, 2])
    self.assertEqual([r.well_count for r in reads], [384, 384])
    self.assertEqual([len(r.values) for r in reads], [384, 384])
    self.assertEqual(reads[0].values[:3], (505, 51, 75))

  def test_a_read_names_the_step_it_was_taken_at(self):
    experiment = self.capture.experiment("multi_stage_multi_step")
    reads = [
      parse_result_data(e.packet.fields())
      for e in experiment.entries
      if e.direction == "RX" and e.packet.type == GET_RESULT_DATA
    ]
    taken = [(r.program, r.step) for r in reads if r.status == 0 and r.guid == experiment.guid]
    self.assertEqual(taken, [(1, 2), (2, 2)])

  def test_a_short_read_is_refused(self):
    with self.assertRaises(ValueError):
      parse_result_data(["0", "1"])


class ReplayedLightCycler480(SimulatedLightCycler480):
  """A simulated instrument that answers each request with what the device answered it in the
  capture, in order, the last answer again once the others are used; anything the capture holds
  no answer for, it answers as the simulator does."""

  def __init__(self, experiment: CapturedExperiment) -> None:
    super().__init__()
    self.tray_open, self.plate_present, self.state = False, True, 10
    self.answers: Dict[Tuple[int, bytes], Deque[Packet]] = defaultdict(deque)
    asked: Dict[int, Deque[Packet]] = defaultdict(deque)
    for entry in experiment.entries:
      packet = entry.packet
      if entry.direction == "TX":
        asked[entry.port].append(packet)
      elif asked[entry.port]:
        question = asked[entry.port].popleft()
        self.answers[(question.type, question.payload)].append(packet)

  def _answer(self, index: int, packet: Packet) -> List[Packet]:
    answers = self.answers.get((packet.type, packet.payload))
    if not answers:
      return super()._answer(index, packet)
    return [answers.popleft() if len(answers) > 1 else answers[0]]


class ReplayTests(unittest.IsolatedAsyncioTestCase):
  """The device runs each captured experiment against the answers the instrument gave."""

  async def test_each_captured_experiment_runs_as_it_did(self):
    capture = load_capture()
    for name, protocol in PROTOCOLS.items():
      with self.subTest(name):
        experiment = capture.experiment(name)
        instrument = ReplayedLightCycler480(experiment)
        await instrument.start()
        lc = LightCycler480(driver=LightCycler480Simulator(instrument))
        try:
          await lc.setup()
          done = await lc.run_experiment(protocol, experiment_id=experiment.guid)
        finally:
          await lc.stop()
          await instrument.stop()
        sent = [p.encode() for i, p in instrument.received if i == COMMANDS_PORT]
        self.assertEqual(sent, experiment.sent_on(BASE_PORT + 2))
        self.assertEqual(done.status, "complete")
        self.assertEqual(len(done.acquisitions), experiment.acquisitions)
        for read in done.acquisitions:
          self.assertEqual(len(read.values), 384)
        if name == "multi_stage":
          self.assertEqual([round(a.temperature) for a in done.acquisitions], [37, 50])
          self.assertEqual([a.stage_index for a in done.acquisitions], [0, 1])


class SimulatedDriverTests(unittest.IsolatedAsyncioTestCase):
  """The driver's commands against the simulated instrument, as flo4's mock tests run them."""

  async def asyncSetUp(self):
    self.instrument = SimulatedLightCycler480()
    self.instrument.set_plate(True)
    self.instrument.set_tray(False)
    self.driver = LightCycler480Simulator(self.instrument)
    await self.driver.setup()

  async def asyncTearDown(self):
    await self.driver.stop()
    await self.instrument.stop()

  async def run_config(self, config: ExperimentConfig):
    self.assertEqual(await self.driver.drain_stale_results(), 0)
    await self.driver.wait_idle(timeout=5)
    await self.driver.prepare_run()
    await self.driver.send_experiment(config)
    results = []
    for number in range(1, config.total_acquisitions + 1):
      results.append(await self.driver.wait_for_result(number, config.guid, timeout=5))
      await self.driver.acknowledge_result(number)
    await self.driver.wait_idle(timeout=5)
    await self.driver.finish_run()
    return results

  async def test_the_handshake_reads_the_firmware(self):
    assert self.driver.info is not None
    self.assertEqual(self.driver.info.firmware_version, "1.8.6.1501")
    self.assertEqual(self.driver.info.controller, "8/HTC")
    self.assertEqual(self.driver.info.hardware_info[4], "00DEADBEEF42")

  async def test_a_single_read(self):
    step = WireStep(temperature=37.0, hold_seconds=1.0, filter_code=1)
    results = await self.run_config(ExperimentConfig("MOCK0001", 384, 20, ((step,),)))
    self.assertEqual(len(results), 1)
    self.assertEqual((results[0].well_count, results[0].guid), (384, "MOCK0001"))
    self.assertAlmostEqual(results[0].temperature, 37.0, delta=0.11)

  async def test_a_triple_read(self):
    results = await self.run_config(simple_read(37.0, 1.0, 3, "MOCK0002"))
    self.assertEqual([r.guid for r in results], ["MOCK0002"] * 3)
    self.assertEqual([r.step for r in results], [1, 2, 3])

  async def test_a_multi_stage_read(self):
    stages = tuple((WireStep(t, 1.0, filter_code=1),) for t in (37.0, 50.0))
    results = await self.run_config(ExperimentConfig("MOCK0003", 384, 20, stages))
    self.assertEqual([round(r.temperature) for r in results], [37, 50])
    self.assertEqual([r.program for r in results], [1, 2])

  async def test_a_thermal_only_run_reads_nothing(self):
    config = ExperimentConfig("MOCK0004", 384, 20, ((WireStep(50.0, 1.0),),))
    self.assertEqual(await self.run_config(config), [])
    self.assertEqual(self.instrument.runs_started, 1)

  async def test_a_96_well_run_reads_96_wells(self):
    results = await self.run_config(simple_read(37.0, 1.0, 1, "MOCK0005", well_count=96))
    self.assertEqual(len(results[0].values), 96)

  async def test_a_refused_command_raises_and_the_rest_are_not_sent(self):
    refuse = self.instrument._answer

    def refusing(index: int, packet: Packet) -> List[Packet]:
      if packet.type == THERMAL_PARAMS:
        return [Packet(THERMAL_PARAMS, b"3\n3\n0\n")]
      return refuse(index, packet)

    self.instrument._answer = refusing  # type: ignore[method-assign]
    with self.assertRaises(CommandFailedError) as raised:
      await self.driver.send_experiment(simple_read(37.0, 1.0, 1, "MOCK0006"))
    self.assertEqual(raised.exception.command, "ThermalParams")
    self.assertEqual(self.instrument.runs_started, 0)

  async def test_the_tray_state_is_read(self):
    self.instrument.set_plate(True, barcode="PLATE-7")
    state = await self.driver.request_tray_state()
    self.assertEqual((state.open, state.plate_loaded, state.barcode), (False, True, "PLATE-7"))
    self.instrument.set_tray(True)
    state = await self.driver.request_tray_state()
    self.assertEqual((state.open, state.plate_loaded), (True, False))
    self.instrument.set_tray(False)
    self.instrument.set_plate(False)
    state = await self.driver.request_tray_state()
    self.assertEqual((state.open, state.plate_loaded), (False, False))
    self.assertEqual(await self.driver.request_instrument_state(), 6)

  async def test_events_are_acknowledged_and_kept(self):
    self.instrument.set_tray(True)
    for _ in range(100):
      if len(self.driver.logs()) >= 2:
        break
      await asyncio.sleep(0.01)
    entries = self.driver.logs()
    self.assertEqual(
      [(e.kind, e.code, e.data[0]) for e in entries[:2]], [("event", 301, "5"), ("event", 11, "6")]
    )
    acks = [p for i, p in self.instrument.received if i == EVENTS_PORT and p.type == EVENT]
    self.assertTrue(acks)
    self.assertTrue(re.match(r"^\d+$", acks[0].payload.decode()))
    self.assertEqual(self.driver.logs(since_id=entries[-1].id), [])

  async def test_a_closed_connection_fails_commands_with_connection_error(self):
    await self.instrument.stop()
    with self.assertRaises(ConnectionError):
      for _ in range(100):
        await self.driver.request_instrument_state()
        await asyncio.sleep(0.01)
    self.assertFalse(self.driver.connected)


if __name__ == "__main__":
  unittest.main()
