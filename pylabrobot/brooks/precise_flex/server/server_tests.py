"""A PreciseFlex driven through a PreciseFlex server: the same API and the same answers as one in
this process, what the server keeps, and what it refuses."""

import asyncio
import importlib
import inspect
import json
import os
import shutil
import tempfile
import unittest
from typing import Any, Dict, List, Tuple
from unittest import mock

from connectrpc.code import Code
from connectrpc.errors import ConnectError

from pylabrobot.brooks.precise_flex import PreciseFlexAxis as A
from pylabrobot.brooks.precise_flex.device import RECORDING_PF400, PreciseFlex400
from pylabrobot.brooks.precise_flex.driver.errors import (
  OutOfRangeOfMotionError,
  PreciseFlexCollisionError,
  PreciseFlexError,
)
from pylabrobot.brooks.precise_flex.driver.simulator import PreciseFlexSimulationDriver
from pylabrobot.brooks.precise_flex.kinematics import IKError, PreciseFlexCartesianPose
from pylabrobot.brooks.precise_flex.server import client, generate, wire
from pylabrobot.brooks.precise_flex.server.client import PreciseFlexServer
from pylabrobot.brooks.precise_flex.server.description import read_settings
from pylabrobot.brooks.precise_flex.server.errors import from_connect_error, to_connect_error
from pylabrobot.brooks.precise_flex.server.v1 import positions_pb2 as ppb
from pylabrobot.brooks.precise_flex.server.v1 import rail_pb2
from pylabrobot.brooks.precise_flex.server.v1 import types_pb2 as tpb
from pylabrobot.resources.coordinate import Coordinate
from pylabrobot.resources.rotation import Rotation
from pylabrobot.resources.server.client import ResourceServer

# The modules, which the package's functions of the same names shadow.
serve = importlib.import_module("pylabrobot.brooks.precise_flex.server.serve")
positions = importlib.import_module("pylabrobot.brooks.precise_flex.server.positions")
command_line = importlib.import_module("pylabrobot.brooks.precise_flex.server.__main__")

_REMOTE = {
  "PreciseFlexService": client.RemotePreciseFlexDevice,
  "DriverService": client.RemotePreciseFlexDriver,
  "ArmService": client.RemotePreciseFlexArm,
  "GripperService": client.RemotePreciseFlexGripper,
  "RailService": client.RemotePreciseFlexRail,
  "VisionService": client.RemotePreciseFlexVision,
}

# Two places a plate sits, clear of the column and the base plate on the way from the fold.
HOTEL = {A.BASE: 100.0, A.SHOULDER: 30.0, A.ELBOW: 120.0, A.WRIST: 210.0}
NEST = {A.BASE: 150.0, A.SHOULDER: -30.0, A.ELBOW: 240.0, A.WRIST: 150.0}
PLATE: Dict[str, Any] = {"width": 85.5, "height": 10.0, "plate_height": 14.5}


def _railed_configuration(directory: str) -> str:
  """A declared PreciseFlex 400 on a rail, as a file."""
  with open(RECORDING_PF400, encoding="utf-8") as f:
    saved = json.load(f)
  saved["rail"] = {"soft_limit_range": [0.0, 2000.0]}
  path = os.path.join(directory, "pf400_rail.json")
  with open(path, "w", encoding="utf-8") as f:
    json.dump(saved, f)
  return path


def _plain(value: Any) -> Any:
  """A value as plain data, to compare: a rotation is equal only to itself."""
  if isinstance(value, Rotation):
    return ("Rotation", value.x, value.y, value.z)
  if isinstance(value, dict):
    return {key: _plain(item) for key, item in value.items()}
  if isinstance(value, (list, tuple)):
    return [_plain(item) for item in value]
  if hasattr(value, "__dict__"):
    return (type(value).__name__, _plain(vars(value)))
  return value


