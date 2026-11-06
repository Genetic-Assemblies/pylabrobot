import asyncio
import unittest

from pylabrobot.high_res.microspin import (
  DoorLockPinError,
  MicroSpinAbortedError,
  MicroSpinError,
  MicroSpinSimulator,
  MicroSpinTimeoutError,
  NotHomedError,
  QueueTimeoutError,
  SimulatedMicroSpin,
)
from pylabrobot.high_res.microspin.errors import error_for, parse_error_entry
from pylabrobot.high_res.microspin.simulator import rpm_at

# What a device printed before ending `spin 3000 100 100 1200`, acknowledged as id 14, with
# `ERROR!`; abridged.
_DOOR_LOCK_PIN_LINES = [
  "WARNING: Retry of door lock pin",
  "WARNING: Retry of door lock pin",
  "Error 1: (10:10:45) -10: Unmount of `/rw' failed (-1)",
  "Error 2: (10:11:02) -60: Unable to mount the filesystem.",
  "Error 3: (12:18:42) 14: Unable to confirm door lock pin is in place",
]

# What a device printed before ending `home`, acknowledged as id 66, with `ERROR!`; abridged.
_HOME_TIMED_OUT_LINES = [
  "Error 21: (08:03:18) -11: A command (63 - status), slot 0 in the queue, timed out.",
  "Error 25: (08:06:34) -11: A command (54 - home), slot 0 in the queue, timed out.",
]


class ErrorTests(unittest.TestCase):
  def test_an_entry_is_read_into_its_parts(self):
    entry = parse_error_entry(
      "Error 12: (12:18:42) 14: Unable to confirm door lock pin is in place"
    )
    assert entry is not None
    self.assertEqual(
      (entry.index, entry.time, entry.command_id, entry.message),
      (12, "12:18:42", 14, "Unable to confirm door lock pin is in place"),
    )

  def test_a_line_that_is_not_an_entry_is_none(self):
    self.assertIsNone(parse_error_entry("WARNING: Retry of door lock pin"))

  def test_the_entries_carrying_the_commands_id_are_its_own(self):
    error = error_for("spin 3000 100 100 1200", 14, _DOOR_LOCK_PIN_LINES)
    self.assertIsInstance(error, DoorLockPinError)
    self.assertEqual([entry.index for entry in error.own_entries], [3])
    self.assertEqual(len(error.entries), 3)
    self.assertIn("door lock pin", str(error))

  def test_with_no_entry_of_its_own_the_newest_entry_explains_it(self):
    error = error_for("home", 66, _HOME_TIMED_OUT_LINES)
    self.assertIsInstance(error, QueueTimeoutError)
    self.assertEqual(error.own_entries, [])
    self.assertIn("54 - home", error.message)

  def test_an_unrecognized_message_is_a_microspin_error(self):
    error = error_for("home", 5, ["Error 1: (00:00:01) 5: something else"])
    self.assertIs(type(error), MicroSpinError)


class DriverTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.device = SimulatedMicroSpin()
    self.driver = MicroSpinSimulator(self.device)
    self.driver.default_spindle_poll_interval = 0.005
    await self.driver.setup()

  async def asyncTearDown(self):
    await self.driver.stop()

  def sent(self, connection: str):
    return [command for name, command in self.device.received if name == connection]

  async def wait_until_spinning(self):
    while not self.device.spinning:
      await asyncio.sleep(0)

  async def wait_until_at_speed(self, g: float):
    while self.device.spindle_rpm() < rpm_at(g) - 0.5:
      await asyncio.sleep(0.005)

  async def test_setup_reads_the_version_on_the_control_connection(self):
    self.assertEqual(self.sent("control"), ["version"])

  async def test_before_homing_open_and_spin_are_refused(self):
    self.assertFalse(await self.driver.request_homed())
    with self.assertRaises(NotHomedError):
      await self.driver.present_bucket(1)
    with self.assertRaises(NotHomedError):
      await self.driver.spin(g=500, duration=15)

  async def test_home_then_present_each_bucket(self):
    await self.driver.home()
    self.assertTrue(await self.driver.request_homed())
    await self.driver.present_bucket(2)
    self.assertEqual((await self.driver.request_status()).spindle_position, 4087)
    await self.driver.present_bucket(1)
    self.assertEqual((await self.driver.request_status()).spindle_position, 8186)
    self.assertEqual(self.sent("motion"), ["home", "open 2", "status", "open 1", "status"])

  async def test_a_bucket_that_is_not_1_or_2_is_refused_before_sending(self):
    with self.assertRaisesRegex(ValueError, "bucket"):
      await self.driver.present_bucket(3)  # type: ignore[arg-type]
    self.assertEqual(self.sent("motion"), [])

  async def test_spin_sends_whole_g_percent_ramps_and_seconds(self):
    await self.driver.home()
    await self.driver.spin(g=3000, duration=1200)
    await self.driver.spin(g=500.4, duration=30.6, acceleration=0.5, deceleration=0.456)
    self.assertEqual(self.sent("motion")[1:], ["spin 3000 100 100 1200", "spin 500 50 46 31"])

  async def test_spin_refuses_what_is_out_of_range_before_sending(self):
    for kwargs in (
      {"g": 3001, "duration": 10},
      {"g": 0.5, "duration": 10},
      {"g": 100, "duration": 0.5},
      {"g": 100, "duration": 10, "acceleration": 0},
      {"g": 100, "duration": 10, "deceleration": 1.5},
    ):
      with self.subTest(**kwargs), self.assertRaises(ValueError):
        await self.driver.spin(**kwargs)
    self.assertEqual(self.sent("motion"), [])

  async def test_a_door_lock_pin_failure_raises_its_own_error(self):
    await self.driver.home()
    self.device.fail_next(
      "spin", "Unable to confirm door lock pin is in place", ("WARNING: Retry of door lock pin",)
    )
    with self.assertRaises(DoorLockPinError) as raised:
      await self.driver.spin(g=3000, duration=60)
    self.assertEqual(raised.exception.lines[0], "WARNING: Retry of door lock pin")
    self.assertEqual(len(raised.exception.own_entries), 1)
    await self.driver.spin(g=3000, duration=60)

  async def test_abort_reaches_the_device_during_a_spin(self):
    await self.driver.home()
    self.device.seconds_per_second = 1000.0
    spin = asyncio.create_task(self.driver.spin(g=1000, duration=600))
    await self.wait_until_spinning()
    self.assertTrue(await self.driver.request_homed())
    await self.driver.abort()
    with self.assertRaises(MicroSpinAbortedError):
      await spin
    self.assertEqual(self.sent("control"), ["version", "homedstatus", "abort"])

  async def test_after_an_abort_motion_is_refused_until_the_latch_is_cleared(self):
    await self.driver.home()
    await self.driver.abort()
    with self.assertRaisesRegex(RuntimeError, "abort latch"):
      await self.driver.present_bucket(1)
    self.assertEqual(self.sent("motion"), ["home"])
    await self.driver.clear_abort()
    await self.driver.present_bucket(1)

  async def test_status_answers_once_the_spin_has_finished(self):
    await self.driver.home()
    self.device.seconds_per_second = 0.0001
    spin = asyncio.create_task(self.driver.spin(g=1000, duration=50))
    await self.wait_until_spinning()
    status = await self.driver.request_status()
    self.assertTrue(spin.done())
    self.assertEqual(status.spindle_position, (1958 + 1000) % 8192)

  async def test_a_timed_out_spin_gives_its_id_and_the_device_says_how_it_went(self):
    await self.driver.home()
    self.device.seconds_per_second = 0.002
    with self.assertRaises(MicroSpinTimeoutError) as raised:
      await self.driver.spin(g=1000, duration=600, timeout=0.01)
    command_id = raised.exception.command_id
    assert command_id is not None
    self.assertEqual(await self.driver.request_command_status(command_id), "RUNNING")
    await self.driver.reset(timeout=5)
    self.assertEqual(await self.driver.request_command_status(command_id), "ABORTED")

  async def test_after_a_spin_times_out_reset_stops_it_and_the_connection_still_works(self):
    await self.driver.home()
    self.device.seconds_per_second = 0.002
    with self.assertRaises(TimeoutError):
      await self.driver.spin(g=1000, duration=600, timeout=0.01)
    self.assertTrue(self.device.spinning)
    status = await self.driver.reset(timeout=5)
    self.assertFalse(self.device.spinning)
    self.assertEqual(status.spindle_position, 1958)
    await self.driver.present_bucket(2)
    self.assertEqual(self.device.presented, 2)

  async def test_the_spindle_velocity_reads_the_speed_for_its_g(self):
    await self.driver.home()
    self.device.seconds_per_second = 0.002
    spin = asyncio.create_task(self.driver.spin(g=500, duration=600))
    await self.wait_until_at_speed(500)
    self.assertAlmostEqual(await self.driver.request_spindle_velocity(), rpm_at(500), delta=1)
    await self.driver.reset(timeout=5)
    with self.assertRaises(MicroSpinAbortedError):
      await spin

  async def test_after_an_abort_nothing_is_sent_to_the_machine_until_the_rotor_stops(self):
    await self.driver.home()
    self.device.seconds_per_second = 0.002
    spin = asyncio.create_task(self.driver.spin(g=500, duration=600))
    await self.wait_until_at_speed(500)
    await self.driver.abort()
    with self.assertRaises(MicroSpinAbortedError):
      await spin
    self.assertGreater(await self.driver.request_spindle_velocity(), 100)
    with self.assertRaisesRegex(RuntimeError, "abort latch"):
      await self.driver.request_status()
    with self.assertRaisesRegex(RuntimeError, "still turning"):
      await self.driver.clear_abort()
    await self.driver.wait_for_spindle_stopped(timeout=5)
    await self.driver.clear_abort()
    await self.driver.request_status()
    await self.driver.home()
    self.assertEqual(self.sent("motion"), ["home", "spin 500 100 100 600", "status", "home"])

  async def test_reset_during_a_spin_waits_for_the_coast_then_recovers(self):
    await self.driver.home()
    self.device.seconds_per_second = 0.002
    spin = asyncio.create_task(self.driver.spin(g=500, duration=600))
    await self.wait_until_at_speed(500)
    status = await self.driver.reset(timeout=5)
    with self.assertRaises(MicroSpinAbortedError):
      await spin
    self.assertEqual(await self.driver.request_spindle_velocity(), 0)
    self.assertEqual(status.door_position, -451)
    control = self.sent("control")
    after_abort = control[control.index("abort") + 1 :]
    cleared = after_abort.index("clearbuttonabort")
    self.assertGreater(cleared, 1)
    self.assertEqual(set(after_abort[:cleared]), {"cget 1 24"})

  async def test_a_spin_longer_than_the_transports_read_timeout_finishes(self):
    device = SimulatedMicroSpin(seconds_per_second=0.002)
    driver = MicroSpinSimulator(device, read_timeout=0.05)
    await driver.setup()
    try:
      await driver.home()
      await driver.spin(g=500, duration=60)
    finally:
      await driver.stop()

  async def test_request_errors_reads_the_stack(self):
    self.device.fail_next("home", "Unable to confirm door lock pin is in place")
    with self.assertRaises(DoorLockPinError):
      await self.driver.home()
    entries = await self.driver.request_errors(5)
    self.assertEqual(
      [entry.message for entry in entries], ["Unable to confirm door lock pin is in place"]
    )


if __name__ == "__main__":
  unittest.main()
