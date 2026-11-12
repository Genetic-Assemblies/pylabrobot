"""A PreciseFlex arm that answers without being connected.

Each feature has a small subclass here that overrides the methods which would otherwise talk to the
controller, returning what one would have said. `PreciseFlexSimulationDriver` swaps those in, so
everything above them - discovery, the declared configuration's check, the guards, the model - runs
as it does against an arm.

Nothing reaches the wire. `send_command` raises, which is how a command that has not been simulated
makes itself known: override the method that sends it, on the feature that owns it.
"""

import logging
from typing import Any, Dict, List, Optional, cast

from pylabrobot.brooks.precise_flex.driver.configuration import (
  PreciseFlexConfiguration,
  read_configuration,
)
from pylabrobot.brooks.precise_flex.driver.features.arm import PreciseFlexArm
from pylabrobot.brooks.precise_flex.driver.features.gripper import PreciseFlexGripper
from pylabrobot.brooks.precise_flex.driver.features.rail import PreciseFlexRail
from pylabrobot.brooks.precise_flex.driver.master import PreciseFlexDriver
from pylabrobot.brooks.precise_flex.kinematics import JointState, PreciseFlexAxis
from pylabrobot.resources.resource import Resource

logger = logging.getLogger(__name__)


class _SimulatedArm(PreciseFlexArm):
  """An arm that holds its joint state: a joint read returns it, a joint move sets it."""

  def __init__(self, driver: PreciseFlexDriver) -> None:
    super().__init__(driver)
    # Set at discovery, once the soft limits and the parking pose are known.
    self.simulated_joint_state: JointState = {}
    self.simulated_speed_percent = 100.0
    self.simulated_freedrive = False
    # Each station's joint state, as `locAngles` sets it.
    self.simulated_stations: Dict[int, JointState] = {}

  async def _wait_for_eom(self, *args: Any, **kwargs: Any) -> None:
    """A simulated move is over as soon as it is sent."""

  async def request_joint_state(self) -> JointState:
    joints = dict(self.simulated_joint_state)
    self.update_joint_state(joints)
    gripper = self._driver.gripper
    gripper.update_width(gripper._firmware_units_to_mm(joints[PreciseFlexAxis.GRIPPER]))
    return joints

  async def _unchecked_fw_move_j(self, profile_index: int, joint_coords: JointState) -> None:
    self.simulated_joint_state.update(joint_coords)

  async def _unchecked_fw_move_one_axis(self, axis: PreciseFlexAxis, position: float) -> None:
    self.simulated_joint_state[axis] = position

  async def _set_speed(self, speed_percent: float) -> None:
    self.simulated_speed_percent = speed_percent

  async def _request_speed(self) -> float:
    return self.simulated_speed_percent

  async def start_freedrive_mode(self, free_axes: Optional[List[int]] = None) -> None:
    """A simulated arm in freedrive stands wherever `simulated_joint_state` is set to."""
    self.simulated_freedrive = True

  async def stop_freedrive_mode(self) -> None:
    """Leave freedrive: the arm holds where it was left."""
    self.simulated_freedrive = False

  async def stop_zero_torque(self) -> None:
    """A simulated arm is never in zero torque."""

  async def _unchecked_fw_set_joint_angles(
    self, station_index: int, joint_position: JointState
  ) -> None:
    self.simulated_stations[station_index] = dict(joint_position)

  async def _unchecked_fw_set_grip_detail(self) -> None:
    """A simulated station is always approached from above."""

  async def _unchecked_fw_pick_plate(self) -> None:
    """Go to the station and close the jaws to the grasp width: a plate is always there."""
    station = self.simulated_stations[self.station_index]
    self.simulated_joint_state.update(
      {axis: value for axis, value in station.items() if axis != PreciseFlexAxis.GRIPPER}
    )
    gripper = cast(_SimulatedGripper, self._driver.gripper)
    self.simulated_joint_state[PreciseFlexAxis.GRIPPER] = gripper.simulated_grasp_units

  async def _unchecked_fw_place_plate(self) -> None:
    """Go to the station and open the jaws all the way."""
    station = self.simulated_stations[self.station_index]
    self.simulated_joint_state.update(
      {axis: value for axis, value in station.items() if axis != PreciseFlexAxis.GRIPPER}
    )
    configuration = self._driver.gripper.configuration
    assert configuration is not None
    self.simulated_joint_state[PreciseFlexAxis.GRIPPER] = configuration.soft_limit_range[1]

  async def halt(self) -> None:
    """A simulated move is never under way."""