def _simulated(device: Any) -> Any:
  driver = device.driver
  assert isinstance(driver, PreciseFlexSimulationDriver)
  return driver._simulated_arm


class GeneratedTests(unittest.TestCase):
  def test_the_generated_files_are_what_the_generator_writes(self):
    for path, text in generate.outputs().items():
      with self.subTest(path=os.path.basename(path)), open(path, encoding="utf-8") as f:
        self.assertEqual(f.read(), text, "run `make generate-rpc`")

  def test_every_method_is_served_with_its_own_signature(self):
    for service in generate.SERVICES:
      cls = service.cls
      remote = dict(inspect.getmembers(_REMOTE[service.name]))
      own = dict(inspect.getmembers(cls))
      served = {rpc.python for rpc in generate.rpcs(service)}
      for name in generate.served_methods(cls):
        with self.subTest(method=f"{cls.__name__}.{name}"):
          self.assertIn(name, served)
          self.assertIsNot(remote[name], own[name])
          self.assertEqual(
            [
              (p.name, p.kind, p.default)
              for p in inspect.signature(remote[name]).parameters.values()
            ],
            [(p.name, p.kind, p.default) for p in inspect.signature(own[name]).parameters.values()],
          )
          self.assertEqual(remote[name].__doc__, own[name].__doc__)

  def test_the_deprecated_aliases_are_inherited_and_not_served(self):
    remote = client.RemotePreciseFlexDriver
    for name in ("move_gripper", "request_joint_position", "move_rail", "set_payload"):
      with self.subTest(method=name):
        self.assertNotIn(name, generate.served_methods(generate.SERVICES[1].cls))
        self.assertIs(getattr(remote, name), getattr(generate.SERVICES[1].cls, name))

  def test_the_remote_classes_are_plrs(self):
    from pylabrobot.brooks.precise_flex import (
      PreciseFlexArm,
      PreciseFlexDevice,
      PreciseFlexDriver,
      PreciseFlexGripper,
    )

    for remote, plr in (
      (client.RemotePreciseFlexDevice, PreciseFlexDevice),
      (client.RemotePreciseFlexDriver, PreciseFlexDriver),
      (client.RemotePreciseFlexArm, PreciseFlexArm),
      (client.RemotePreciseFlexGripper, PreciseFlexGripper),
    ):
      self.assertTrue(issubclass(remote, plr))


class WireTests(unittest.TestCase):
  def test_values_go_over_and_come_back_as_they_were(self):
    pose = PreciseFlexCartesianPose(
      location=Coordinate(1.0, 2.0, 3.0),
      rotation=Rotation(0.0, 0.0, 90.0),
      rail_position=5.0,
      orientation="left",
      wrist="cw",
    )
    cases: List[Tuple[str, Any]] = [
      ("joint_state", {A.BASE: 1.0, A.WRIST: -2.5, A.RAIL: 0.0}),
      ("joint_limits", {A.SHOULDER: (-90.0, 90.0)}),
      ("cartesian_pose", pose),
      ("coordinate", Coordinate(1.0, 2.0, 3.0)),
      ("camera", "bottom"),
      ("camera", 2),
      ("parameter_value", "text"),
      ("parameter_value", 3),
      ("parameter_value", 2.5),
      ("parameter_value", True),
    ]
    for name, value in cases:
      with self.subTest(kind=name, value=value):
        to, from_ = getattr(wire, f"{name}_to"), getattr(wire, f"{name}_from")
        back = from_(to(value))
        # A rotation is equal only to itself, so they are compared as they read.
        self.assertEqual(repr(back), repr(value))
        self.assertIs(type(back), type(value))

  def test_a_configuration_goes_over_as_save_configuration_writes_it(self):
    configuration = PreciseFlexSimulationDriver(RECORDING_PF400).simulated_configuration
    self.assertEqual(wire.configuration_from(wire.configuration_to(configuration)), configuration)


