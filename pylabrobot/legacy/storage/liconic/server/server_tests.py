import asyncio
import importlib
import inspect
import unittest
from typing import Any, Callable, Dict, List, Tuple
from unittest import mock

from pylabrobot.legacy.storage import Incubator
from pylabrobot.legacy.storage.cytomat.racks import cytomat_rack_10mm_47
from pylabrobot.legacy.storage.liconic import ExperimentalLiconicBackend
from pylabrobot.legacy.storage.liconic.errors import (
  LiconicHandlerExportPlateError,
  LiconicHandlerGeneralError,
)
from pylabrobot.legacy.storage.liconic.racks import liconic_rack_17mm_22, liconic_rack_44mm_10
from pylabrobot.legacy.storage.liconic.server import LiconicServer, RemoteLiconicBackend
from pylabrobot.legacy.storage.liconic.server.__main__ import main
from pylabrobot.legacy.storage.liconic.server.v1 import liconic_pb2 as pb
from pylabrobot.legacy.storage.liconic.simulator import LiconicSimulator
from pylabrobot.legacy.storage.server.v1 import incubator_pb2 as ipb
from pylabrobot.resources import Coordinate, Plate, Well
from pylabrobot.resources.server.v1 import types_pb2 as tpb

serve = importlib.import_module("pylabrobot.legacy.storage.liconic.server.serve")
served_module = importlib.import_module("pylabrobot.legacy.storage.server.served")


def _plate(name: str) -> Plate:
  well = Well(name=f"{name}_A1", size_x=1, size_y=1, size_z=1).at(Coordinate(0, 0, 0))
  return Plate(name=name, size_x=127.76, size_y=85.48, size_z=14, ordered_items={"A1": well})


def _incubator(backend: ExperimentalLiconicBackend) -> Incubator:
  return Incubator(
    backend=backend,
    name="liconic",
    size_x=600,
    size_y=600,
    size_z=900,
    racks=[liconic_rack_17mm_22("cassette_1"), liconic_rack_44mm_10("cassette_2")],
    loading_tray_location=Coordinate(0, 0, 0),
  )


def _liconic(incubator: Incubator) -> ExperimentalLiconicBackend:
  assert isinstance(incubator.backend, ExperimentalLiconicBackend)
  return incubator.backend


def _ref(name: str, root: str = "") -> tpb.ResourceRef:
  return tpb.ResourceRef(name=tpb.NameRef(root=root, name=name))


class ParityTests(unittest.TestCase):
  def test_every_public_coroutine_is_a_call(self):
    remote = dict(inspect.getmembers(RemoteLiconicBackend, inspect.iscoroutinefunction))
    for name, method in inspect.getmembers(ExperimentalLiconicBackend, inspect.iscoroutinefunction):
      if name.startswith("_"):
        continue
      with self.subTest(name):
        self.assertTrue(remote[name].__qualname__.startswith("RemoteLiconicBackend."))
        self.assertEqual(
          inspect.signature(remote[name], eval_str=True), inspect.signature(method, eval_str=True)
        )


