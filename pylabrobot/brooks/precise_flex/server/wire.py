"""The PreciseFlex's values as the wire carries them, and back: what the generated code calls for
each argument and result that is not a plain number, string or flag (`v1/types.proto`)."""

import dataclasses
import json
from typing import Any, Dict, List, Literal, Tuple, Union, cast

from pylabrobot.brooks.precise_flex.driver.configuration import (
  DEVICE_FEATURE_CONFIGURATIONS,
  PreciseFlexConfiguration,
  restore_configuration,
  to_jsonable,
)
from pylabrobot.brooks.precise_flex.driver.features.arm import MotionProfile
from pylabrobot.brooks.precise_flex.driver.features.vision import (
  CameraInfo,
  StereoParameters,
  VisionConfiguration,
  VisionToolInfo,
)
from pylabrobot.brooks.precise_flex.kinematics import (
  ElbowOrientation,
  JointState,
  PF400Params,
  PreciseFlexAxis,
  PreciseFlexCartesianPose,
  PreciseFlexPose,
  Wrist,
)
from pylabrobot.brooks.precise_flex.server.v1 import types_pb2 as tpb
from pylabrobot.resources.coordinate import Coordinate
from pylabrobot.resources.rotation import Rotation

# Each axis and its field in `JointState` and `JointLimits`.
AXIS_FIELDS: Tuple[Tuple[PreciseFlexAxis, str], ...] = tuple(
  (axis, axis.name.lower()) for axis in PreciseFlexAxis
)

# -- named values --------------------------------------------------------------------------------

_ELBOW = {"right": tpb.ELBOW_ORIENTATION_RIGHT, "left": tpb.ELBOW_ORIENTATION_LEFT}
_WRIST = {"cw": tpb.WRIST_CW, "ccw": tpb.WRIST_CCW}
_RESPONSE_MODE = {"pc": tpb.RESPONSE_MODE_PC, "verbose": tpb.RESPONSE_MODE_VERBOSE}
_COMMAND_SERVER = {
  "controller": tpb.COMMAND_SERVER_CONTROLLER,
  "vision": tpb.COMMAND_SERVER_VISION,
}
_CAMERA_NAME = {"front": tpb.CAMERA_NAME_FRONT, "bottom": tpb.CAMERA_NAME_BOTTOM}


def _named(table: Dict[str, Any], value: str, what: str) -> Any:
  try:
    return table[value]
  except KeyError:
    raise ValueError(f"{what} is one of {sorted(table)}, not {value!r}") from None


def _unnamed(table: Dict[str, Any], value: int, what: str) -> Any:
  for name, number in table.items():
    if number == value:
      return name
  raise ValueError(f"{value} is no {what}")


def elbow_orientation_to(value: ElbowOrientation) -> "tpb.ElbowOrientation":
  return cast("tpb.ElbowOrientation", _named(_ELBOW, value, "an elbow orientation"))


def elbow_orientation_from(value: int) -> ElbowOrientation:
  return cast(ElbowOrientation, _unnamed(_ELBOW, value, "elbow orientation"))


def wrist_to(value: Wrist) -> "tpb.Wrist":
  return cast("tpb.Wrist", _named(_WRIST, value, "a wrist"))


def wrist_from(value: int) -> Wrist:
  return cast(Wrist, _unnamed(_WRIST, value, "wrist"))


def response_mode_to(value: str) -> "tpb.ResponseMode":
  return cast("tpb.ResponseMode", _named(_RESPONSE_MODE, value, "a response mode"))


def response_mode_from(value: int) -> Literal["pc", "verbose"]:
  return cast(Literal["pc", "verbose"], _unnamed(_RESPONSE_MODE, value, "response mode"))


def command_server_to(value: str) -> "tpb.CommandServer":
  return cast("tpb.CommandServer", _named(_COMMAND_SERVER, value, "a server"))


def command_server_from(value: int) -> Literal["controller", "vision"]:
  return cast(Literal["controller", "vision"], _unnamed(_COMMAND_SERVER, value, "server"))