class ErrorTests(unittest.TestCase):
  def back(self, error: BaseException) -> BaseException:
    raised = from_connect_error(to_connect_error(error))
    assert raised is not None
    return raised

  def test_an_error_comes_back_as_its_class_with_its_message(self):
    for error in (
      ValueError("too far"),
      RuntimeError("not set up"),
      NotImplementedError("not simulated"),
      KeyError("x"),
      IKError("unreachable"),
      PreciseFlexError(-1012, "moving"),
      PreciseFlexError(-3100, "hit"),
    ):
      with self.subTest(error=error):
        back = self.back(error)
        self.assertIs(type(back), type(error))
        self.assertEqual(str(back), str(error))
    self.assertIsInstance(self.back(PreciseFlexError(-3100, "hit")), PreciseFlexCollisionError)

  def test_an_out_of_range_error_keeps_its_axes(self):
    error = OutOfRangeOfMotionError("out", {A.ELBOW: (300.0, (-10.0, 290.0))})
    back = self.back(error)
    assert isinstance(back, OutOfRangeOfMotionError)
    self.assertEqual(back.axes, error.axes)


class _Served(unittest.IsolatedAsyncioTestCase):
  """A simulated arm served in this process, and another driven here, to compare them with."""

  rail = False

  async def asyncSetUp(self):
    self.directory = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.directory)
    self.positions_path = os.path.join(self.directory, "positions.json")
    self.resource_server = ResourceServer.local()
    self.served_device = self.make_device()
    self.local = self.make_device()
    self.server = PreciseFlexServer.local(
      self.served_device,
      resource_server=self.resource_server,
      positions_path=self.positions_path,
    )
    self.remote: Any = PreciseFlex400(
      precise_flex_server=self.server, resource_server=self.resource_server
    )

  def make_device(self) -> Any:
    configuration = _railed_configuration(self.directory) if self.rail else RECORDING_PF400
    return PreciseFlex400(simulation=True, declared_configuration_json=configuration, name="pf400")

  @property
  def joints(self) -> Dict[A, float]:
    joints: Dict[A, float] = _simulated(self.served_device).simulated_joint_state
    return joints

  async def set_up(self) -> None:
    await self.local.setup()
    await self.remote.setup()


