import asyncio
import importlib
import inspect
import unittest
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest import mock

from pylabrobot.high_res.sample_storage import (
  HighResSampleStorageError,
  HighResSampleStorageFault,
  NoFreeSiteError,
  PlateNotFoundError,
  TundraStore,
)
from pylabrobot.high_res.sample_storage.driver import HighResSampleStorage
from pylabrobot.high_res.sample_storage.driver.environment import EnvironmentControl
from pylabrobot.high_res.sample_storage.server import (
  RemoteEnvironmentControl,
  RemoteTundraStore,
  SampleStorageServer,
)
from pylabrobot.high_res.sample_storage.server.v1 import sample_storage_pb2 as pb
from pylabrobot.high_res.sample_storage.simulator import SampleStorageSimulator
from pylabrobot.resources import Coordinate, Plate, ResourceNotFoundError, Well
from pylabrobot.resources.server.v1 import types_pb2 as tpb

# The module, which the package's `serve` function shadows.
serve = importlib.import_module("pylabrobot.high_res.sample_storage.server.serve")


def _plate(name: str, size_z: float = 14.0) -> Plate:
  well = Well(name=f"{name}_A1", size_x=1, size_y=1, size_z=1).at(Coordinate(0, 0, 0))
  return Plate(name=name, size_x=127.76, size_y=85.48, size_z=size_z, ordered_items={"A1": well})


def _simulated(name: str = "tundra", nests: int = 2) -> Tuple[TundraStore, SampleStorageSimulator]:
  store = TundraStore(host="simulation", name=name)
  simulator = SampleStorageSimulator(nests=nests)
  store.io = simulator  # type: ignore[assignment]
  return store, simulator


class _Context:
  """What a handler is given, with its response headers."""

  def __init__(self) -> None:
    self.response_headers: Dict[str, str] = {}


def _public_coroutines(cls: type) -> Dict[str, Any]:
  return {
    name: method
    for name, method in inspect.getmembers(cls, inspect.iscoroutinefunction)
    if not name.startswith("_")
  }


class ParityTests(unittest.TestCase):
  def test_every_public_coroutine_is_a_call(self):
    for local, remote in (
      (TundraStore, RemoteTundraStore),
      (EnvironmentControl, RemoteEnvironmentControl),
    ):
      served = _public_coroutines(remote)
      for name, method in _public_coroutines(local).items():
        with self.subTest(f"{local.__name__}.{name}"):
          self.assertTrue(served[name].__qualname__.startswith(f"{remote.__name__}."))
          self.assertEqual(
            inspect.signature(served[name], eval_str=True), inspect.signature(method, eval_str=True)
          )

  def test_it_is_a_tundra_store(self):
    store = RemoteTundraStore("tundra", sample_storage_server=SampleStorageServer("http://x"))
    self.assertIsInstance(store, TundraStore)
    self.assertIsInstance(store, HighResSampleStorage)