def axis_to(value: PreciseFlexAxis) -> "tpb.Axis":
  return cast("tpb.Axis", int(PreciseFlexAxis(value)))


def axis_from(value: int) -> PreciseFlexAxis:
  return PreciseFlexAxis(value)


def camera_to(value: Union[str, int]) -> tpb.Camera:
  if isinstance(value, str):
    return tpb.Camera(name=_named(_CAMERA_NAME, value, "a camera"))
  return tpb.Camera(number=value)


def camera_from(message: tpb.Camera) -> Union[Literal["front", "bottom"], int]:
  if message.WhichOneof("camera") == "number":
    return message.number
  return cast(Literal["front", "bottom"], _unnamed(_CAMERA_NAME, message.name, "camera"))


# -- values --------------------------------------------------------------------------------------


def coordinate_to(value: Coordinate) -> tpb.Coordinate:
  return tpb.Coordinate(x=value.x, y=value.y, z=value.z)


def coordinate_from(message: tpb.Coordinate) -> Coordinate:
  return Coordinate(message.x, message.y, message.z)


def joint_state_to(value: JointState) -> tpb.JointState:
  message = tpb.JointState()
  for axis, field in AXIS_FIELDS:
    if axis in value:
      setattr(message, field, float(value[axis]))
  return message


def joint_state_from(message: tpb.JointState) -> JointState:
  return {axis: getattr(message, field) for axis, field in AXIS_FIELDS if message.HasField(field)}


def joint_limits_to(value: Dict[PreciseFlexAxis, Tuple[float, float]]) -> tpb.JointLimits:
  message = tpb.JointLimits()
  for axis, field in AXIS_FIELDS:
    if axis in value:
      low, high = value[axis]
      getattr(message, field).CopyFrom(tpb.Range(low=low, high=high))
  return message


def joint_limits_from(message: tpb.JointLimits) -> Dict[PreciseFlexAxis, Tuple[float, float]]:
  limits: Dict[PreciseFlexAxis, Tuple[float, float]] = {}
  for axis, field in AXIS_FIELDS:
    if message.HasField(field):
      found = getattr(message, field)
      limits[axis] = (found.low, found.high)
  return limits


def cartesian_pose_to(value: PreciseFlexCartesianPose) -> tpb.CartesianPose:
  message = tpb.CartesianPose(
    location=coordinate_to(value.location),
    rotation=tpb.Rotation(x=value.rotation.x, y=value.rotation.y, z=value.rotation.z),
  )
  if value.rail_position is not None:
    message.rail_position = value.rail_position
  if value.orientation is not None:
    message.orientation = elbow_orientation_to(value.orientation)
  if value.wrist is not None:
    message.wrist = wrist_to(value.wrist)
  return message


def cartesian_pose_from(message: tpb.CartesianPose) -> PreciseFlexCartesianPose:
  return PreciseFlexCartesianPose(
    location=coordinate_from(message.location),
    rotation=Rotation(message.rotation.x, message.rotation.y, message.rotation.z),
    rail_position=message.rail_position if message.HasField("rail_position") else None,
    orientation=elbow_orientation_from(message.orientation) if message.orientation else None,
    wrist=wrist_from(message.wrist) if message.wrist else None,
  )


def pose_to(value: PreciseFlexPose) -> tpb.Pose:
  return tpb.Pose(
    shoulder_joint_location=coordinate_to(value.shoulder_joint_location),
    elbow_joint_location=coordinate_to(value.elbow_joint_location),
    wrist_joint_location=coordinate_to(value.wrist_joint_location),
    gripper_pose=cartesian_pose_to(value.gripper_pose),
    joints=joint_state_to(value.joints),
  )


def pose_from(message: tpb.Pose) -> PreciseFlexPose:
  return PreciseFlexPose(
    shoulder_joint_location=coordinate_from(message.shoulder_joint_location),
    elbow_joint_location=coordinate_from(message.elbow_joint_location),
    wrist_joint_location=coordinate_from(message.wrist_joint_location),
    gripper_pose=cartesian_pose_from(message.gripper_pose),
    joints=joint_state_from(message.joints),
  )