class ParityTests(_Served):
  """A served arm answers what the same arm in this process answers, call for call."""

  async def both(self, call: Any) -> Tuple[Any, Any]:
    return await call(self.local), await call(self.remote)

  async def assert_same(self, call: Any) -> Any:
    here, there = await self.both(call)
    self.assertEqual(_plain(there), _plain(here))
    return there

  async def assert_same_error(self, call: Any) -> BaseException:
    raised = []
    for device in (self.local, self.remote):
      with self.assertRaises(Exception) as caught:
        await call(device)
      raised.append(caught.exception)
    self.assertIs(type(raised[1]), type(raised[0]))
    self.assertEqual(str(raised[1]), str(raised[0]))
    return raised[1]

  async def test_setup_describes_the_same_arm(self):
    await self.set_up()
    self.assertEqual(self.remote.name, "pf400")
    self.assertEqual(self.remote.model, "PreciseFlex400")
    self.assertEqual(self.remote.driver.configuration, self.local.driver.configuration)
    self.assertEqual(self.remote.arm.parking_position, self.local.arm.parking_position)
    self.assertEqual(self.remote.gripper.jaw_width_range, self.local.gripper.jaw_width_range)
    self.assertEqual(
      self.remote.gripper.closed_gripper_position, self.local.gripper.closed_gripper_position
    )
    self.assertEqual(self.remote.arm.profile_index, self.local.arm.profile_index)
    self.assertIsNone(self.remote.rail)
    self.assertEqual(self.remote.get_size_x(), self.local.get_size_x())

  async def test_reads_are_the_same(self):
    await self.set_up()
    for read in (
      lambda d: d.arm.request_joint_state(),
      lambda d: d.arm.request_pose(),
      lambda d: d.arm.request_gripper_pose(),
      lambda d: d.gripper.sense_fully_closed(),
      lambda d: d.driver.discover(),
    ):
      await self.assert_same(read)

  async def test_moves_end_in_the_same_place(self):
    await self.set_up()
    lower = {**HOTEL}
    await self.both(lambda d: d.arm.move_to_joint_state(lower, speed_percent=50))
    await self.assert_same(lambda d: d.arm.request_joint_state())
    pose = await self.local.arm.request_gripper_pose()
    await self.both(lambda d: d.arm.park())
    await self.both(
      lambda d: d.arm.move_to_location(
        pose.location, pose.rotation.z, orientation=pose.orientation, wrist=pose.wrist
      )
    )
    await self.assert_same(lambda d: d.arm.request_joint_state())
    await self.both(lambda d: d.gripper.move_to_jaw_position(100.0))
    await self.assert_same(lambda d: d.arm.request_joint_state())

  async def test_a_pick_up_and_a_drop_are_the_same(self):
    await self.set_up()
    for device in (self.local, self.remote):
      await device.arm.park()
    await self.both(lambda d: d.arm.pick_up_at_joint_state(HOTEL, resource_width=85.5))
    await self.assert_same(lambda d: d.arm.request_joint_state())
    await self.both(lambda d: d.arm.drop_at_joint_state(NEST, resource_width=85.5))
    await self.assert_same(lambda d: d.arm.request_joint_state())

  async def test_a_deprecated_alias_calls_what_it_stands_for(self):
    await self.set_up()
    with self.assertWarns(DeprecationWarning):
      await self.remote.driver.move_gripper(90.0)
    with self.assertWarns(DeprecationWarning):
      await self.local.driver.move_gripper(90.0)
    await self.assert_same(lambda d: d.arm.request_joint_state())

  async def test_errors_are_the_same(self):
    await self.set_up()
    await self.assert_same_error(lambda d: d.arm.move_to_joint_state({A.BASE: 9999.0}))
    await self.assert_same_error(lambda d: d.driver.set_parameter(100, "x"))
    await self.assert_same_error(lambda d: d.gripper.sense_each_fully_closed())

  async def test_a_feature_the_arm_lacks_is_refused(self):
    await self.set_up()
    with self.assertRaises(ConnectError) as raised:
      await self.server.clients.rail.move_rail(rail_pb2.RailMoveRailRequest(rail_position=1.0))
    self.assertEqual(raised.exception.code, Code.FAILED_PRECONDITION)

  async def test_settings_are_read_and_not_set(self):
    await self.set_up()
    with self.assertRaisesRegex(AttributeError, "settings file"):
      self.remote.arm.profile_index = 2
    with self.assertRaisesRegex(AttributeError, "settings file"):
      self.remote.arm.parking_position = HOTEL
    with self.assertRaisesRegex(AttributeError, "settings file"):
      self.remote.gripper.default_grasp_force = 5.0


class RailTests(_Served):
  rail = True

  async def test_the_rail_moves_as_it_does_here(self):
    await self.set_up()
    assert self.remote.rail is not None and self.local.rail is not None
    await self.local.rail.move_rail(300.0)
    await self.remote.rail.move_rail(300.0)
    joints = await self.remote.arm.request_joint_state()
    self.assertEqual(joints[A.RAIL], 300.0)
    self.assertEqual(joints, await self.local.arm.request_joint_state())


