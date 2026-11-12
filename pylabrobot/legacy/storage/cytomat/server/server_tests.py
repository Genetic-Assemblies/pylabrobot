import asyncio
import importlib
import inspect
import unittest
from typing import Any, Callable, Dict, List, Tuple
from unittest import mock

from pylabrobot.legacy.storage import Incubator
from pylabrobot.legacy.storage.cytomat import CytomatBackend
from pylabrobot.legacy.storage.cytomat.errors import (
  CytomatNoMtpLoadedOnHandlerShovelError,
  CytomatTransferStationOccupiedError,
)
from pylabrobot.legacy.storage.cytomat.racks import cytomat_rack_10mm_47, cytomat_rack_23mm_21
from pylabrobot.legacy.storage.cytomat.server import CytomatServer, RemoteCytomatBackend
from pylabrobot.legacy.storage.cytomat.server.__main__ import main
from pylabrobot.legacy.storage.cytomat.server.v1 import cytomat_pb2 as pb
from pylabrobot.legacy.storage.cytomat.simulator import CytomatSimulator
from pylabrobot.legacy.storage.server.served import TaskLock
from pylabrobot.legacy.storage.server.v1 import incubator_pb2 as ipb
from pylabrobot.resources import Coordinate, Plate, Well
from pylabrobot.resources.server.v1 import types_pb2 as tpb

serve = importlib.import_module("pylabrobot.legacy.storage.cytomat.server.serve")
served_module = importlib.import_module("pylabrobot.legacy.storage.server.served")


def _plate(name: str) -> Plate:
  well = Well(name=f"{name}_A1", size_x=1, size_y=1, size_z=1).at(Coordinate(0, 0, 0))
  return Plate(name=name, size_x=127.76, size_y=85.48, size_z=14, ordered_items={"A1": well})


def _incubator(backend: CytomatBackend) -> Incubator:
  return Incubator(
    backend=backend,
    name="cytomat",
    size_x=860,
    size_y=550,
    size_z=900,
    racks=[cytomat_rack_10mm_47("rack_1"), cytomat_rack_23mm_21("rack_2")],
    loading_tray_location=Coordinate(0, 0, 0),
  )


def _cytomat(incubator: Incubator) -> CytomatBackend:
  assert isinstance(incubator.backend, CytomatBackend)
  return incubator.backend


def _ref(name: str, root: str = "") -> tpb.ResourceRef:
  return tpb.ResourceRef(name=tpb.NameRef(root=root, name=name))


class ParityTests(unittest.TestCase):
  def test_every_public_coroutine_is_a_call(self):
    remote = dict(inspect.getmembers(RemoteCytomatBackend, inspect.iscoroutinefunction))
    for name, method in inspect.getmembers(CytomatBackend, inspect.iscoroutinefunction):
      if name.startswith("_"):
        continue
      with self.subTest(name):
        self.assertTrue(remote[name].__qualname__.startswith("RemoteCytomatBackend."))
        self.assertEqual(
          inspect.signature(remote[name], eval_str=True), inspect.signature(method, eval_str=True)
        )


async def _session(incubator: Incubator, simulator: CytomatSimulator) -> List[Any]:
  """The same calls, on an incubator whose backend is in this process or served; what each
  returned. `simulator` is the simulated Cytomat behind it, where the robot puts plates."""
  backend: CytomatBackend = incubator.backend  # type: ignore[assignment]
  seen: List[Any] = []

  async def attempt(call: Callable[[], Any]) -> None:
    try:
      seen.append(await call())
    except Exception as error:
      seen.append((type(error), str(error)))

  await incubator.setup()
  seen.append(backend.model)
  plate = _plate("plate_1")
  incubator.loading_tray.assign_child_resource(plate)
  simulator.transfer_station = True  # the robot put it there
  await incubator.take_in_plate(incubator.racks[1].sites[3])
  seen.append(plate.parent.name if plate.parent else None)
  fetched = await incubator.fetch_plate_to_loading_tray("plate_1")
  seen += [fetched is plate, plate.parent.name if plate.parent else None]
  plate.unassign()
  simulator.transfer_station = False  # and took it away
  await attempt(incubator.get_temperature)
  await attempt(incubator.open_door)
  await attempt(incubator.close_door)
  await attempt(lambda: incubator.start_shaking(frequency=10.0))
  await attempt(incubator.stop_shaking)
  await attempt(lambda: incubator.set_temperature(37))

  site, other = incubator.racks[0].sites[0], incubator.racks[0].sites[46]
  simulator.load(0, 0)
  await attempt(backend.get_overview_register)
  await attempt(backend.get_warning_register)
  await attempt(backend.get_error_register)
  await attempt(backend.get_action_register)
  await attempt(backend.get_swap_register)
  await attempt(backend.get_sensor_register)
  await attempt(lambda: backend.action_storage_to_wait(site))
  await attempt(backend.action_wait_to_exposed)
  await attempt(backend.action_exposed_to_wait)
  await attempt(lambda: backend.action_wait_to_storage(other))
  await attempt(lambda: backend.action_storage_to_exposed(other))
  await attempt(lambda: backend.action_exposed_to_storage(site))
  await attempt(lambda: backend.action_storage_to_transfer(site))
  await attempt(backend.action_transfer_to_wait)
  await attempt(backend.action_wait_to_transfer)
  await attempt(lambda: backend.action_transfer_to_storage(other))
  await attempt(lambda: backend.action_read_barcode("001", "047"))
  await attempt(backend.shovel_out)
  await attempt(backend.shovel_in)
  await attempt(backend.init_shakers)
  await attempt(lambda: backend.set_shaking_frequency(12, shakers=[2]))
  await attempt(lambda: backend.get_incubation_query("ih"))
  await attempt(backend.get_co2)
  await attempt(backend.get_humidity)
  await attempt(backend.get_o2)
  await attempt(lambda: backend.send_command("ch", "bs", ""))
  await attempt(lambda: backend.send_action("ll", "gp", "002"))
  await attempt(backend.wait_for_task_completion)
  await attempt(lambda: backend.wait_for_transfer_station(occupied=False))
  await attempt(backend.reset_error_register)
  await attempt(backend.initialize)
  await attempt(lambda: backend.send_command("xx", "yy", ""))
  await incubator.stop()
  return seen