def motion_profile_to(value: MotionProfile) -> tpb.MotionProfile:
  return tpb.MotionProfile(**value._asdict())


def motion_profile_from(message: tpb.MotionProfile) -> MotionProfile:
  return MotionProfile(**{field: getattr(message, field) for field in MotionProfile._fields})


def kinematic_parameters_to(value: PF400Params) -> tpb.KinematicParameters:
  return tpb.KinematicParameters(**dataclasses.asdict(value))


def kinematic_parameters_from(message: tpb.KinematicParameters) -> PF400Params:
  return PF400Params(
    **{field.name: getattr(message, field.name) for field in dataclasses.fields(PF400Params)}
  )


def stereo_parameters_to(value: StereoParameters) -> tpb.StereoParameters:
  return tpb.StereoParameters(**dataclasses.asdict(value))


def stereo_parameters_from(message: tpb.StereoParameters) -> StereoParameters:
  return StereoParameters(
    **{field.name: getattr(message, field.name) for field in dataclasses.fields(StereoParameters)}
  )


def parameter_value_to(value: Any) -> tpb.ParameterValue:
  """A value for the parameter database: a string is quoted, so the kind travels with it."""
  if isinstance(value, bool):
    return tpb.ParameterValue(flag=value)
  if isinstance(value, int):
    return tpb.ParameterValue(integer=value)
  if isinstance(value, float):
    return tpb.ParameterValue(number=value)
  if isinstance(value, str):
    return tpb.ParameterValue(text=value)
  raise TypeError(f"a parameter is a number, a string or a flag, not {type(value).__name__}")


def parameter_value_from(message: tpb.ParameterValue) -> Any:
  which = message.WhichOneof("value")
  return None if which is None else getattr(message, which)


def image_to(value: Any) -> tpb.Image:
  import numpy as np

  array = np.ascontiguousarray(value)
  return tpb.Image(data=array.tobytes(), shape=list(array.shape), dtype=str(array.dtype))


def image_from(message: tpb.Image) -> Any:
  import numpy as np

  return np.frombuffer(message.data, dtype=np.dtype(message.dtype)).reshape(tuple(message.shape))


def vision_server_result_to(value: Tuple[str, bytes]) -> tpb.VisionServerResult:
  return tpb.VisionServerResult(name=value[0], data=value[1])


def vision_server_result_from(message: tpb.VisionServerResult) -> Tuple[str, bytes]:
  return (message.name, message.data)


def string_lists_to(value: Dict[str, List[str]]) -> Dict[str, tpb.StringList]:
  return {key: tpb.StringList(values=items) for key, items in value.items()}


def string_lists_from(message: Any) -> Dict[str, List[str]]:
  return {key: list(items.values) for key, items in message.items()}


# -- configurations, as JSON -----------------------------------------------------------------------


def configuration_to(value: PreciseFlexConfiguration) -> str:
  """A configuration, as `save_configuration` writes one."""
  device = to_jsonable(value)
  saved: Dict[str, Any] = {
    "device": {n: v for n, v in device.items() if n not in DEVICE_FEATURE_CONFIGURATIONS}
  }
  for name in DEVICE_FEATURE_CONFIGURATIONS:
    if device.get(name) is not None:
      saved[name] = device[name]
  return json.dumps(saved, sort_keys=True)


def configuration_from(text: str) -> PreciseFlexConfiguration:
  configuration: PreciseFlexConfiguration = restore_configuration(json.loads(text))["device"]
  return configuration


def vision_configuration_to(value: VisionConfiguration) -> str:
  return json.dumps(to_jsonable(value), sort_keys=True)


def vision_configuration_from(text: str) -> VisionConfiguration:
  saved = json.loads(text)
  return VisionConfiguration(
    **{
      **saved,
      "vision_tools": {
        name: VisionToolInfo(**tool) for name, tool in saved.get("vision_tools", {}).items()
      },
      "cameras": {int(n): CameraInfo(**camera) for n, camera in saved.get("cameras", {}).items()},
    }
  )