class DescriptionTests(_Served):
  async def test_settings_from_the_file_are_put_in_place_and_described(self):
    path = os.path.join(self.directory, "settings.json")
    with open(path, "w", encoding="utf-8") as f:
      json.dump(
        {
          "arm": {
            "profile_index": 2,
            "parking_position": {"shoulder": 90, "elbow": 180, "wrist": 0},
          },
          "gripper": {"default_grasp_force": 7.5},
        },
        f,
      )
    server = PreciseFlexServer.local(self.served_device, settings=read_settings(path))
    remote = PreciseFlex400(precise_flex_server=server)
    await remote.setup()
    self.assertEqual(self.served_device.arm.profile_index, 2)
    self.assertEqual(remote.arm.profile_index, 2)
    self.assertEqual(remote.gripper.default_grasp_force, 7.5)
    self.assertEqual(remote.arm.parking_position, {A.SHOULDER: 90.0, A.ELBOW: 180.0, A.WRIST: 0.0})

  async def test_a_misspelled_setting_is_refused(self):
    path = os.path.join(self.directory, "settings.json")
    with open(path, "w", encoding="utf-8") as f:
      json.dump({"arm": {"profile_indx": 2}}, f)
    with self.assertRaisesRegex(ValueError, "settings"):
      read_settings(path)

  async def test_the_revision_moves_on_only_when_the_description_changes(self):
    await self.remote.setup()
    before = self.server.revision
    await self.remote.arm.request_joint_state()
    self.assertEqual(self.server.revision, before)
    await self.server.teach("hotel", HOTEL)
    await self.remote.arm.pick_up_at_joint_state(HOTEL, resource_width=85.5)
    self.assertNotEqual(self.server.revision, before)
    self.assertTrue(self.remote.driver.described.holding)  # type: ignore[union-attr]

  async def test_the_arms_parts_are_handles_on_the_resource_server_and_move(self):
    await self.remote.setup()
    carriage = self.remote.arm.resource
    self.assertIsNotNone(carriage)
    self.assertEqual(carriage.name, "pf400_z_carriage")  # type: ignore[union-attr]
    self.assertEqual(self.remote.base_plate.name, "pf400_base_plate")  # type: ignore[union-attr]
    self.assertEqual(self.remote.gripper.resource.name, "pf400_gripper")  # type: ignore[union-attr]
    before = await carriage.get_location()  # type: ignore[union-attr]
    joints = await self.remote.arm.request_joint_state()
    await self.remote.arm.move_to_joint_state({**joints, A.BASE: joints[A.BASE] - 40.0})
    after = await carriage.get_location()  # type: ignore[union-attr]
    assert before is not None and after is not None
    self.assertAlmostEqual(before.z - after.z, 40.0)
    rotation = await self.remote.arm.link_1.get_rotation()  # type: ignore[union-attr]
    self.assertEqual(_plain(rotation), _plain(self.served_device.arm.link_1.rotation))

  async def test_a_device_the_resource_server_holds_is_taken_up_not_made_again(self):
    await self.remote.setup()
    first = self.remote.body
    again = PreciseFlexServer.local(self.make_device(), resource_server=self.resource_server)
    remote: Any = PreciseFlex400(precise_flex_server=again, resource_server=self.resource_server)
    await remote.setup()
    self.assertEqual(remote.body, first)

  async def test_the_factory_refuses_what_the_server_decides(self):
    with self.assertRaisesRegex(ValueError, "simulation"):
      PreciseFlex400(simulation=True, precise_flex_server=self.server)
    with self.assertRaisesRegex(ValueError, "resource_server"):
      PreciseFlex400(simulation=True, resource_server=self.resource_server)


