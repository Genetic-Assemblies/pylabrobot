import asyncio
import unittest
from typing import Any, AsyncIterator, List

from connectrpc.code import Code
from connectrpc.errors import ConnectError

from pylabrobot.high_res.microspin import (
  DoorLockPinError,
  MicroSpin,
  MicroSpinSimulator,
  NotHomedError,
  SimulatedMicroSpin,
)
from pylabrobot.high_res.microspin.server import (
  MicroSpinServer,
  ServedMicroSpin,
  microspin_server_app,
)
from pylabrobot.high_res.microspin.server.v1 import microspin_pb2 as mpb
from pylabrobot.resources.server import ResourceServer


class _DropsTheFirstSpinStream:
  """The service, with the first spin stream it gives dropping after its first update."""

  def __init__(self, service: Any) -> None:
    self._service = service
    self.dropped = False

  async def spin(self, request: mpb.SpinRequest) -> AsyncIterator[mpb.SpinUpdate]:
    async for update in self._service.spin(request):
      yield update
      if not self.dropped:
        self.dropped = True
        raise ConnectError(Code.UNAVAILABLE, "connection reset")


class ServedMicroSpinTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.resources = ResourceServer.local()
    self.device = SimulatedMicroSpin()
    driver = MicroSpinSimulator(self.device)
    driver.default_spindle_poll_interval = 0.005
    self.local = MicroSpin(name="cf", driver=driver, resource_server=self.resources)
    await self.local.setup()
    settings = mpb.Settings(default_acceleration=0.5)
    app = microspin_server_app(self.local, settings=settings, progress_interval=0.005)
    self.server = MicroSpinServer.in_process(app)
    served = MicroSpin(microspin_server=self.server, resource_server=self.resources)
    assert isinstance(served, ServedMicroSpin)
    self.served = served
    self.served.reconnect_delay = 0.0
    await self.served.setup()

  async def asyncTearDown(self):
    await self.local.stop()

  def spins_sent(self) -> List[str]:
    return [c for name, c in self.device.received if name == "motion" and c.startswith("spin")]

  async def test_a_served_microspin_is_the_servers_device_on_the_same_resources(self):
    self.assertIsInstance(self.served, ServedMicroSpin)
    self.assertEqual(self.served.name, "cf")
    assert self.served.body is not None and self.local.body is not None
    self.assertEqual(self.served.body.id, self.local.body.id)
    self.assertEqual(self.served.buckets[2].id, self.local.buckets[2].id)

  async def test_moves_are_made_on_the_device_and_read_back_off_the_shared_model(self):
    await self.served.home()
    await self.served.present_bucket(2)
    at_door = await self.served.get_bucket_at_door()
    assert at_door is not None
    self.assertEqual(at_door.id, self.local.buckets[2].id)
    self.assertEqual((await self.served.request_status()).spindle_position, 4087)
    self.assertTrue(await self.served.request_homed())

  async def test_what_the_device_raises_the_client_raises(self):
    with self.assertRaises(NotHomedError) as raised:
      await self.served.present_bucket(1)
    self.assertIn("Machine must be homed", str(raised.exception))
    self.assertEqual(len(raised.exception.own_entries), 1)
    with self.assertRaisesRegex(ValueError, "bucket"):
      await self.served.present_bucket(3)  # type: ignore[arg-type]

  async def test_the_servers_settings_reach_the_client_and_the_device(self):
    self.assertEqual(self.served.settings.default_acceleration, 0.5)
    await self.served.home()
    await self.served.spin(g=500, duration=10)
    self.assertEqual(self.spins_sent(), ["spin 500 50 100 10"])

  async def test_a_spin_streams_the_spindle_and_ends_finished(self):
    await self.served.home()
    self.device.seconds_per_second = 0.002
    updates = [u async for u in self.served.stream_spin(g=500, duration=60)]
    self.assertEqual(updates[-1].phase, mpb.SPIN_PHASE_FINISHED)
    self.assertFalse(updates[-1].HasField("error"))
    self.assertGreater(max(u.rpm for u in updates), 1900)

  async def test_a_spin_that_fails_raises_its_error_on_the_client(self):
    await self.served.home()
    self.device.fail_next("spin", "Unable to confirm door lock pin is in place")
    with self.assertRaises(DoorLockPinError):
      await self.served.spin(g=500, duration=10)

  async def test_an_unbalanced_spin_is_refused(self):
    await self.served.home()
    await self.resources.create(
      "cor_96_wellplate_360uL_Fb", name="plate", parent=self.local.buckets[1]
    )
    with self.assertRaisesRegex(ValueError, "balance"):
      await self.served.spin(g=500, duration=10)
    self.assertEqual(self.spins_sent(), [])

  async def test_a_spin_asked_for_twice_by_one_id_is_sent_once(self):
    await self.served.home()
    self.device.seconds_per_second = 0.002
    request_id = (7).to_bytes(8, "big")

    async def last(updates: AsyncIterator[mpb.SpinUpdate]) -> mpb.SpinUpdate:
      result = mpb.SpinUpdate()
      async for update in updates:
        result = update
      return result

    a, b = await asyncio.gather(
      last(self.served.stream_spin(g=500, duration=30, request_id=request_id)),
      last(self.served.stream_spin(g=500, duration=30, request_id=request_id)),
    )
    self.assertEqual(a.phase, mpb.SPIN_PHASE_FINISHED)
    self.assertEqual(b.phase, mpb.SPIN_PHASE_FINISHED)
    self.assertEqual(self.spins_sent(), ["spin 500 50 100 30"])

  async def test_one_id_for_another_spin_is_refused(self):
    await self.served.home()
    request_id = b"\x01"
    async for _ in self.served.stream_spin(g=500, duration=10, request_id=request_id):
      pass
    with self.assertRaises(ConnectError) as raised:
      async for _ in self.served.stream_spin(g=600, duration=10, request_id=request_id):
        pass
    self.assertEqual(raised.exception.code, Code.ALREADY_EXISTS)

  async def test_a_dropped_spin_stream_is_asked_for_again_and_the_spin_is_not_doubled(self):
    await self.served.home()
    self.device.seconds_per_second = 0.002
    dropping = _DropsTheFirstSpinStream(self.server.service)
    self.served.server.service = dropping  # type: ignore[assignment]
    await self.served.spin(g=500, duration=30)
    self.assertTrue(dropping.dropped)
    self.assertEqual(self.spins_sent(), ["spin 500 50 100 30"])

  async def test_another_client_can_watch_a_spin_by_its_id(self):
    await self.served.home()
    self.device.seconds_per_second = 0.002
    request_id = b"watched"
    started = self.served.stream_spin(g=500, duration=60, request_id=request_id)
    first = await started.__anext__()
    self.assertEqual(first.phase, mpb.SPIN_PHASE_RUNNING)
    other = ServedMicroSpin(microspin_server=self.server, resource_server=self.resources)
    watched = [u async for u in other.watch_spin(request_id)]
    self.assertEqual(watched[-1].phase, mpb.SPIN_PHASE_FINISHED)
    async for _ in started:
      pass

  async def test_reset_through_the_server_stops_a_spin(self):
    await self.served.home()
    self.device.seconds_per_second = 0.002
    spin = asyncio.create_task(self.served.spin(g=500, duration=600))
    while self.device.spindle_rpm() < 1000:
      await asyncio.sleep(0.005)
    status = await self.served.reset(timeout=5)
    self.assertEqual(status.door_position, -451)
    with self.assertRaisesRegex(Exception, "aborted"):
      await spin
    self.assertEqual(await self.served.get_door(), "closed")

  async def test_a_served_microspin_refuses_what_the_server_decides(self):
    with self.assertRaisesRegex(ValueError, "what its server makes it"):
      MicroSpin(host="1.2.3.4", microspin_server=self.server, resource_server=self.resources)
    with self.assertRaisesRegex(RuntimeError, "on its server"):
      _ = self.served.driver


if __name__ == "__main__":
  unittest.main()
