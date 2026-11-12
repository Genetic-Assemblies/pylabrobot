import argparse
import asyncio
import importlib
import inspect
import unittest
from typing import Any, Dict, List
from unittest import mock

from connectrpc.errors import ConnectError

from pylabrobot.azenta.a4s import A4S, A4SStatus
from pylabrobot.azenta.a4s.server import A4SServer, RemoteA4S
from pylabrobot.azenta.a4s.server.__main__ import _named_port, sealers
from pylabrobot.azenta.a4s.server.v1 import a4s_pb2 as pb
from pylabrobot.azenta.a4s.simulator import SimulatedA4S

# Fast enough that a seal takes a fraction of a second, slow enough that the driver, which pauses a
# tenth of a second after each command, sees the seal cycle run.
SPEED = 40.0

# The module, which the package's `serve` function shadows.
serve = importlib.import_module("pylabrobot.azenta.a4s.server.serve")


class _Context:
  """What a handler is given."""

  def __init__(self) -> None:
    self.response_headers: Dict[str, str] = {}


class ParityTests(unittest.TestCase):
  def test_every_public_coroutine_is_a_call(self):
    remote = dict(inspect.getmembers(RemoteA4S, inspect.iscoroutinefunction))
    for name, method in inspect.getmembers(A4S, inspect.iscoroutinefunction):
      if name.startswith("_"):
        continue
      with self.subTest(name):
        self.assertTrue(remote[name].__qualname__.startswith("RemoteA4S."))
        self.assertEqual(
          inspect.signature(remote[name]).parameters, inspect.signature(method).parameters
        )

  def test_a_remote_one_is_an_a4s(self):
    remote = RemoteA4S("sealer_1", A4SServer.local({"sealer_1": SimulatedA4S()}))
    self.assertIsInstance(remote, A4S)
    self.assertFalse(remote.supports_active_cooling)


class LocalAndRemoteTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.local = SimulatedA4S(speed=SPEED)
    self.served = SimulatedA4S(port="/dev/sim", speed=SPEED)
    self.remote = RemoteA4S("sealer_1", A4SServer.local({"sealer_1": self.served}))

  async def _run(self, a4s: A4S) -> List[Any]:
    """What a sealing run returns, as a list a local and a remote one can be compared by."""
    out: List[Any] = []
    await a4s.setup()
    out.append((await a4s.request_status()).system_status)
    out.append((await a4s.open()).sensor_status)
    await a4s.set_temperature(60)
    out.append(await a4s.request_current_temperature())
    sealed = await a4s.seal(60, 0.5)
    out.append((sealed.current_temperature, sealed.error_code, sealed.sensor_status))
    out.append(await a4s.request_remaining_time())
    out.append((await a4s.close()).sensor_status.shuttle_open_sensor)
    out.append((await a4s.set_heater(on=False)).system_status)
    await a4s.set_time(1.5)
    await a4s.send_command("*00MO=zz!")
    status = await a4s.wait_for_shuttle_open_sensor(True, timeout=5)
    out.append(status.sensor_status.shuttle_open_sensor)
    out.append((await a4s.wait_for_status({A4SStatus.SystemStatus.idle})).system_status)
    out.append((await a4s.read_message())[:2])
    out.append((await a4s.system_reset()).system_status)
    await a4s.deactivate()
    await a4s.stop()
    return out

  async def test_a_remote_one_does_what_a_local_one_does(self):
    local = await self._run(self.local)
    remote = await self._run(self.remote)
    self.assertEqual(remote, local)
    self.assertEqual(self.served.simulator.written, self.local.simulator.written)
    self.assertEqual(self.served.simulator.sealed, 1)
    self.assertIn("*00DT=0015zz!", self.served.simulator.written)

  async def test_setup_takes_up_the_servers_port_and_timeout(self):
    await self.remote.setup()
    self.assertEqual((self.remote.port, self.remote.timeout), ("/dev/sim", 20))

  async def test_errors_come_back_as_they_were_raised(self):
    await self.remote.setup()
    with self.assertRaisesRegex(ValueError, "Temperature out of range"):
      await self.remote.set_temperature(30)
    with self.assertRaisesRegex(ValueError, "Time out of range"):
      await self.remote.set_time(1000)
    self.served.simulator.fault = 7
    with self.assertRaisesRegex(RuntimeError, "An error occurred"):
      await self.remote.request_status()
    self.served.timeout = 0
    with self.assertRaises(TimeoutError):
      await self.remote.wait_for_status({A4SStatus.SystemStatus.finish})

  async def test_a_name_the_server_does_not_serve_is_refused(self):
    other = RemoteA4S("sealer_9", self.remote.server)
    with self.assertRaisesRegex(ConnectError, "sealer_9"):
      await other.request_status()
    with self.assertRaisesRegex(ConnectError, "sealer_9"):
      await other.open()


class LongCallTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    patcher = mock.patch.object(serve, "PROGRESS_INTERVAL", 0.01)
    patcher.start()
    self.addCleanup(patcher.stop)
    self.sim = SimulatedA4S(speed=SPEED)
    await self.sim.setup()
    self.served = serve._Served({"sealer_1": self.sim})

  async def test_a_seal_streams_until_it_is_done(self):
    progress = [
      each
      async for each in self.served.seal(
        pb.SealRequest(name="sealer_1", temperature=60, duration=0.5),
        _Context(),
      )
    ]
    self.assertGreater(len(progress), 1)
    self.assertTrue(progress[-1].done)
    self.assertFalse(any(each.done for each in progress[:-1]))
    self.assertEqual(progress[-1].status.current_temperature, 60.0)

  async def test_a_seal_finishes_on_the_server_when_its_client_goes(self):
    request = pb.SealRequest(name="sealer_1", temperature=60, duration=0.5)
    progress = self.served.seal(request, _Context())
    first = await progress.__anext__()
    self.assertFalse(first.done)
    await progress.aclose()
    self.assertEqual(self.sim.simulator.sealed, 0)
    for _ in range(200):
      if self.sim.simulator.sealed:
        break
      await asyncio.sleep(0.05)
    self.assertEqual(self.sim.simulator.sealed, 1)

  async def test_a_wait_is_dropped_when_its_client_goes(self):
    request = pb.WaitForStatusRequest(name="sealer_1", statuses=[pb.SYSTEM_STATUS_FINISH])
    progress = self.served.wait_for_status(request, _Context())
    await progress.__anext__()
    await progress.aclose()
    await asyncio.sleep(0.01)
    self.assertEqual(self.served._running, set())
    # The sealer is free for the next call.
    self.assertEqual(await self.sim.request_current_temperature(), 25.0)

  async def test_a_call_waits_for_the_one_before_it(self):
    remote = RemoteA4S("sealer_1", A4SServer.local({"sealer_1": self.sim}))
    seal = asyncio.ensure_future(remote.seal(60, 0.5))
    await asyncio.sleep(0.05)
    temperature = await remote.request_current_temperature()
    self.assertTrue(seal.done())
    self.assertEqual(temperature, 60.0)
    await seal


class CommandLineTests(unittest.TestCase):
  def test_a_sealer_is_named_with_its_port(self):
    self.assertEqual(_named_port("sealer_1:/dev/ttyUSB0"), ("sealer_1", "/dev/ttyUSB0"))
    self.assertEqual(_named_port("sealer_1"), ("sealer_1", None))
    for text in (":/dev/ttyUSB0", "sealer_1:"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _named_port(text)

  def test_simulation_serves_simulated_sealers(self):
    args = argparse.Namespace(
      a4s=[("sealer_1", None)], simulation=True, simulation_speed=2.0, timeout=20
    )
    made = sealers(args)
    self.assertIsInstance(made["sealer_1"], SimulatedA4S)
    args.simulation = False
    with self.assertRaises(SystemExit):
      sealers(args)


if __name__ == "__main__":
  unittest.main()