class PositionsTests(_Served):
  async def asyncSetUp(self):
    await super().asyncSetUp()
    await self.remote.setup()

  async def teach_here(self, name: str, joints: Dict[A, float]) -> Dict[A, float]:
    """Move the arm there by hand, as a person in freedrive would, and teach it."""
    await self.remote.arm.start_freedrive_mode()
    self.joints.update(joints)
    taught = await self.server.teach(name)
    await self.remote.arm.stop_freedrive_mode()
    return taught

  async def test_teaching_keeps_where_the_arm_is_and_a_restart_keeps_it(self):
    taught = await self.teach_here("hotel", HOTEL)
    self.assertEqual(taught, HOTEL)
    await self.server.teach("nest", NEST)
    self.assertEqual(await self.server.list_positions(), {"hotel": HOTEL, "nest": NEST})
    again = PreciseFlexServer.local(self.make_device(), positions_path=self.positions_path)
    self.assertEqual(await again.list_positions(), {"hotel": HOTEL, "nest": NEST})
    await again.forget("hotel")
    third = PreciseFlexServer.local(self.make_device(), positions_path=self.positions_path)
    self.assertEqual(await third.list_positions(), {"nest": NEST})

  async def test_teaching_a_name_again_moves_it(self):
    await self.server.teach("hotel", HOTEL)
    await self.server.teach("hotel", NEST)
    self.assertEqual(await self.server.list_positions(), {"hotel": NEST})

  async def test_a_position_needs_a_name_and_every_axis(self):
    with self.assertRaisesRegex(ValueError, "name"):
      await self.server.teach("", HOTEL)
    with self.assertRaisesRegex(ValueError, "WRIST"):
      await self.server.teach("x", {A.BASE: 1.0, A.SHOULDER: 0.0, A.ELBOW: 0.0})

  async def test_forgetting_a_position_it_lacks_is_not_found(self):
    with self.assertRaises(ConnectError) as raised:
      await self.server.forget("nowhere")
    self.assertEqual(raised.exception.code, Code.NOT_FOUND)

  async def test_a_positions_file_it_cannot_use_is_refused_at_start(self):
    with open(self.positions_path, "w", encoding="utf-8") as f:
      json.dump({"positions": [{"name": "x", "joint_state": {"base": 1.0}}]}, f)
    with self.assertRaisesRegex(ValueError, "SHOULDER"):
      PreciseFlexServer.local(self.make_device(), positions_path=self.positions_path)

  async def test_a_carry_picks_up_at_one_position_and_drops_at_the_other(self):
    await self.server.teach("hotel", HOTEL)
    await self.server.teach("nest", NEST)
    arm = _simulated(self.served_device)
    stations: List[Dict[A, float]] = []
    place = arm._unchecked_fw_place_plate

    async def placing() -> None:
      stations.append(dict(arm.simulated_stations[arm.station_index]))
      await place()

    progress: List[tpb.Progress] = []
    with mock.patch.object(arm, "_unchecked_fw_place_plate", side_effect=placing):
      await self.server.carry("hotel", "nest", **PLATE, progress=progress.append)
    self.assertTrue(progress[-1].done)
    self.assertEqual(stations[0][A.BASE], NEST[A.BASE] + PLATE["height"])
    self.assertEqual(stations[0][A.SHOULDER], NEST[A.SHOULDER])
    self.assertFalse(await self.server.get_holding())
    # Folded again, as every visit ends.
    joints = await self.remote.arm.request_joint_state()
    for axis, value in (self.remote.arm.parking_position or {}).items():
      self.assertAlmostEqual(joints[axis], value)
    # The clearance a carry sets is put back.
    self.assertEqual(self.served_device.arm.station_z_clearance, 100)

  async def test_the_gripper_holds_a_plate_between_a_pick_up_and_a_drop(self):
    await self.remote.arm.pick_up_at_joint_state(HOTEL, resource_width=85.5)
    self.assertTrue(await self.server.get_holding())
    await self.remote.arm.drop_at_joint_state(NEST, resource_width=85.5)
    self.assertFalse(await self.server.get_holding())
    await self.remote.gripper.move_to_jaw_position(100.0)
    self.assertIsNone(await self.server.get_holding())

  async def test_a_plate_that_slips_out_is_no_longer_held(self):
    await self.remote.arm.pick_up_at_joint_state(HOTEL, resource_width=85.5)
    self.joints[A.GRIPPER] = self.served_device.gripper.configuration.soft_limit_range[0]
    self.assertFalse(await self.server.get_holding())

  async def test_closing_on_nothing_fails_the_carry(self):
    await self.server.teach("hotel", HOTEL)
    await self.server.teach("nest", NEST)
    low = self.remote.gripper.jaw_width_range[0]
    with self.assertRaisesRegex(RuntimeError, "on nothing"):
      await self.server.carry("hotel", "nest", width=low, height=10.0, plate_height=14.5)
    self.assertFalse(await self.server.get_holding())

  async def test_a_carry_it_cannot_make_is_refused_before_anything_moves(self):
    await self.server.teach("hotel", HOTEL)
    await self.server.teach("nest", NEST)
    before = dict(self.joints)
    with self.assertRaises(ConnectError) as raised:
      await self.server.carry("hotel", "nowhere", **PLATE)
    self.assertEqual(raised.exception.code, Code.NOT_FOUND)
    with self.assertRaisesRegex(ValueError, "width"):
      await self.server.carry("hotel", "nest", width=0.0, height=1.0, plate_height=1.0)
    self.assertEqual(self.joints, before)
    await self.remote.arm.pick_up_at_joint_state(HOTEL, resource_width=85.5)
    before = dict(self.joints)
    with self.assertRaisesRegex(RuntimeError, "already holds"):
      await self.server.carry("hotel", "nest", **PLATE)
    self.assertEqual(self.joints, before)

  async def test_an_arm_not_set_up_refuses_to_carry(self):
    server = PreciseFlexServer.local(self.make_device())
    await server.teach("hotel", HOTEL)
    await server.teach("nest", NEST)
    with self.assertRaisesRegex(RuntimeError, "not set up"):
      await server.carry("hotel", "nest", **PLATE)


