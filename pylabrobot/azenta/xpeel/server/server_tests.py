import argparse
import asyncio
import importlib
import inspect
import unittest
from typing import Any, Dict, List
from unittest import mock

from connectrpc.errors import ConnectError

from pylabrobot.azenta.xpeel import XPeel
from pylabrobot.azenta.xpeel.server import RemoteXPeel, XPeelServer
from pylabrobot.azenta.xpeel.server.__main__ import _named_port, peelers
from pylabrobot.azenta.xpeel.server.v1 import xpeel_pb2 as pb
from pylabrobot.azenta.xpeel.simulator import SimulatedXPeel

# A peel takes a tenth of a second or so.
SPEED = 200.0

# The module, which the package's `serve` function shadows.
serve = importlib.import_module("pylabrobot.azenta.xpeel.server.serve")


class _Context:
  """What a handler is given."""

  def __init__(self) -> None:
    self.response_headers: Dict[str, str] = {}


class ParityTests(unittest.TestCase):
  def test_every_public_coroutine_is_a_call(self):
    remote = dict(inspect.getmembers(RemoteXPeel, inspect.iscoroutinefunction))
    for name, method in inspect.getmembers(XPeel, inspect.iscoroutinefunction):
      if name.startswith("_"):
        continue
      with self.subTest(name):
        self.assertTrue(remote[name].__qualname__.startswith("RemoteXPeel."))
        self.assertEqual(
          inspect.signature(remote[name]).parameters, inspect.signature(method).parameters
        )

  def test_a_remote_one_is_an_xpeel(self):
    remote = RemoteXPeel("peeler_1", XPeelServer.local({"peeler_1": SimulatedXPeel()}))
    self.assertIsInstance(remote, XPeel)
    self.assertEqual(remote.describe_error(7), "Out of tape or tape broke")


class LocalAndRemoteTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.local = SimulatedXPeel(speed=SPEED)
    self.served = SimulatedXPeel(port="/dev/sim", speed=SPEED)
    self.remote = RemoteXPeel("peeler_1", XPeelServer.local({"peeler_1": self.served}))

  async def _run(self, xpeel: XPeel) -> List[Any]:
    """What a peeling run returns, as a list a local and a remote one can be compared by."""
    out: List[Any] = []
    await xpeel.setup()
    out.append(await xpeel.request_status())
    out.append(await xpeel.request_version())
    out.append(await xpeel.seal_check())
    out.append(await xpeel.enable_plate_check(False))
    out.append(await xpeel.peel(begin_location=2, fast=True, adhere_time=5.0))
    out.append(await xpeel.seal_check())
    out.append(await xpeel.request_tape_remaining())
    out.append(await xpeel.request_seal_sensor_status())
    out.append(await xpeel.set_seal_threshold_upper(600))
    out.append(await xpeel.set_seal_threshold_lower(100))
    out.append(await xpeel.move_conveyor_out())
    out.append(await xpeel.move_conveyor_in())
    out.append(await xpeel.move_elevator_down())
    out.append(await xpeel.move_elevator_up())
    out.append(await xpeel.advance_tape())
    out.append(await xpeel.send_command("*stat"))
    out.append(await xpeel.send_command("*moveout", expect_ack=True, wait_for_ready=True))
    out.append(await xpeel.reset())
    out.append(await xpeel.restart())
    out.append(await xpeel.peel())
    await xpeel.stop()
    return out

  async def test_a_remote_one_does_what_a_local_one_does(self):
    local = await self._run(self.local)
    remote = await self._run(self.remote)
    self.assertEqual(remote, local)
    self.assertEqual(self.served.simulator.written, self.local.simulator.written)
    self.assertEqual(self.served.simulator.peels, [(5, 2), (4, 1)])
    self.assertEqual(remote[6], (290, 290))

  async def test_setup_takes_up_the_servers_port_and_timeout(self):
    await self.remote.setup()
    self.assertEqual((self.remote.port, self.remote.response_timeout), ("/dev/sim", 20.0))

  async def test_a_failed_peel_answers_as_it_does_locally(self):
    self.served.simulator.fault = 4
    self.local.simulator.fault = 4
    self.assertEqual(await self.remote.peel(), await self.local.peel())
    self.assertEqual(await self.remote.request_status(), (4, 0, 0))

  async def test_errors_come_back_as_they_were_raised(self):
    with self.assertRaisesRegex(ValueError, "adhere_time must be one of"):
      await self.remote.peel(adhere_time=3.0)
    with self.assertRaisesRegex(ValueError, "begin_location must be one of"):
      await self.remote.peel(begin_location=3)  # type: ignore[arg-type]
    with self.assertRaisesRegex(ValueError, "between 0 and 999"):
      await self.remote.set_seal_threshold_upper(1000)
    self.served.simulator.plate = False
    self.served.simulator.plate_check = True
    self.assertEqual(await self.remote.seal_check(), "plate_not_detected")
    simulator = self.served.simulator
    with mock.patch.object(simulator, "_command", lambda command: simulator._send("*ready:xx")):
      with self.assertRaisesRegex(RuntimeError, "Could not parse ready line"):
        await self.remote.seal_check()

  async def test_a_name_the_server_does_not_serve_is_refused(self):
    other = RemoteXPeel("peeler_9", self.remote.server)
    with self.assertRaisesRegex(ConnectError, "peeler_9"):
      await other.request_status()
    with self.assertRaisesRegex(ConnectError, "peeler_9"):
      await other.peel()


class LongCallTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    patcher = mock.patch.object(serve, "PROGRESS_INTERVAL", 0.01)
    patcher.start()
    self.addCleanup(patcher.stop)
    self.sim = SimulatedXPeel(speed=SPEED / 4)
    await self.sim.setup()
    self.served = serve._Served({"peeler_1": self.sim})

  async def test_a_peel_streams_until_it_is_done(self):
    progress = [
      each
      async for each in self.served.peel(
        pb.PeelRequest(name="peeler_1"),
        _Context(),
      )
    ]
    self.assertGreater(len(progress), 1)
    self.assertTrue(progress[-1].done)
    self.assertFalse(any(each.done for each in progress[:-1]))
    self.assertEqual(list(progress[-1].lines.lines), ["*ack", "*ready:00,00,00 [No error]"])

  async def test_a_peel_finishes_on_the_server_when_its_client_goes(self):
    progress = self.served.peel(pb.PeelRequest(name="peeler_1"), _Context())
    first = await progress.__anext__()
    self.assertFalse(first.done)
    await progress.aclose()
    self.assertEqual(len(self.served._running), 1)
    for _ in range(100):
      if not self.served._running:
        break
      await asyncio.sleep(0.05)
    self.assertEqual(self.served._running, set())
    # The ready line was read by the peel, not left for the next command.
    self.assertEqual(await self.sim.request_status(), (0, 0, 0))
    self.assertEqual(self.sim.simulator.peels, [(4, 1)])

  async def test_a_check_is_dropped_when_its_client_goes(self):
    progress = self.served.request_tape_remaining(
      pb.RequestTapeRemainingRequest(name="peeler_1"),
      _Context(),
    )
    await progress.__anext__()
    await progress.aclose()
    await asyncio.sleep(0.01)
    self.assertEqual(self.served._running, set())

  async def test_a_call_waits_for_the_one_before_it(self):
    remote = RemoteXPeel("peeler_1", XPeelServer.local({"peeler_1": self.sim}))
    peel = asyncio.ensure_future(remote.peel())
    await asyncio.sleep(0.02)
    status = asyncio.ensure_future(remote.request_status())
    await asyncio.sleep(0.02)
    # The peel is still running, and the status waits for it before it writes to the peeler.
    self.assertFalse(peel.done())
    self.assertEqual(self.sim.simulator.written, ["*xpeel:41"])
    self.assertEqual(await status, (0, 0, 0))
    self.assertEqual(await peel, ["*ack", "*ready:00,00,00 [No error]"])
    self.assertEqual(self.sim.simulator.written, ["*xpeel:41", "*stat"])


class CommandLineTests(unittest.TestCase):
  def test_a_peeler_is_named_with_its_port(self):
    self.assertEqual(_named_port("peeler_1:/dev/ttyUSB1"), ("peeler_1", "/dev/ttyUSB1"))
    self.assertEqual(_named_port("peeler_1"), ("peeler_1", None))
    for text in (":/dev/ttyUSB1", "peeler_1:"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _named_port(text)

  def test_simulation_serves_simulated_peelers(self):
    args = argparse.Namespace(
      xpeel=[("peeler_1", None)], simulation=True, simulation_speed=2.0, timeout=20.0
    )
    self.assertIsInstance(peelers(args)["peeler_1"], SimulatedXPeel)
    args.simulation = False
    with self.assertRaises(SystemExit):
      peelers(args)


if __name__ == "__main__":
  unittest.main()
