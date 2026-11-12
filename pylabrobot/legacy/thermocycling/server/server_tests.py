import argparse
import asyncio
import importlib
import inspect
import unittest
from typing import Any, Dict, List, Optional
from unittest import mock

from connectrpc.errors import ConnectError

from pylabrobot.legacy.machines.backend import MachineBackend
from pylabrobot.legacy.thermocycling.backend import ThermocyclerBackend
from pylabrobot.legacy.thermocycling.server import RemoteThermocyclerBackend, ThermocyclerServer
from pylabrobot.legacy.thermocycling.server.__main__ import _named_backend, thermocyclers
from pylabrobot.legacy.thermocycling.server.v1 import thermocycler_pb2 as pb
from pylabrobot.legacy.thermocycling.simulator import ThermocyclerSimulatorBackend
from pylabrobot.legacy.thermocycling.standard import BlockStatus, LidStatus, Protocol, Stage, Step
from pylabrobot.legacy.thermocycling.thermocycler import Thermocycler
from pylabrobot.resources import Coordinate

# A three-stage PCR takes a fraction of a second.
SPEED = 400.0

# The module, which the package's `serve` function shadows.
serve = importlib.import_module("pylabrobot.legacy.thermocycling.server.serve")

PCR = Protocol(
  stages=[
    Stage(steps=[Step([95.0], 30)], repeats=1),
    Stage(steps=[Step([95.0], 10), Step([55.0], 10, rate=2.5), Step([72.0], 20)], repeats=3),
    Stage(steps=[Step([4.0], 0)], repeats=1),
  ]
)


def _thermocycler(backend: ThermocyclerBackend) -> Thermocycler:
  return Thermocycler(
    name="tc", size_x=150, size_y=150, size_z=100, backend=backend, child_location=Coordinate.zero()
  )


class _Context:
  """What a handler is given."""

  def __init__(self) -> None:
    self.response_headers: Dict[str, str] = {}


class _BlockBackend(ThermocyclerSimulatorBackend):
  """A backend that takes a block id, as a ThermoFisher's does, and whose run waits for its end, as
  some do; it says which block each call was for."""

  def __init__(self, **kwargs: Any):
    super().__init__(**kwargs)
    self.blocks: List[Optional[int]] = []

  async def set_block_temperature(self, temperature: List[float], block_id: Optional[int] = None):
    assert block_id is not None, "block_id must be specified"
    self.blocks.append(block_id)
    await super().set_block_temperature(temperature)

  async def run_protocol(
    self, protocol: Protocol, block_max_volume: float, block_id: Optional[int] = None
  ):
    self.blocks.append(block_id)
    await super().run_protocol(protocol, block_max_volume)
    assert self._run is not None
    await self._run

  async def get_lid_open(self) -> bool:
    raise NotImplementedError("this one cannot say whether its lid is open")


class ParityTests(unittest.TestCase):
  def test_every_method_of_the_interface_is_a_call(self):
    remote = dict(inspect.getmembers(RemoteThermocyclerBackend, inspect.iscoroutinefunction))
    for name, method in inspect.getmembers(ThermocyclerBackend, inspect.iscoroutinefunction):
      if name.startswith("_"):
        continue
      with self.subTest(name):
        self.assertTrue(remote[name].__qualname__.startswith("RemoteThermocyclerBackend."))
        expected = list(inspect.signature(method).parameters.values())
        if name != "stop":
          expected.append(inspect.Parameter("backend_kwargs", inspect.Parameter.VAR_KEYWORD))
        parameters = list(inspect.signature(remote[name]).parameters.values())
        self.assertEqual(parameters, expected)

  def test_it_serializes_as_a_machine_backend(self):
    backend = RemoteThermocyclerBackend("tc_1", "http://127.0.0.1:8096")
    again = MachineBackend.deserialize(backend.serialize())
    self.assertIsInstance(again, RemoteThermocyclerBackend)
    self.assertEqual((again.name, again.server.address), ("tc_1", "http://127.0.0.1:8096"))

  def test_a_protocol_goes_over_as_it_is(self):
    self.assertEqual(serve.protocol_from_proto(serve.protocol_to_proto(PCR)), PCR)


class LocalAndRemoteTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.local_backend = ThermocyclerSimulatorBackend(speed=SPEED)
    self.served = ThermocyclerSimulatorBackend(speed=SPEED)
    self.server = ThermocyclerServer.local({"tc_1": self.served})
    self.remote_backend = RemoteThermocyclerBackend("tc_1", self.server)

  async def _run(self, tc: Thermocycler) -> List[Any]:
    """What a PCR run says, as a list a local and a remote one can be compared by."""
    out: List[Any] = []
    await tc.setup()
    await tc.open_lid()
    out.append(await tc.get_lid_open())
    await tc.close_lid()
    out.append(await tc.get_lid_open())
    out.append(await tc.is_profile_running())
    await tc.set_lid_temperature([105.0])
    out.append(await tc.get_lid_target_temperature())
    await tc.run_protocol(PCR, block_max_volume=25)
    out.append(await tc.is_profile_running())
    await tc.wait_for_profile_completion(poll_interval=0.02)
    out.append(await tc.get_block_current_temperature())
    out.append(await tc.get_block_target_temperature())
    out.append(await tc.get_block_status())
    out.append(await tc.get_hold_time())
    out.append(
      (
        await tc.get_current_cycle_index(),
        await tc.get_total_cycle_count(),
        await tc.get_current_step_index(),
        await tc.get_total_step_count(),
      )
    )
    await tc.deactivate_lid()
    out.append(await tc.get_lid_status())
    await tc.deactivate_block()
    await tc.stop()
    return out

  async def test_a_remote_backend_does_what_a_local_one_does(self):
    local = await self._run(_thermocycler(self.local_backend))
    remote = await self._run(_thermocycler(self.remote_backend))
    self.assertEqual(remote, local)
    self.assertEqual(remote[0:3], [True, False, False])
    self.assertEqual(remote[4], True)
    self.assertEqual(remote[5:8], [[4.0], [4.0], BlockStatus.HOLDING_AT_TARGET])
    self.assertEqual(remote[-1], LidStatus.IDLE)
    self.assertEqual(self.served.ran, [PCR])

  async def test_the_server_says_what_it_holds(self):
    described = await self.server.describe()
    self.assertEqual(
      [(t.name, t.backend) for t in described], [("tc_1", "ThermocyclerSimulatorBackend")]
    )

  async def test_errors_come_back_as_they_were_raised(self):
    tc = _thermocycler(self.remote_backend)
    await tc.setup()
    with self.assertRaisesRegex(ValueError, "Expected 1 block temperatures, got 2"):
      await tc.set_block_temperature([95.0, 95.0])
    with self.assertRaisesRegex(RuntimeError, "Block target temperature is not set"):
      await tc.get_block_target_temperature()
    await tc.open_lid()
    with self.assertRaisesRegex(RuntimeError, "the lid is open"):
      await tc.run_protocol(PCR, block_max_volume=25)
    with self.assertRaisesRegex(TypeError, "JSON serializable"):
      await tc.open_lid(block=object())
    with self.assertRaisesRegex(TypeError, "unexpected keyword argument 'block_id'"):
      await tc.open_lid(block_id=0)

  async def test_a_name_the_server_does_not_serve_is_refused(self):
    other = RemoteThermocyclerBackend("tc_9", self.server)
    with self.assertRaisesRegex(ConnectError, "tc_9"):
      await other.get_lid_open()
    with self.assertRaisesRegex(ConnectError, "tc_9"):
      await other.open_lid()


class BackendArgumentTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    patcher = mock.patch.object(serve, "PROGRESS_INTERVAL", 0.01)
    patcher.start()
    self.addCleanup(patcher.stop)
    self.served = _BlockBackend(speed=SPEED)
    self.tc = _thermocycler(
      RemoteThermocyclerBackend("tc_1", ThermocyclerServer.local({"tc_1": self.served}))
    )
    await self.tc.setup()

  async def test_a_backends_own_arguments_go_to_it(self):
    await self.tc.set_block_temperature([60.0], block_id=0)
    await self.tc.run_protocol(PCR, block_max_volume=25, block_id=1)
    self.assertEqual(self.served.blocks, [0, 1])
    self.assertEqual(self.served.ran, [PCR])

  async def test_what_a_backend_cannot_do_comes_back_as_it_was_raised(self):
    with self.assertRaisesRegex(AssertionError, "block_id must be specified"):
      await self.tc.set_block_temperature([60.0])
    with self.assertRaisesRegex(NotImplementedError, "cannot say whether its lid is open"):
      await self.tc.get_lid_open()


class LongCallTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    patcher = mock.patch.object(serve, "PROGRESS_INTERVAL", 0.01)
    patcher.start()
    self.addCleanup(patcher.stop)
    self.backend = _BlockBackend(speed=SPEED)
    self.served = serve._Served({"tc_1": self.backend})

  async def test_opening_the_lid_streams_until_it_is_open(self):
    await self.backend.close_lid()
    progress = [
      each async for each in self.served.open_lid(pb.OpenLidRequest(name="tc_1"), _Context())
    ]
    self.assertGreater(len(progress), 1)
    self.assertTrue(progress[-1].done)
    self.assertFalse(any(each.done for each in progress[:-1]))
    self.assertTrue(self.backend.lid_open)

  async def test_opening_the_lid_finishes_on_the_server_when_its_client_goes(self):
    progress = self.served.open_lid(pb.OpenLidRequest(name="tc_1"), _Context())
    self.assertFalse((await progress.__anext__()).done)
    await progress.aclose()
    self.assertFalse(self.backend.lid_open)
    for _ in range(100):
      if self.backend.lid_open:
        break
      await asyncio.sleep(0.02)
    self.assertTrue(self.backend.lid_open)

  async def test_a_run_finishes_on_the_server_when_its_client_goes(self):
    request = pb.RunProtocolRequest(
      name="tc_1",
      protocol=serve.protocol_to_proto(PCR),
      block_max_volume=25,
      backend_kwargs='{"block_id": 0}',
    )
    progress = self.served.run_protocol(request, _Context())
    self.assertFalse((await progress.__anext__()).done)
    await progress.aclose()
    self.assertEqual(self.backend.ran, [])
    self.assertEqual(len(self.served._running), 1)
    for _ in range(200):
      if self.backend.ran:
        break
      await asyncio.sleep(0.02)
    self.assertEqual(self.backend.ran, [PCR])
    self.assertEqual(self.backend.blocks, [0])

  async def test_a_run_that_waits_streams_until_its_end(self):
    remote = RemoteThermocyclerBackend("tc_1", ThermocyclerServer.local({"tc_1": self.backend}))
    await remote.run_protocol(PCR, 25, block_id=0)
    self.assertEqual(self.backend.ran, [PCR])


class CommandLineTests(unittest.TestCase):
  def test_a_thermocycler_is_named_with_its_backend(self):
    self.assertEqual(_named_backend("tc_1:odtc:192.168.1.20"), ("tc_1", ("odtc", "192.168.1.20")))
    self.assertEqual(_named_backend("tc_1"), ("tc_1", None))
    for text in ("tc_1:nope:192.168.1.20", "tc_1:odtc", ":odtc:192.168.1.20"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _named_backend(text)

  def test_simulation_serves_simulated_thermocyclers(self):
    args = argparse.Namespace(
      thermocycler=[("tc_1", None)], simulation=True, simulation_speed=2.0, simulation_zones=3
    )
    made = thermocyclers(args)["tc_1"]
    assert isinstance(made, ThermocyclerSimulatorBackend)
    self.assertEqual(made.num_zones, 3)
    args.simulation = False
    with self.assertRaises(SystemExit):
      thermocyclers(args)


if __name__ == "__main__":
  unittest.main()