class RailPositionsTests(_Served):
  rail = True

  async def test_a_position_keeps_its_rail_position_and_the_rail_moves_folded(self):
    await self.remote.setup()
    await self.server.teach("hotel", {**HOTEL, A.RAIL: 250.0})
    await self.server.teach("nest", {**NEST, A.RAIL: 900.0})
    with self.assertRaisesRegex(ValueError, "RAIL"):
      await self.server.teach("x", HOTEL)
    await self.server.carry("hotel", "nest", **PLATE)
    self.assertEqual(self.joints[A.RAIL], 900.0)

  async def test_a_position_taught_without_a_rail_is_refused(self):
    flat = {"base": 100, "shoulder": 30, "elbow": 120, "wrist": 210}
    with open(self.positions_path, "w", encoding="utf-8") as f:
      json.dump({"positions": [{"name": "flat", "joint_state": flat}]}, f)
    server = PreciseFlexServer.local(self.make_device(), positions_path=self.positions_path)
    remote = PreciseFlex400(precise_flex_server=server)
    await remote.setup()
    with self.assertRaisesRegex(ValueError, "without a rail"):
      await server.carry("flat", "flat", **PLATE)


class _Context:
  """What a handler is given, with its response headers and trailers."""

  def __init__(self) -> None:
    self.response_headers: Dict[str, str] = {}
    self.response_trailers: Dict[str, str] = {}