class _SimulatedGripper(PreciseFlexGripper):
  """A gripper whose jaws stand wherever they were last sent, in the arm's held joint state."""

  def __init__(self, driver: PreciseFlexDriver, arm: _SimulatedArm, **kwargs: Any) -> None:
    super().__init__(driver, **kwargs)
    self._arm = arm
    # The gripper axis position `pickplate` closes to, as `GraspData` sets it.
    self.simulated_grasp_units = self.closed_gripper_position

  async def _unchecked_fw_grasp_plate(
    self, units: float, speed_percent: float, force: float
  ) -> bool:
    self._arm.simulated_joint_state[PreciseFlexAxis.GRIPPER] = units
    return False  # a simulated gripper holds nothing

  async def _unchecked_fw_release_plate(self, units: float, speed_percent: float) -> None:
    self._arm.simulated_joint_state[PreciseFlexAxis.GRIPPER] = units

  async def _unchecked_fw_set_grasp_data(
    self, units: float, finger_speed_percent: float, grasp_force: float
  ) -> None:
    self.simulated_grasp_units = units

  async def sense_fully_closed(self) -> bool:
    """Whether the jaws stand within 2 mm of the closed end of their travel."""
    if self._is_dual_gripper:
      raise ValueError("sense_fully_closed is only valid for single gripper robots.")
    closed = self.configuration.soft_limit_range[0] if self.configuration else 0.0
    return self._arm.simulated_joint_state[PreciseFlexAxis.GRIPPER] <= closed + 2.0


class _SimulatedRail(PreciseFlexRail):
  """A rail that stands at the arm's held rail position: a rail move sets it."""

  def __init__(self, driver: PreciseFlexDriver, arm: _SimulatedArm) -> None:
    super().__init__(driver)
    self._arm = arm
    self._stations: Dict[int, float] = {}

  async def _unchecked_fw_set_rail_position(self, station_id: int, rail_position: float) -> None:
    self._stations[station_id] = rail_position

  async def _unchecked_fw_move_rail(self, station_id: int, mode: int = 1) -> None:
    self._arm.simulated_joint_state[PreciseFlexAxis.RAIL] = self._stations[station_id]


class PreciseFlexSimulationDriver(PreciseFlexDriver):
  """A simulated PreciseFlex arm, driven exactly like the real one."""

  def __init__(
    self,
    declared_configuration_json: str,
    base_plate: Optional[Resource] = None,
  ) -> None:
    """
    Args:
      declared_configuration_json: path to a declared configuration, which this arm then answers
        as. Its kinematics give the tool length and offset.
      base_plate: the base plate to build the arm on, as the real driver takes it.

    Raises:
      ValueError: If the file declares no device configuration.
    """
    configuration = read_configuration(declared_configuration_json).get("device")
    if configuration is None:
      raise ValueError(
        "a simulated arm has to be told what it is simulating: pass "
        "`declared_configuration_json`, naming a file that holds one"
      )
    # Firmware units equal millimetres: the narrow end of the jaws is their first unit.
    closed = PreciseFlexGripper.jaw_width_range[0]
    super().__init__(
      host="simulation",
      gripper_length=configuration.arm.kinematics.gripper_length,
      gripper_z_offset=configuration.arm.kinematics.gripper_z_offset,
      closed_gripper_position=closed,
      base_plate=base_plate,
      declared_configuration_json=declared_configuration_json,
    )
    self.simulated_configuration: PreciseFlexConfiguration = configuration
    self._simulated_arm = _SimulatedArm(self)
    self.arm = self._simulated_arm
    # Unset, as the real constructor leaves it: discovery fills the default.
    self.arm.parking_position = None
    self.gripper = _SimulatedGripper(
      self,
      self._simulated_arm,
      closed_gripper_position=closed,
      is_dual_gripper=configuration.gripper.is_dual_gripper,
    )
    self._homed = False

  async def send_command(self, command: str, **kwargs: Any) -> str:
    raise NotImplementedError(
      f"a simulated arm sends nothing, and {command.split()[0]!r} is not simulated: override the "
      "method that sends it, on the feature that owns it"
    )

  async def connect(self) -> None:
    logger.debug("[PreciseFlex simulation] connected")

  async def disconnect(self) -> None:
    logger.debug("[PreciseFlex simulation] disconnected")

  async def power_on_robot(self) -> None:
    """A simulated arm has power."""

  async def attach(self, attach_state: Optional[int] = None) -> int:
    return 1

  async def home(self) -> None:
    self._homed = True

  async def _is_robot_homed(self) -> bool:
    return self._homed

  async def _request_configuration(self) -> PreciseFlexConfiguration:
    return self.simulated_configuration

  async def discover(self) -> PreciseFlexConfiguration:
    """Adopt the declared configuration; the first time, stand the arm parked with its jaws open."""
    configuration = await super().discover()
    arm = self._simulated_arm
    if not arm.simulated_joint_state:
      parked = arm._parking_pose_with_default_z(arm.parking_position or {})
      arm.simulated_joint_state = {
        **dict.fromkeys([PreciseFlexAxis.RAIL, *PreciseFlexArm._WIRE_ORDER], 0.0),
        **parked,
        PreciseFlexAxis.GRIPPER: configuration.gripper.soft_limit_range[1],
      }
    return configuration

  def _adopt_configuration(self, config: PreciseFlexConfiguration) -> None:
    """Adopt it as the real driver does, with a simulated rail on an arm declared with one."""
    super()._adopt_configuration(config)
    if self.rail is not None and not isinstance(self.rail, _SimulatedRail):
      rail = _SimulatedRail(self, self._simulated_arm)
      rail.configuration = self.rail.configuration
      self.rail = rail

  async def _setup_vision(self, vision_host: Optional[str]) -> None:
    """A simulated arm has no vision server."""
