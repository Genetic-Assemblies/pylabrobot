import asyncio
import unittest

from pylabrobot.high_res.microspin import (
  MicroSpin,
  MicroSpinAbortedError,
  MicroSpinSimulator,
  MicroSpinTimeoutError,
  SimulatedMicroSpin,
)
from pylabrobot.resources.server import ResourceServer


class MicroSpinTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.server = ResourceServer.local()
    self.device = SimulatedMicroSpin()
    self.microspin = MicroSpin(
      name="cf", driver=MicroSpinSimulator(self.device), resource_server=self.server
    )
    await self.microspin.setup()

  async def asyncTearDown(self):
    await self.microspin.stop()

  def sent(self):
    return [command for name, command in self.device.received if name == "motion"]

  async def test_setup_makes_the_body_rotor_and_buckets(self):
    body = await self.server.get("cf")
    rotor = await body.get_resource("cf_rotor")
    names = sorted(child.name for child in await rotor.get_children())
    self.assertEqual(names, ["cf_bucket_1", "cf_bucket_2"])

  async def test_a_second_setup_takes_up_the_resources_already_there(self):
    again = MicroSpin(name="cf", driver=MicroSpinSimulator(), resource_server=self.server)
    await again.setup()
    try:
      assert again.body is not None and self.microspin.body is not None
      self.assertEqual(again.body.id, self.microspin.body.id)
      self.assertEqual(len(await self.server.roots()), 1)
    finally:
      await again.stop()

  async def test_presenting_a_bucket_turns_the_rotor_and_opens_the_door(self):
    await self.microspin.home()
    self.assertEqual(await self.microspin.get_door(), "closed")
    self.assertIsNone(await self.microspin.get_bucket_at_door())
    await self.microspin.present_bucket(2)
    self.assertEqual(await self.microspin.get_door(), "open")
    self.assertIs(await self.microspin.get_bucket_at_door(), self.microspin.buckets[2])
    assert self.microspin.rotor is not None
    self.assertAlmostEqual((await self.microspin.rotor.get_rotation()).z, 180, delta=1)
    await self.microspin.present_bucket(1)
    self.assertIs(await self.microspin.get_bucket_at_door(), self.microspin.buckets[1])

  async def test_a_spin_with_one_bucket_loaded_is_refused_before_sending(self):
    await self.microspin.home()
    await self.server.create(
      "cor_96_wellplate_360uL_Fb", name="plate_1", parent=self.microspin.buckets[1]
    )
    with self.assertRaisesRegex(ValueError, "balance"):
      await self.microspin.spin(g=500, duration=10)
    self.assertEqual(self.sent(), ["home", "status"])

  async def test_a_balanced_spin_closes_the_door_and_keeps_the_plates_in_their_buckets(self):
    await self.microspin.home()
    await self.microspin.present_bucket(1)
    for bucket in (1, 2):
      await self.server.create(
        "cor_96_wellplate_360uL_Fb", name=f"plate_{bucket}", parent=self.microspin.buckets[bucket]
      )
    await self.microspin.spin(g=500, duration=10)
    self.assertEqual(await self.microspin.get_door(), "closed")
    for bucket in (1, 2):
      held = await self.microspin.buckets[bucket].get_resource_held()
      assert held is not None
      self.assertEqual(held.name, f"plate_{bucket}")

  async def test_reset_during_a_spin_records_where_the_rotor_stopped(self):
    await self.microspin.home()
    await self.microspin.present_bucket(2)
    self.device.seconds_per_second = 0.002
    self.microspin.driver.default_spindle_poll_interval = 0.005
    spin = asyncio.create_task(self.microspin.spin(g=500, duration=600))
    while self.device.spindle_rpm() < 100:
      await asyncio.sleep(0.005)
    await self.microspin.reset(timeout=5)
    with self.assertRaises(MicroSpinAbortedError):
      await spin
    self.assertEqual(await self.microspin.get_door(), "closed")
    self.assertIsNone(await self.microspin.get_bucket_at_door())

  async def test_a_spin_that_times_out_raises_its_own_timeout_at_once(self):
    await self.microspin.home()
    self.device.seconds_per_second = 0.01
    self.microspin.driver.default_timeout = 0.2
    loop = asyncio.get_running_loop()
    started = loop.time()
    with self.assertRaises(MicroSpinTimeoutError):
      await self.microspin.spin(g=500, duration=600, timeout=0.05)
    self.assertLess(loop.time() - started, 0.15)
    await self.microspin.reset(timeout=10)

  async def test_a_microspin_needs_a_host_a_simulation_or_a_driver(self):
    with self.assertRaisesRegex(ValueError, "host"):
      MicroSpin()


if __name__ == "__main__":
  unittest.main()