async def _session(store: TundraStore, arm: Callable[[int, bool], None]) -> List[Any]:
  """The same calls, made on a store in this process or a served one; what each returned.

  Args:
    arm: what the robot that loads the nests does to the simulated store when a plate is put on a
      nest, or taken off one, by hand: its nest number and whether it holds a plate now. A served
      store's server does that itself.
  """
  seen: List[Any] = []
  await store.setup(home=True)
  seen.append([r.name for r in store.racks])
  seen.append([n.name for n in store.nests])
  seen.append(await store.request_version())
  seen.append(await store.request_environment())
  seen.append(await store.request_axis_positions())
  seen.append(await store.request_is_homed())
  seen.append(await store.request_door_status())
  seen.append(await store.request_nest_status())
  seen.append(await store.request_spatula_is_holding())
  seen.append(await store.request_nest_is_holding(1))
  seen.append(await store.request_stacker_dimensions())
  seen.append((await store.request_settings()).machine_type)
  seen.append(await store.request_stacker_barcodes(1, 2))
  seen.append(await store.request_stacker_barcodes("all"))
  seen.append(await store.request_is_parked())

  plate = _plate("plate_1")
  store.nests[0].assign_child_resource(plate)
  arm(1, True)
  taken = await store.take_in_plate(0, store.racks[0].sites[4])
  seen += [taken is plate, plate.parent.name if plate.parent else None]
  fetched = await store.fetch_plate_to_loading_tray("plate_1", 1)
  seen += [fetched is plate, plate.parent.name if plate.parent else None]
  moved = await store.transfer_plate_between_nests(1, 0)
  seen += [moved is plate, plate.parent.name if plate.parent else None]
  await store.store_plate(plate, store.racks[1].sites[0], 0)
  seen.append(plate.parent.name if plate.parent else None)
  seen.append(store.get_site_by_plate_name("plate_1").name)
  seen.append(store.get_num_free_sites())
  fetched = await store.fetch_plate_to_loading_tray(plate, 0)
  seen.append(fetched is plate)
  plate.unassign()  # the arm takes it
  arm(1, False)
  seen.append(await store.request_nest_status())

  short = _plate("plate_2", size_z=10)
  store.nests[1].assign_child_resource(short)
  arm(2, True)
  await store.take_in_plate(1)
  seen.append(short.parent.name if short.parent else None)

  await store.open_all_doors()
  seen.append(await store.request_door_status())
  await store.close_all_doors()
  await store.clear_abort()
  seen.append(await store.recover())

  environment = store.environment
  await environment.set_temperature(-10.0)
  await environment.start_temperature_control()
  await environment.stop_temperature_control()
  seen.append(await environment.request_current_temperature())
  seen.append(await environment.request_target_temperature())
  await environment.set_humidity(0.4)
  await environment.start_humidity_control()
  await environment.stop_humidity_control()
  seen.append(await environment.request_current_humidity())
  seen.append(await environment.request_target_humidity())
  seen.append(await environment.request_tank_pressures())
  seen.append(await environment.refresh())
  seen.append(environment.parameters)
  seen.append(environment.supports_humidity_control)
  for call in (environment.set_co2(0.05), environment.request_current_o2()):
    try:
      await call
    except Exception as error:  # what it raises is part of what is compared
      seen.append((type(error), str(error)))
  return seen


class SameAsInProcessTests(unittest.IsolatedAsyncioTestCase):
  async def test_a_served_store_does_what_one_in_this_process_does(self):
    local, local_simulator = _simulated()
    served, served_simulator = _simulated()
    remote = RemoteTundraStore("tundra", sample_storage_server=SampleStorageServer.local(served))
    in_process = await _session(local, local_simulator.nests.__setitem__)
    self.assertEqual(await _session(remote, lambda nest, held: None), in_process)
    self.assertEqual(served_simulator.written, local_simulator.written)
    self.assertEqual(served_simulator.slots, local_simulator.slots)

  async def test_a_second_client_takes_up_what_the_first_did(self):
    served, _ = _simulated()
    server = SampleStorageServer.local(served)
    first = RemoteTundraStore("tundra", sample_storage_server=server)
    second = RemoteTundraStore(
      "tundra", sample_storage_server=SampleStorageServer.local(served, set_up=True)
    )
    await first.setup(home=True)
    first.nests[0].assign_child_resource(_plate("p"))
    await first.take_in_plate(0)
    self.assertEqual(await second.request_is_homed(), True)
    self.assertEqual(second.get_site_by_plate_name("p").name, "tundra_stacker_1_slot_1")


class ErrorTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.local, self.local_simulator = _simulated()
    self.served, self.simulator = _simulated()
    self.remote = RemoteTundraStore(
      "tundra", sample_storage_server=SampleStorageServer.local(self.served)
    )
    for store in (self.local, self.remote):
      await store.setup(home=True)

  async def _both(self, call) -> Tuple[BaseException, BaseException]:
    raised = []
    for store in (self.local, self.remote):
      with self.assertRaises(Exception) as caught:
        await call(store)
      raised.append(caught.exception)
    return raised[0], raised[1]

  async def test_an_empty_slot_is_plate_not_found_with_the_devices_lines(self):
    for store, simulator in ((self.local, self.local_simulator), (self.remote, self.simulator)):
      store.racks[0].sites[2].assign_child_resource(_plate("ghost"))
    await self.remote.request_is_homed()  # the hand placement reaches the server
    self.local_simulator.slots.clear()
    self.simulator.slots.clear()
    local, remote = await self._both(lambda s: s.fetch_plate_to_loading_tray("ghost", 0))
    self.assertIs(type(remote), PlateNotFoundError)
    self.assertEqual(str(remote), str(local))
    self.assertEqual(remote.command, local.command)  # type: ignore[attr-defined]
    self.assertEqual(remote.error_lines, local.error_lines)  # type: ignore[attr-defined]
    self.assertIsNone(self.remote.unresolved_transfer)
    self.assertEqual(self.remote.get_site_by_plate_name("ghost").name, "tundra_stacker_1_slot_3")

  async def test_a_fault_leaves_the_transfer_unresolved_until_it_is_resolved(self):
    ghost = _plate("ghost")
    self.remote.racks[0].sites[23].assign_child_resource(ghost)
    await self.remote.request_is_homed()
    self.simulator.slots.clear()  # the top slot is empty after all
    with self.assertRaises(HighResSampleStorageFault) as caught:
      await self.remote.fetch_plate_to_loading_tray(ghost, 0)
    self.assertIsInstance(caught.exception, HighResSampleStorageError)
    self.assertIn("call recover()", str(caught.exception))
    transfer = self.remote.unresolved_transfer
    assert transfer is not None
    self.assertIs(transfer.plate, ghost)
    self.assertIs(transfer.source, self.remote.racks[0].sites[23])
    self.assertIs(transfer.destination, self.remote.nests[0])
    with self.assertRaisesRegex(RuntimeError, "unresolved"):
      await self.remote.home()
    self.assertTrue(await self.remote.recover())
    resolved = await self.remote.resolve_unresolved_transfer("unassigned")
    self.assertIs(resolved, ghost)
    self.assertIsNone(ghost.parent)
    self.assertIsNone(self.remote.unresolved_transfer)
    self.assertIsNone(self.served.unresolved_transfer)

  async def test_python_errors_come_back_as_they_were_raised(self):
    cases = [
      (lambda s: s.fetch_plate_to_loading_tray("nothing", 0), ResourceNotFoundError),
      (lambda s: s.take_in_plate(5), ValueError),
      (lambda s: s.take_in_plate(0), ResourceNotFoundError),
      (lambda s: s.transfer_plate_between_nests(0, 0), ValueError),
      (lambda s: s.resolve_unresolved_transfer("source"), RuntimeError),
      (lambda s: s.environment.set_temperature(30), ValueError),
      (lambda s: s.environment.set_co2(0.05), NotImplementedError),
    ]
    for call, cls in cases:
      local, remote = await self._both(call)
      with self.subTest(cls.__name__):
        self.assertIs(type(local), cls)
        self.assertIs(type(remote), cls)
        self.assertEqual(str(remote), str(local))

  async def test_no_free_site(self):
    for store in (self.local, self.remote):
      store.nests[0].assign_child_resource(_plate("tall", size_z=100))
    local, remote = await self._both(lambda s: s.take_in_plate(0))
    self.assertIs(type(remote), NoFreeSiteError)
    self.assertEqual(str(remote), str(local))

  async def test_a_refused_placement_puts_the_tree_back_as_the_server_has_it(self):
    self.remote.nests[0].assign_child_resource(_plate("p"))
    await self.remote.take_in_plate(0, self.remote.racks[0].sites[0])
    # Another plate is put in the same slot here, which the server's tree says is taken.
    self.served.racks[0].sites[1].assign_child_resource(_plate("q"))
    self.remote.racks[0].sites[1].assign_child_resource(_plate("r"))
    with self.assertRaisesRegex(ValueError, "holds 'q'"):
      await self.remote.request_is_homed()
    self.assertEqual(self.remote.racks[0].sites[1].resource.name, "q")  # type: ignore[union-attr]


class ResourceTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.store, self.simulator = _simulated()
    await self.store.setup(home=True)
    self.served = serve._Served(self.store, set_up=True)

  def _name(self, name: str, root: str = "") -> tpb.ResourceRef:
    return tpb.ResourceRef(name=tpb.NameRef(root=root, name=name))

  async def test_a_placement_by_name_makes_the_plate_where_it_says(self):
    placement = pb.Placement(
      holder=self._name("tundra_stacker_2_slot_3", root="tundra"),
      plate=pb.PlateDefinition(name="from_gatc", size_z=15),
    )
    await self.served.place_plates(pb.PlacePlatesRequest(placements=[placement]), _Context())  # type: ignore[arg-type]
    site = self.store.get_site_by_plate_name("from_gatc")
    self.assertEqual(site.name, "tundra_stacker_2_slot_3")
    self.assertEqual(site.resource.get_size_z(), 15)  # type: ignore[union-attr]
    self.assertIn((2, 3), self.simulator.slots)
    definition = await self.served.get_plate(self._name("from_gatc"), _Context())  # type: ignore[arg-type]
    self.assertEqual(definition.name, "from_gatc")
    description = await self.served.describe(pb.Empty(), _Context())  # type: ignore[arg-type]
    slot = description.stackers[1].sites[2]
    self.assertEqual(
      (slot.name, slot.slot, slot.plate), ("tundra_stacker_2_slot_3", 3, "from_gatc")
    )
    self.assertEqual([n.name for n in description.nests], ["tundra_nest_1", "tundra_nest_2"])

  async def test_a_fetch_names_the_plate_and_a_take_in_its_slot(self):
    self.store.racks[0].sites[0].assign_child_resource(_plate("p"))
    self.simulator.load(1, 1)
    request = pb.FetchPlateToLoadingTrayRequest(plate=self._name("p"), tray_index=0)
    last = [p async for p in self.served.fetch_plate_to_loading_tray(request, _Context())][-1]  # type: ignore[arg-type]
    self.assertTrue(last.done)
    self.assertEqual(last.plate, "p")
    self.assertEqual(self.simulator.nests[1], True)
    take_in = pb.TakeInPlateRequest(tray_index=0, holder=self._name("tundra_stacker_1_slot_5"))
    async for _ in self.served.take_in_plate(take_in, _Context()):  # type: ignore[arg-type]
      pass
    self.assertEqual(self.store.get_site_by_plate_name("p").name, "tundra_stacker_1_slot_5")

  def test_references_resolve_by_name_in_the_stores_tree_only(self):
    self.assertIs(self.served.resolve(self._name("tundra_nest_1")), self.store.nests[0])
    self.assertIs(self.served.resolve(self._name("tundra", root="")), self.store)
    with self.assertRaisesRegex(ValueError, "not this server's store"):
      self.served.resolve(self._name("tundra_nest_1", root="other"))
    with self.assertRaisesRegex(ValueError, "by name"):
      self.served.resolve(tpb.ResourceRef(id=b"\x01" * 16))
    with self.assertRaises(ResourceNotFoundError):
      self.served.resolve(self._name("nowhere"))
    with self.assertRaisesRegex(ValueError, "not a nest or a stacker slot"):
      self.served._holder(self._name("tundra_stacker_1"))


class _SlowSimulator(SampleStorageSimulator):
  """Takes a while over a pick."""

  async def write(self, data: bytes, timeout: Optional[float] = None) -> None:
    if data.startswith(b"pick"):
      await asyncio.sleep(0.1)
    await super().write(data, timeout)


class LongCallTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    patcher = mock.patch.object(serve, "PROGRESS_INTERVAL", 0.01)
    patcher.start()
    self.addCleanup(patcher.stop)
    self.store = TundraStore(host="simulation", name="tundra")
    self.simulator = _SlowSimulator()
    self.store.io = self.simulator  # type: ignore[assignment]
    await self.store.setup(home=True)
    self.store.racks[0].sites[0].assign_child_resource(_plate("p"))
    self.simulator.load(1, 1)

  async def test_a_fetch_streams_until_it_is_done(self):
    remote = RemoteTundraStore(
      "tundra", sample_storage_server=SampleStorageServer.local(self.store, set_up=True)
    )
    plate = await remote.fetch_plate_to_loading_tray("p", 0)
    self.assertIs(plate.parent, remote.nests[0])

  async def test_a_fetch_finishes_on_the_server_when_its_client_goes(self):
    served = serve._Served(self.store, set_up=True)
    request = pb.FetchPlateToLoadingTrayRequest(
      plate=tpb.ResourceRef(name=tpb.NameRef(name="p")), tray_index=0
    )
    progress = served.fetch_plate_to_loading_tray(request, _Context())  # type: ignore[arg-type]
    first = await progress.__anext__()
    self.assertFalse(first.done)
    await progress.aclose()  # type: ignore[attr-defined]
    self.assertFalse(self.simulator.nests[1])
    await asyncio.sleep(0.3)
    self.assertTrue(self.simulator.nests[1])
    self.assertIs(self.store.get_resource("p").parent, self.store.nests[0])


if __name__ == "__main__":
  unittest.main()