async def _session(incubator: Incubator, simulator: LiconicSimulator) -> List[Any]:
  """The same calls, on an incubator whose backend is in this process or served; what each
  returned. `simulator` is the simulated Liconic behind it, where the robot puts plates."""
  backend = _liconic(incubator)
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
  await incubator.take_in_plate(incubator.racks[0].sites[3], read_barcode=True)
  seen += [plate.parent.name if plate.parent else None, plate.barcode]
  plate.barcode = None
  fetched = await incubator.fetch_plate_to_loading_tray("plate_1", read_barcode=True)
  seen += [fetched is plate, plate.parent.name if plate.parent else None, plate.barcode]
  plate.unassign()
  simulator.transfer_station = False  # and took it away

  moved = _plate("moved")
  incubator.racks[1].sites[2].assign_child_resource(moved)
  simulator.load(1, 2)
  await attempt(lambda: backend.move_position_to_position(moved, incubator.racks[0].sites[9]))
  moved.unassign()  # the backend leaves moving it in the tree to the caller
  incubator.racks[0].sites[9].assign_child_resource(moved)
  await attempt(
    lambda: backend.move_position_to_position(moved, incubator.racks[1].sites[5], read_barcode=True)
  )
  seen.append(moved.barcode)
  await attempt(lambda: backend.read_barcode_inline(1, 3))
  await attempt(lambda: backend.scan_barcode(incubator.racks[1].sites[0]))
  await attempt(lambda: incubator.set_temperature(30.5))
  await attempt(incubator.get_temperature)
  await attempt(backend.get_target_temperature)
  await attempt(lambda: backend.set_humidity(0.85))
  await attempt(backend.get_humidity)
  await attempt(backend.get_target_humidity)
  await attempt(lambda: backend.set_co2_level(0.05))
  await attempt(backend.get_co2_level)
  await attempt(backend.get_target_co2_level)
  await attempt(lambda: backend.set_n2_level(0.9))
  await attempt(backend.get_n2_level)
  await attempt(backend.get_target_n2_level)
  await attempt(backend.shaker_status)
  await attempt(lambda: incubator.start_shaking(frequency=12.5))
  await attempt(backend.get_shaker_speed)
  await attempt(incubator.stop_shaking)
  await attempt(lambda: backend.start_shaking(80))
  await attempt(lambda: backend.turn_swap_station(home=False))
  await attempt(lambda: backend.turn_swap_station(home=True))
  await attempt(backend.check_shovel_sensor)
  await attempt(backend.check_transfer_sensor)
  await attempt(backend.check_second_transfer_sensor)
  await attempt(incubator.open_door)
  await attempt(incubator.close_door)
  await attempt(backend.initialize)
  moved.barcode = None
  await attempt(lambda: backend.move_position_to_position(moved, incubator.racks[1].sites[7], True))
  seen.append(moved.barcode)
  await attempt(backend.get_shaker_speed)
  await attempt(backend.initialize)
  await attempt(backend.get_shaker_speed)
  await incubator.stop()
  return seen


class SameAsInProcessTests(unittest.IsolatedAsyncioTestCase):
  async def test_a_served_liconic_does_what_one_in_this_process_does(self):
    local = LiconicSimulator()
    served = LiconicSimulator()
    remote = RemoteLiconicBackend(LiconicServer.local(served))
    in_process = await _session(_incubator(local), local)
    self.assertEqual(await _session(_incubator(remote), served), in_process)
    self.assertEqual(served.written, local.written)
    self.assertEqual(served.positions, local.positions)

  async def test_setup_refuses_another_model(self):
    remote = RemoteLiconicBackend(LiconicServer.local(LiconicSimulator()), model="STX110_IC")
    with self.assertRaisesRegex(ValueError, "STX44_IC"):
      await remote.setup()


class ErrorTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.local, self.served = LiconicSimulator(), LiconicSimulator()
    self.incubators = [
      _incubator(self.local),
      _incubator(RemoteLiconicBackend(LiconicServer.local(self.served))),
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

  async def test_an_empty_position_fails_as_the_plc_says(self):
    for incubator in self.incubators:
      incubator.racks[0].sites[2].assign_child_resource(_plate("ghost"))
    local, remote = await self._both(lambda i: i.fetch_plate_to_loading_tray("ghost"))
    self.assertIs(type(remote), LiconicHandlerExportPlateError)
    self.assertEqual(str(remote), str(local))

  async def test_an_occupied_transfer_station_is_refused(self):
    for incubator, simulator in zip(self.incubators, (self.local, self.served)):
      incubator.racks[0].sites[2].assign_child_resource(_plate("p"))
      simulator.load(0, 2)
      simulator.transfer_station = True
    local, remote = await self._both(lambda i: i.fetch_plate_to_loading_tray("p"))
    self.assertIs(type(remote), LiconicHandlerGeneralError)
    self.assertEqual(str(remote), str(local))

  async def test_python_errors_come_back_as_they_were_raised(self):
    cases: List[Tuple[Callable[[Incubator], Any], type]] = [
      (lambda i: i.start_shaking(frequency=90), ValueError),
      (lambda i: _liconic(i).shaker_status(), NotImplementedError),
      (lambda i: _liconic(i).scan_barcode(cytomat_rack_10mm_47("stray").sites[0]), ValueError),
    ]
    for incubator in self.incubators:
      incubator.racks[1].sites[0].assign_child_resource(_plate("taken"))
    cases.append(
      (
        lambda i: _liconic(i).move_position_to_position(
          i.racks[1].sites[0].resource,  # type: ignore[arg-type]
          i.racks[1].sites[0],
        ),
        RuntimeError,
      )
    )
    for call, cls in cases:
      local, remote = await self._both(call)
      with self.subTest(cls.__name__):
        self.assertIs(type(local), cls)
        self.assertIs(type(remote), cls)
        if cls is not ValueError:  # a stray site is refused by name on the server
          self.assertEqual(str(remote), str(local))

  async def test_a_liconic_with_no_climate_control_refuses_it(self):
    remote = RemoteLiconicBackend(LiconicServer.local(LiconicSimulator("STX44_NC")))
    with self.assertRaisesRegex(NotImplementedError, "Climate control"):
      await remote.get_temperature()

  async def test_a_barcode_needs_a_reader(self):
    remote = RemoteLiconicBackend(LiconicServer.local(LiconicSimulator(barcode_scanner=False)))
    with self.assertRaisesRegex(RuntimeError, "Barcode scanner not configured"):
      await remote.read_barcode_inline(1, 1)


class ResourceTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.simulator = LiconicSimulator()
    await self.simulator.setup()
    await self.simulator.set_racks([liconic_rack_17mm_22("c1"), liconic_rack_17mm_22("c2")])
    self.served = serve._Served(self.simulator)

  async def test_a_fetch_and_a_take_in_by_site_as_gatc_makes_them(self):
    self.simulator.load(1, 4)
    fetch = pb.FetchPlateToLoadingTrayRequest(
      plate=ipb.Plate(name="p", site=_ref("c2-4", root="c2")), read_barcode=True
    )
    last = [p async for p in self.served.fetch_plate_to_loading_tray(fetch, None)][-1]  # type: ignore[arg-type]
    self.assertTrue(last.done)
    self.assertEqual(last.barcode.data, "SIM-2-5")
    self.assertTrue(self.simulator.transfer_station)
    self.assertIsNone(self.simulator._racks[1].sites[4].resource)
    take_in = pb.TakeInPlateRequest(plate=ipb.Plate(name="p"), site=_ref("c1-0"))
    async for _ in self.served.take_in_plate(take_in, None):  # type: ignore[arg-type]
      pass
    self.assertEqual(self.simulator.positions, {(1, 1)})
    description = await self.served.describe(ipb.Empty(), None)  # type: ignore[arg-type]
    self.assertEqual([r.name for r in description.racks], ["c1", "c2"])
    self.assertEqual(description.racks[0].model, "liconic_rack_17mm_22")
    self.assertTrue(description.barcode_scanner)


class LongCallTests(unittest.IsolatedAsyncioTestCase):
  async def test_a_fetch_finishes_on_the_server_when_its_client_goes(self):
    patcher = mock.patch.object(served_module, "PROGRESS_INTERVAL", 0.01)
    patcher.start()
    self.addCleanup(patcher.stop)
    simulator = LiconicSimulator(move_time=0.1)
    await simulator.set_racks([liconic_rack_17mm_22("c1")])
    simulator.load(0, 0)
    served = serve._Served(simulator)
    request = pb.FetchPlateToLoadingTrayRequest(plate=ipb.Plate(name="p", site=_ref("c1-0")))
    progress = served.fetch_plate_to_loading_tray(request, None)  # type: ignore[arg-type]
    first = await progress.__anext__()
    self.assertFalse(first.done)
    await progress.aclose()  # type: ignore[attr-defined]
    self.assertFalse(simulator.transfer_station)
    await asyncio.sleep(0.4)
    self.assertTrue(simulator.transfer_station)
    self.assertEqual(simulator.written[-1], "ST 1903")


class CommandLineTests(unittest.TestCase):
  def test_the_simulation_is_served_with_its_racks(self):
    captured: Dict[str, Any] = {}

    async def fake_serve(backend, host, port):
      captured.update(backend=backend, port=port)

    main_module = importlib.import_module("pylabrobot.legacy.storage.liconic.server.__main__")
    with mock.patch.object(main_module, "serve", fake_serve):
      main(["--simulation", "--rack", "liconic_rack_17mm_22:c1", "--model", "STX110_IC"])
    backend = captured["backend"]
    self.assertIsInstance(backend, LiconicSimulator)
    self.assertEqual(captured["port"], 8093)
    self.assertEqual([r.name for r in backend._racks], ["c1"])
    self.assertEqual(backend.model.value, "STX110_IC")


if __name__ == "__main__":
  unittest.main()
