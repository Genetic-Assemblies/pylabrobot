import asyncio
import unittest

from pylabrobot.legacy.thermocycling.standard import Protocol, Stage, Step
from pylabrobot.roche.lightcycler import (
  ExperimentFailedError,
  LightCycler480,
  LightCycler480Simulator,
  LightCyclerStep,
  SimulatedTrayButton,
)
from pylabrobot.roche.lightcycler.wire import CREATE_EXPERIMENT, START_RUN, THERMAL_PARAMS


def read_at(temperature: float, hold: float = 1.0) -> LightCyclerStep:
  return LightCyclerStep(temperature=[temperature], hold_seconds=hold, acquire=True)


def reads(*temperatures: float) -> Protocol:
  return Protocol([Stage([read_at(t) for t in temperatures], repeats=1)])


class LightCycler480Tests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.lc = LightCycler480(simulation=True)
    assert isinstance(self.lc.driver, LightCycler480Simulator)
    self.instrument = self.lc.driver.instrument
    assert isinstance(self.lc.tray_button, SimulatedTrayButton)
    self.button = self.lc.tray_button
    self.lc.tray_poll_interval = 0.01
    await self.lc.setup()

  async def asyncTearDown(self):
    await self.lc.stop()

  def sent(self, message_type: int):
    return [p for _, p in self.instrument.received if p.type == message_type]

  async def load_plate(self):
    await self.lc.open_tray()
    await self.lc.close_tray()

  async def test_setup_twice_keeps_the_connection(self):
    await self.lc.setup()
    status = await self.lc.request_status()
    self.assertEqual((status.state, status.firmware_version), (6, "1.8.6.1501"))
    self.assertIsNone(status.running_experiment)

  async def test_the_tray_is_pressed_only_when_it_is_not_where_asked(self):
    await self.lc.open_tray()
    self.assertEqual(self.button.presses, 0)
    await self.lc.close_tray()
    await self.lc.close_tray()
    self.assertEqual(self.button.presses, 1)
    tray = await self.lc.request_tray_state()
    self.assertEqual((tray.open, tray.plate_loaded), (False, True))
    await self.lc.open_tray()
    self.assertEqual(self.button.presses, 2)
    self.assertTrue((await self.lc.request_tray_state()).open)

  async def test_without_a_button_the_tray_is_not_moved(self):
    self.lc.tray_button = None
    await self.lc.open_tray()
    with self.assertRaisesRegex(RuntimeError, "no tray button"):
      await self.lc.close_tray()

  async def test_a_tray_that_does_not_move_times_out(self):
    class Stuck:
      async def press(self) -> None:
        pass

    self.lc.tray_button = Stuck()
    with self.assertRaisesRegex(TimeoutError, "not closed"):
      await self.lc.close_tray(timeout=0.05)

  async def test_an_experiment_needs_the_tray_closed_on_a_plate(self):
    with self.assertRaisesRegex(RuntimeError, "tray is open"):
      await self.lc.start_experiment(reads(37))
    self.instrument.set_tray(False)
    with self.assertRaisesRegex(RuntimeError, "no plate"):
      await self.lc.start_experiment(reads(37))
    self.assertEqual(self.sent(CREATE_EXPERIMENT), [])

  async def test_a_run_reads_each_acquiring_step(self):
    await self.load_plate()
    experiment = await self.lc.run_experiment(reads(37, 37, 37))
    self.assertEqual(experiment.status, "complete")
    self.assertEqual(len(experiment.acquisitions), 3)
    self.assertEqual([a.number for a in experiment.acquisitions], [1, 2, 3])
    self.assertEqual([a.step_index for a in experiment.acquisitions], [0, 1, 2])
    self.assertEqual({len(a.values) for a in experiment.acquisitions}, {384})
    self.assertIsNotNone(experiment.finished_at)

  async def test_stages_and_their_repeats_are_programs_of_their_own(self):
    await self.load_plate()
    protocol = Protocol(
      [
        Stage([Step(temperature=[95], hold_seconds=2.0)], repeats=1),
        Stage([LightCyclerStep([95], 1.0), read_at(60, 1.0)], repeats=3),
      ]
    )
    experiment = await self.lc.run_experiment(protocol, well_count=96, volume=10)
    create = self.sent(CREATE_EXPERIMENT)[-1].fields()
    self.assertEqual(create[2:5], ["96", "10", "4"])
    self.assertEqual(
      [p.fields()[-1] for p in self.sent(THERMAL_PARAMS)], ["200", "100", "100", "100"]
    )
    places = [(a.stage_index, a.cycle, a.step_index) for a in experiment.acquisitions]
    self.assertEqual(places, [(1, 0, 1), (1, 1, 1), (1, 2, 1)])
    self.assertEqual({round(a.temperature) for a in experiment.acquisitions}, {60})
    self.assertEqual({len(a.values) for a in experiment.acquisitions}, {96})
    self.assertIsInstance(experiment.protocol.stages[0].steps[0], LightCyclerStep)

  async def test_a_run_that_reads_nothing_finishes(self):
    await self.load_plate()
    protocol = Protocol([Stage([Step(temperature=[50], hold_seconds=1.0)], repeats=1)])
    experiment = await self.lc.run_experiment(protocol)
    self.assertEqual((experiment.status, experiment.acquisitions), ("complete", ()))

  async def test_what_the_lightcycler_cannot_run_is_refused_before_anything_is_sent(self):
    await self.load_plate()
    for protocol, message in [
      (Protocol([]), "no stages"),
      (Protocol([Stage([read_at(37, 1.0), read_at(37, 2.0)], 1)]), "one time"),
      (Protocol([Stage([LightCyclerStep([60, 65], 1.0)], 1)]), "one temperature"),
      (Protocol([Stage([read_at(37)], 0)]), "repeats"),
      (Protocol([Stage([LightCyclerStep([37], 1.0, filter_set="fam")], 1)]), "filter_set"),  # type: ignore[arg-type]
    ]:
      with self.subTest(message), self.assertRaisesRegex(ValueError, message):
        await self.lc.start_experiment(protocol)
    with self.assertRaisesRegex(ValueError, "well_count"):
      await self.lc.start_experiment(reads(37), well_count=48)
    with self.assertRaisesRegex(ValueError, "32 hex"):
      await self.lc.start_experiment(reads(37), experiment_id="run-1")
    self.assertEqual(self.sent(CREATE_EXPERIMENT), [])

  async def test_a_run_the_instrument_is_already_running_is_not_interrupted(self):
    await self.load_plate()
    self.instrument.state = 7
    with self.assertRaisesRegex(RuntimeError, "did not start"):
      await self.lc.start_experiment(reads(37))
    self.assertEqual(self.sent(CREATE_EXPERIMENT), [])

  async def test_an_experiment_started_twice_by_its_id_runs_once(self):
    await self.load_plate()
    experiment_id = "0123456789abcdef0123456789abcdef"
    first = await self.lc.start_experiment(reads(37), experiment_id=experiment_id)
    second = await self.lc.start_experiment(reads(37), experiment_id=experiment_id)
    self.assertEqual(first, second)
    self.assertEqual(first, experiment_id.upper())
    with self.assertRaisesRegex(ValueError, "another protocol"):
      await self.lc.start_experiment(reads(50), experiment_id=experiment_id)
    await self.lc.wait_for_experiment(first)
    again = await self.lc.run_experiment(reads(37), experiment_id=experiment_id)
    self.assertEqual(len(again.acquisitions), 1)
    self.assertEqual(len(self.sent(START_RUN)), 1)

  async def test_one_experiment_runs_at_a_time_with_the_tray_shut(self):
    await self.load_plate()
    self.instrument.seconds_per_second = 0.05
    started = await self.lc.start_experiment(reads(37, 37))
    with self.assertRaisesRegex(RuntimeError, "is running"):
      await self.lc.start_experiment(reads(37))
    with self.assertRaisesRegex(RuntimeError, "is running"):
      await self.lc.open_tray()
    self.assertEqual((await self.lc.request_status()).running_experiment, started)
    with self.assertRaises(TimeoutError):
      await self.lc.wait_for_experiment(started, timeout=0.01)
    await self.lc.wait_for_experiment(started)

  async def test_an_experiment_is_watched_read_by_read(self):
    await self.lc.close_tray()
    self.instrument.seconds_per_second = 0.02
    started = await self.lc.start_experiment(reads(37, 37, 37))
    seen = [(e.status, len(e.acquisitions)) async for e in self.lc.watch_experiment(started)]
    self.assertEqual(seen[-1], ("complete", 3))
    self.assertIn(("running", 1), seen)
    self.assertIn(("running", 2), seen)

  async def test_experiments_are_listed_newest_first_and_found_by_id(self):
    await self.lc.close_tray()
    a = (await self.lc.run_experiment(reads(37))).id
    b = (await self.lc.run_experiment(reads(37, 37))).id
    listed = await self.lc.list_experiments()
    self.assertEqual([(s.id, s.acquisitions_done) for s in listed], [(b, 2), (a, 1)])
    self.assertEqual(len(await self.lc.list_experiments(limit=1)), 1)
    self.assertEqual((await self.lc.get_experiment(a.lower())).id, a)
    with self.assertRaises(KeyError):
      await self.lc.get_experiment("F" * 32)

  async def test_an_experiment_whose_instrument_goes_away_fails(self):
    await self.lc.close_tray()
    self.instrument.seconds_per_second = 0.05
    started = await self.lc.start_experiment(reads(37, 37))
    await asyncio.sleep(0.02)
    await self.instrument.stop()
    with self.assertRaises(ExperimentFailedError) as raised:
      await self.lc.wait_for_experiment(started, timeout=5)
    self.assertEqual(raised.exception.experiment_id, started)
    self.assertEqual((await self.lc.get_experiment(started)).status, "error")

  async def test_the_instruments_events_are_its_logs(self):
    await self.lc.close_tray()
    await self.lc.run_experiment(reads(37))
    for _ in range(100):
      codes = [e.code for e in await self.lc.request_logs(limit=1000)]
      if 101 in codes:
        break
      await asyncio.sleep(0.01)
    self.assertIn(201, codes)
    self.assertIn(101, codes)
    first = (await self.lc.request_logs(limit=1))[0]
    self.assertEqual((await self.lc.request_logs(since_id=first.id, limit=1))[0].id, first.id + 1)


class ConstructionTests(unittest.TestCase):
  def test_a_lightcycler_needs_a_host_or_simulation(self):
    with self.assertRaisesRegex(ValueError, "host"):
      LightCycler480()
    lc = LightCycler480(host="192.168.95.41")
    self.assertEqual(lc.driver.ports, [5100, 5101, 5102, 5104, 5105])
    self.assertIsNone(lc.tray_button)


if __name__ == "__main__":
  unittest.main()