class SameAsInProcessTests(unittest.IsolatedAsyncioTestCase):
  async def test_a_served_cytomat_does_what_one_in_this_process_does(self):
    local = CytomatSimulator()
    served = CytomatSimulator()
    remote = RemoteCytomatBackend(CytomatServer.local(served))
    in_process = await _session(_incubator(local), local)
    self.assertEqual(await _session(_incubator(remote), served), in_process)
    self.assertEqual(served.written, local.written)
    self.assertEqual(served.locations, local.locations)
    self.assertEqual([r.name for r in served._racks], ["rack_1", "rack_2"])

  async def test_setup_refuses_another_model(self):
    remote = RemoteCytomatBackend(CytomatServer.local(CytomatSimulator()), model="C2C_425")
    with self.assertRaisesRegex(ValueError, "C6000"):
      await remote.setup()


class ErrorTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.local, self.served = CytomatSimulator(), CytomatSimulator()
    self.incubators = [
      _incubator(self.local),
      _incubator(RemoteCytomatBackend(CytomatServer.local(self.served))),
    ]
    for incubator in self.incubators:
      await incubator.setup()

  async def _both(self, call: Callable[[Incubator], Any]) -> Tuple[BaseException, BaseException]:
    raised = []
    for incubator in self.incubators:
      with self.assertRaises(Exception) as caught:
        await call(incubator)
      raised.append(caught.exception)
    return raised[0], raised[1]

  async def test_an_empty_site_fails_as_the_device_says(self):
    for incubator in self.incubators:
      incubator.racks[0].sites[2].assign_child_resource(_plate("ghost"))
    local, remote = await self._both(lambda i: i.fetch_plate_to_loading_tray("ghost"))
    self.assertIs(type(remote), CytomatNoMtpLoadedOnHandlerShovelError)
    self.assertEqual(str(remote), str(local))

  async def test_an_occupied_transfer_station_is_refused(self):
    for incubator, simulator in zip(self.incubators, (self.local, self.served)):
      incubator.racks[0].sites[2].assign_child_resource(_plate("p"))
      simulator.load(0, 2)
      simulator.transfer_station = True
    local, remote = await self._both(lambda i: i.fetch_plate_to_loading_tray("p"))
    self.assertIs(type(remote), CytomatTransferStationOccupiedError)
    self.assertEqual(str(remote), str(local))

  async def test_python_errors_come_back_as_they_were_raised(self):
    local, remote = await self._both(lambda i: i.set_temperature(37))
    self.assertIs(type(remote), NotImplementedError)
    self.assertEqual(str(remote), str(local))
    query: Any = "zz"
    local, remote = await self._both(lambda i: _cytomat(i).get_incubation_query(query))
    self.assertIs(type(remote), type(local))

  async def test_a_site_not_in_its_racks_is_refused(self):
    stray = cytomat_rack_10mm_47("stray")
    local, remote = await self._both(lambda i: _cytomat(i).action_storage_to_wait(stray.sites[0]))
    self.assertIs(type(local), ValueError)
    self.assertIs(type(remote), ValueError)
    self.assertIn("no site 'stray-1' in rack 'stray'", str(remote))


class ResourceTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.simulator = CytomatSimulator()
    await self.simulator.setup()
    await self.simulator.set_racks([cytomat_rack_10mm_47("rack_1"), cytomat_rack_10mm_47("rack_2")])
    self.served = serve._Served(self.simulator)

  def test_a_site_is_named_in_its_rack(self):
    self.assertIs(
      self.served.site(_ref("rack_2-3", root="rack_2")), self.simulator._racks[1].sites[2]
    )
    self.assertIs(self.served.site(_ref("rack_2-3")), self.simulator._racks[1].sites[2])
    with self.assertRaisesRegex(ValueError, "no site 'rack_2-3' in rack 'rack_1'"):
      self.served.site(_ref("rack_2-3", root="rack_1"))
    with self.assertRaisesRegex(ValueError, "by name"):
      self.served.site(tpb.ResourceRef(id=b"\x01"))

  async def test_a_fetch_and_a_take_in_by_site_as_gatc_makes_them(self):
    self.simulator.load(1, 2)
    fetch = pb.PlateRequest(plate=ipb.Plate(name="p", site=_ref("rack_2-3", root="rack_2")))
    last = [p async for p in self.served.fetch_plate_to_loading_tray(fetch, None)][-1]  # type: ignore[arg-type]
    self.assertTrue(last.done)
    self.assertTrue(self.simulator.transfer_station)
    self.assertEqual(self.simulator.written[-2:], ["mv:st 050", "ch:bs"])
    # The server holds no plates: nothing is left in the site.
    self.assertIsNone(self.simulator._racks[1].sites[2].resource)
    take_in = pb.TakeInPlateRequest(plate=ipb.Plate(name="p"), site=_ref("rack_1-1"))
    async for _ in self.served.take_in_plate(take_in, None):  # type: ignore[arg-type]
      pass
    self.assertEqual(self.simulator.locations, {"001"})

  async def test_racks_a_client_sends_replace_the_servers(self):
    request = ipb.SetRacksRequest(racks=[])
    from pylabrobot.legacy.storage.server.remote import racks_request

    rack = cytomat_rack_23mm_21("only")
    rack.sites[0].assign_child_resource(_plate("left_out"))
    request = racks_request([rack])
    await self.served.set_racks(request, None)  # type: ignore[arg-type]
    description = await self.served.describe(ipb.Empty(), None)  # type: ignore[arg-type]
    self.assertEqual([r.name for r in description.racks], ["only"])
    self.assertEqual(len(description.racks[0].sites), 21)
    self.assertEqual(description.racks[0].sites[0].name, "only-1")
    self.assertIsNone(self.simulator._racks[0].sites[0].resource)


class LongCallTests(unittest.IsolatedAsyncioTestCase):
  async def test_a_fetch_finishes_on_the_server_when_its_client_goes(self):
    patcher = mock.patch.object(served_module, "PROGRESS_INTERVAL", 0.01)
    patcher.start()
    self.addCleanup(patcher.stop)
    simulator = CytomatSimulator(move_time=0.1)
    await simulator.set_racks([cytomat_rack_10mm_47("rack_1")])
    simulator.load(0, 0)
    served = serve._Served(simulator)
    request = pb.PlateRequest(plate=ipb.Plate(name="p", site=_ref("rack_1-1")))
    progress = served.fetch_plate_to_loading_tray(request, None)  # type: ignore[arg-type]
    first = await progress.__anext__()
    self.assertFalse(first.done)
    await progress.aclose()  # type: ignore[attr-defined]
    self.assertFalse(simulator.transfer_station)
    await asyncio.sleep(0.3)
    self.assertTrue(simulator.transfer_station)
    self.assertEqual(simulator.locations, set())

  async def test_a_wait_is_dropped_when_its_client_goes(self):
    patcher = mock.patch.object(served_module, "PROGRESS_INTERVAL", 0.01)
    patcher.start()
    self.addCleanup(patcher.stop)
    simulator = CytomatSimulator()
    served = serve._Served(simulator)
    request = pb.WaitForTransferStationRequest(occupied=True)
    progress = served.wait_for_transfer_station(request, None)  # type: ignore[arg-type]
    await progress.__anext__()
    await progress.aclose()  # type: ignore[attr-defined]
    await asyncio.sleep(0.01)
    asked = len(simulator.written)
    await asyncio.sleep(1.2)
    self.assertEqual(len(simulator.written), asked)

  async def test_commands_wait_for_the_one_before(self):
    lock = TaskLock()
    order: List[str] = []

    async def holder(name: str) -> None:
      async with lock:
        async with lock:  # the same task may take it again
          order.append(f"{name} in")
          await asyncio.sleep(0.01)
          order.append(f"{name} out")

    await asyncio.gather(holder("a"), holder("b"))
    self.assertEqual(order, ["a in", "a out", "b in", "b out"])


class CommandLineTests(unittest.TestCase):
  def test_an_unknown_rack_is_refused(self):
    with mock.patch.object(serve, "serve") as served, self.assertRaisesRegex(ValueError, "no rack"):
      main(["--simulation", "--rack", "nothing:rack_1"])
    served.assert_not_called()

  def test_the_simulation_is_served_with_its_racks(self):
    captured: Dict[str, Any] = {}

    async def fake_serve(backend, host, port):
      captured.update(backend=backend, port=port)

    main_module = importlib.import_module("pylabrobot.legacy.storage.cytomat.server.__main__")
    with mock.patch.object(main_module, "serve", fake_serve):
      main(["--simulation", "--rack", "cytomat_rack_10mm_47:rack_1", "--model", "C6002"])
    backend = captured["backend"]
    self.assertIsInstance(backend, CytomatSimulator)
    self.assertEqual(captured["port"], 8092)
    self.assertEqual([r.name for r in backend._racks], ["rack_1"])
    self.assertFalse(backend.strict_transfer_station)


if __name__ == "__main__":
  unittest.main()