class LongCallTests(_Served):
  async def asyncSetUp(self):
    await super().asyncSetUp()
    patcher = mock.patch.object(positions, "PROGRESS_INTERVAL", 0.01)
    patcher.start()
    self.addCleanup(patcher.stop)
    self.served = serve.Served(self.served_device, positions_path=self.positions_path)
    self.handlers = positions.PositionsHandlers(self.served)
    await self.served_device.setup()
    self.served.set_up, self.served.holding = True, False
    for name, joints in (("hotel", HOTEL), ("nest", NEST)):
      self.served.positions.teach(ppb.Position(name=name, joint_state=wire.joint_state_to(joints)))
    # A park that takes a while, as a real one does.
    park = self.served_device.arm.park

    async def slow_park(**kwargs: Any) -> None:
      await asyncio.sleep(0.05)
      await park(**kwargs)

    parking = mock.patch.object(self.served_device.arm, "park", side_effect=slow_park)
    parking.start()
    self.addCleanup(parking.stop)

  def carry(self) -> ppb.CarryRequest:
    return ppb.CarryRequest(from_position="hotel", to_position="nest", grip=ppb.Grip(**PLATE))

  async def test_a_carry_streams_its_progress_until_it_is_done(self):
    context = _Context()
    progress = [p async for p in self.handlers.carry(self.carry(), context)]  # type: ignore[arg-type]
    self.assertGreater(len(progress), 1)
    self.assertFalse(any(p.done for p in progress[:-1]))
    self.assertTrue(progress[-1].done)
    self.assertIn("park", {p.step for p in progress})
    self.assertEqual(context.response_trailers[serve.REVISION_HEADER], str(self.served.revision))

  async def test_a_carry_finishes_on_the_server_when_its_client_goes(self):
    stream = self.handlers.carry(self.carry(), _Context())  # type: ignore[arg-type]
    first = await stream.__anext__()
    self.assertFalse(first.done)
    await stream.aclose()  # type: ignore[attr-defined]
    self.assertTrue(self.served.running)
    while self.served.running:
      await asyncio.sleep(0.01)
    arm = _simulated(self.served_device)
    self.assertEqual(arm.simulated_stations[arm.station_index][A.BASE], NEST[A.BASE] + 10.0)
    self.assertFalse(self.served.holding)

  async def test_a_move_waits_for_a_carry(self):
    stream = self.handlers.carry(self.carry(), _Context())  # type: ignore[arg-type]
    await stream.__anext__()
    self.assertTrue(self.served.motion.locked())
    async for _ in stream:
      pass
    self.assertFalse(self.served.motion.locked())

  async def test_a_carry_that_fails_says_so(self):
    self.served.holding = True
    with self.assertRaises(ConnectError) as raised:
      async for _ in self.handlers.carry(self.carry(), _Context()):  # type: ignore[arg-type]
        pass
    self.assertEqual(raised.exception.code, Code.FAILED_PRECONDITION)


class CommandLineTests(unittest.TestCase):
  def run_main(self, *argv: str) -> mock.AsyncMock:
    with mock.patch.object(command_line, "serve", new_callable=mock.AsyncMock) as served:
      command_line.main(list(argv))
    return served

  def test_a_simulated_arm_is_served_with_its_positions(self):
    served = self.run_main("--simulation", "--positions", "p.json", "--name", "arm_1")
    (device,), kwargs = served.call_args.args, served.call_args.kwargs
    self.assertEqual(device.name, "arm_1")
    self.assertIsInstance(device.driver, PreciseFlexSimulationDriver)
    self.assertEqual(kwargs["positions_path"], "p.json")
    self.assertEqual(kwargs["port"], 8090)
    self.assertIsNone(kwargs["resource_server"])

  def test_a_real_arm_needs_its_closed_gripper_position(self):
    with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
      self.run_main("--arm-host", "10.0.0.5")
    served = self.run_main("--arm-host", "10.0.0.5", "--closed-gripper-position", "60")
    (device,) = served.call_args.args
    self.assertNotIsInstance(device.driver, PreciseFlexSimulationDriver)
    self.assertEqual(device.driver.gripper.closed_gripper_position, 60.0)

  def test_a_resource_server_is_held_here_when_given_a_port(self):
    served = self.run_main("--simulation", "--resource-port", "8091")
    kwargs = served.call_args.kwargs
    self.assertEqual(kwargs["resource_port"], 8091)
    self.assertIsNotNone(kwargs["resource_server"].memory)

  def test_it_needs_an_arm(self):
    with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
      self.run_main("--positions", "p.json")


if __name__ == "__main__":
  unittest.main()
