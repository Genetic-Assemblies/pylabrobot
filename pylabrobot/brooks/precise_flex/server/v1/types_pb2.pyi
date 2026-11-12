from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ElbowOrientation(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ELBOW_ORIENTATION_UNSPECIFIED: _ClassVar[ElbowOrientation]
    ELBOW_ORIENTATION_RIGHT: _ClassVar[ElbowOrientation]
    ELBOW_ORIENTATION_LEFT: _ClassVar[ElbowOrientation]

class Wrist(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    WRIST_UNSPECIFIED: _ClassVar[Wrist]
    WRIST_CW: _ClassVar[Wrist]
    WRIST_CCW: _ClassVar[Wrist]

class ResponseMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RESPONSE_MODE_UNSPECIFIED: _ClassVar[ResponseMode]
    RESPONSE_MODE_PC: _ClassVar[ResponseMode]
    RESPONSE_MODE_VERBOSE: _ClassVar[ResponseMode]

class CommandServer(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMMAND_SERVER_UNSPECIFIED: _ClassVar[CommandServer]
    COMMAND_SERVER_CONTROLLER: _ClassVar[CommandServer]
    COMMAND_SERVER_VISION: _ClassVar[CommandServer]

class CameraName(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CAMERA_NAME_UNSPECIFIED: _ClassVar[CameraName]
    CAMERA_NAME_FRONT: _ClassVar[CameraName]
    CAMERA_NAME_BOTTOM: _ClassVar[CameraName]

class Axis(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AXIS_UNSPECIFIED: _ClassVar[Axis]
    AXIS_BASE: _ClassVar[Axis]
    AXIS_SHOULDER: _ClassVar[Axis]
    AXIS_ELBOW: _ClassVar[Axis]
    AXIS_WRIST: _ClassVar[Axis]
    AXIS_GRIPPER: _ClassVar[Axis]
    AXIS_RAIL: _ClassVar[Axis]
ELBOW_ORIENTATION_UNSPECIFIED: ElbowOrientation
ELBOW_ORIENTATION_RIGHT: ElbowOrientation
ELBOW_ORIENTATION_LEFT: ElbowOrientation
WRIST_UNSPECIFIED: Wrist
WRIST_CW: Wrist
WRIST_CCW: Wrist
RESPONSE_MODE_UNSPECIFIED: ResponseMode
RESPONSE_MODE_PC: ResponseMode
RESPONSE_MODE_VERBOSE: ResponseMode
COMMAND_SERVER_UNSPECIFIED: CommandServer
COMMAND_SERVER_CONTROLLER: CommandServer
COMMAND_SERVER_VISION: CommandServer
CAMERA_NAME_UNSPECIFIED: CameraName
CAMERA_NAME_FRONT: CameraName
CAMERA_NAME_BOTTOM: CameraName
AXIS_UNSPECIFIED: Axis
AXIS_BASE: Axis
AXIS_SHOULDER: Axis
AXIS_ELBOW: Axis
AXIS_WRIST: Axis
AXIS_GRIPPER: Axis
AXIS_RAIL: Axis

class Coordinate(_message.Message):
    __slots__ = ("x", "y", "z")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ...) -> None: ...

class Rotation(_message.Message):
    __slots__ = ("x", "y", "z")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ...) -> None: ...

class JointState(_message.Message):
    __slots__ = ("base", "shoulder", "elbow", "wrist", "gripper", "rail")
    BASE_FIELD_NUMBER: _ClassVar[int]
    SHOULDER_FIELD_NUMBER: _ClassVar[int]
    ELBOW_FIELD_NUMBER: _ClassVar[int]
    WRIST_FIELD_NUMBER: _ClassVar[int]
    GRIPPER_FIELD_NUMBER: _ClassVar[int]
    RAIL_FIELD_NUMBER: _ClassVar[int]
    base: float
    shoulder: float
    elbow: float
    wrist: float
    gripper: float
    rail: float
    def __init__(self, base: _Optional[float] = ..., shoulder: _Optional[float] = ..., elbow: _Optional[float] = ..., wrist: _Optional[float] = ..., gripper: _Optional[float] = ..., rail: _Optional[float] = ...) -> None: ...

class Range(_message.Message):
    __slots__ = ("low", "high")
    LOW_FIELD_NUMBER: _ClassVar[int]
    HIGH_FIELD_NUMBER: _ClassVar[int]
    low: float
    high: float
    def __init__(self, low: _Optional[float] = ..., high: _Optional[float] = ...) -> None: ...

class JointLimits(_message.Message):
    __slots__ = ("base", "shoulder", "elbow", "wrist", "gripper", "rail")
    BASE_FIELD_NUMBER: _ClassVar[int]
    SHOULDER_FIELD_NUMBER: _ClassVar[int]
    ELBOW_FIELD_NUMBER: _ClassVar[int]
    WRIST_FIELD_NUMBER: _ClassVar[int]
    GRIPPER_FIELD_NUMBER: _ClassVar[int]
    RAIL_FIELD_NUMBER: _ClassVar[int]
    base: Range
    shoulder: Range
    elbow: Range
    wrist: Range
    gripper: Range
    rail: Range
    def __init__(self, base: _Optional[_Union[Range, _Mapping]] = ..., shoulder: _Optional[_Union[Range, _Mapping]] = ..., elbow: _Optional[_Union[Range, _Mapping]] = ..., wrist: _Optional[_Union[Range, _Mapping]] = ..., gripper: _Optional[_Union[Range, _Mapping]] = ..., rail: _Optional[_Union[Range, _Mapping]] = ...) -> None: ...

class CartesianPose(_message.Message):
    __slots__ = ("location", "rotation", "rail_position", "orientation", "wrist")
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ROTATION_FIELD_NUMBER: _ClassVar[int]
    RAIL_POSITION_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    WRIST_FIELD_NUMBER: _ClassVar[int]
    location: Coordinate
    rotation: Rotation
    rail_position: float
    orientation: ElbowOrientation
    wrist: Wrist
    def __init__(self, location: _Optional[_Union[Coordinate, _Mapping]] = ..., rotation: _Optional[_Union[Rotation, _Mapping]] = ..., rail_position: _Optional[float] = ..., orientation: _Optional[_Union[ElbowOrientation, str]] = ..., wrist: _Optional[_Union[Wrist, str]] = ...) -> None: ...

class Pose(_message.Message):
    __slots__ = ("shoulder_joint_location", "elbow_joint_location", "wrist_joint_location", "gripper_pose", "joints")
    SHOULDER_JOINT_LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELBOW_JOINT_LOCATION_FIELD_NUMBER: _ClassVar[int]
    WRIST_JOINT_LOCATION_FIELD_NUMBER: _ClassVar[int]
    GRIPPER_POSE_FIELD_NUMBER: _ClassVar[int]
    JOINTS_FIELD_NUMBER: _ClassVar[int]
    shoulder_joint_location: Coordinate
    elbow_joint_location: Coordinate
    wrist_joint_location: Coordinate
    gripper_pose: CartesianPose
    joints: JointState
    def __init__(self, shoulder_joint_location: _Optional[_Union[Coordinate, _Mapping]] = ..., elbow_joint_location: _Optional[_Union[Coordinate, _Mapping]] = ..., wrist_joint_location: _Optional[_Union[Coordinate, _Mapping]] = ..., gripper_pose: _Optional[_Union[CartesianPose, _Mapping]] = ..., joints: _Optional[_Union[JointState, _Mapping]] = ...) -> None: ...

class MotionProfile(_message.Message):
    __slots__ = ("profile", "speed", "speed2", "acceleration", "deceleration", "acceleration_ramp", "deceleration_ramp", "in_range", "straight")
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    SPEED2_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    DECELERATION_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_RAMP_FIELD_NUMBER: _ClassVar[int]
    DECELERATION_RAMP_FIELD_NUMBER: _ClassVar[int]
    IN_RANGE_FIELD_NUMBER: _ClassVar[int]
    STRAIGHT_FIELD_NUMBER: _ClassVar[int]
    profile: int
    speed: float
    speed2: float
    acceleration: float
    deceleration: float
    acceleration_ramp: float
    deceleration_ramp: float
    in_range: float
    straight: bool
    def __init__(self, profile: _Optional[int] = ..., speed: _Optional[float] = ..., speed2: _Optional[float] = ..., acceleration: _Optional[float] = ..., deceleration: _Optional[float] = ..., acceleration_ramp: _Optional[float] = ..., deceleration_ramp: _Optional[float] = ..., in_range: _Optional[float] = ..., straight: _Optional[bool] = ...) -> None: ...

class KinematicParameters(_message.Message):
    __slots__ = ("l1", "l2", "gripper_length", "gripper_z_offset", "eps")
    L1_FIELD_NUMBER: _ClassVar[int]
    L2_FIELD_NUMBER: _ClassVar[int]
    GRIPPER_LENGTH_FIELD_NUMBER: _ClassVar[int]
    GRIPPER_Z_OFFSET_FIELD_NUMBER: _ClassVar[int]
    EPS_FIELD_NUMBER: _ClassVar[int]
    l1: float
    l2: float
    gripper_length: float
    gripper_z_offset: float
    eps: float
    def __init__(self, l1: _Optional[float] = ..., l2: _Optional[float] = ..., gripper_length: _Optional[float] = ..., gripper_z_offset: _Optional[float] = ..., eps: _Optional[float] = ...) -> None: ...

class StereoParameters(_message.Message):
    __slots__ = ("process_name", "tool_name", "optimum_distance_to_target", "optimum_window_scale_factor", "wrist_axis_index", "aruco1_number", "aruco2_number", "distance_between_arucos", "max_aruco_distance_estimate_error", "wait_msecs")
    PROCESS_NAME_FIELD_NUMBER: _ClassVar[int]
    TOOL_NAME_FIELD_NUMBER: _ClassVar[int]
    OPTIMUM_DISTANCE_TO_TARGET_FIELD_NUMBER: _ClassVar[int]
    OPTIMUM_WINDOW_SCALE_FACTOR_FIELD_NUMBER: _ClassVar[int]
    WRIST_AXIS_INDEX_FIELD_NUMBER: _ClassVar[int]
    ARUCO1_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ARUCO2_NUMBER_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_BETWEEN_ARUCOS_FIELD_NUMBER: _ClassVar[int]
    MAX_ARUCO_DISTANCE_ESTIMATE_ERROR_FIELD_NUMBER: _ClassVar[int]
    WAIT_MSECS_FIELD_NUMBER: _ClassVar[int]
    process_name: str
    tool_name: str
    optimum_distance_to_target: float
    optimum_window_scale_factor: float
    wrist_axis_index: int
    aruco1_number: int
    aruco2_number: int
    distance_between_arucos: float
    max_aruco_distance_estimate_error: float
    wait_msecs: int
    def __init__(self, process_name: _Optional[str] = ..., tool_name: _Optional[str] = ..., optimum_distance_to_target: _Optional[float] = ..., optimum_window_scale_factor: _Optional[float] = ..., wrist_axis_index: _Optional[int] = ..., aruco1_number: _Optional[int] = ..., aruco2_number: _Optional[int] = ..., distance_between_arucos: _Optional[float] = ..., max_aruco_distance_estimate_error: _Optional[float] = ..., wait_msecs: _Optional[int] = ...) -> None: ...

class Camera(_message.Message):
    __slots__ = ("name", "number")
    NAME_FIELD_NUMBER: _ClassVar[int]
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    name: CameraName
    number: int
    def __init__(self, name: _Optional[_Union[CameraName, str]] = ..., number: _Optional[int] = ...) -> None: ...

class ParameterValue(_message.Message):
    __slots__ = ("number", "integer", "text", "flag")
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    INTEGER_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    FLAG_FIELD_NUMBER: _ClassVar[int]
    number: float
    integer: int
    text: str
    flag: bool
    def __init__(self, number: _Optional[float] = ..., integer: _Optional[int] = ..., text: _Optional[str] = ..., flag: _Optional[bool] = ...) -> None: ...

class Image(_message.Message):
    __slots__ = ("data", "shape", "dtype")
    DATA_FIELD_NUMBER: _ClassVar[int]
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    DTYPE_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    shape: _containers.RepeatedScalarFieldContainer[int]
    dtype: str
    def __init__(self, data: _Optional[bytes] = ..., shape: _Optional[_Iterable[int]] = ..., dtype: _Optional[str] = ...) -> None: ...

class VisionServerResult(_message.Message):
    __slots__ = ("name", "data")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    name: str
    data: bytes
    def __init__(self, name: _Optional[str] = ..., data: _Optional[bytes] = ...) -> None: ...

class StringList(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class IntList(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, values: _Optional[_Iterable[int]] = ...) -> None: ...

class OptionalDouble(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class Progress(_message.Message):
    __slots__ = ("elapsed", "done", "step")
    ELAPSED_FIELD_NUMBER: _ClassVar[int]
    DONE_FIELD_NUMBER: _ClassVar[int]
    STEP_FIELD_NUMBER: _ClassVar[int]
    elapsed: float
    done: bool
    step: str
    def __init__(self, elapsed: _Optional[float] = ..., done: _Optional[bool] = ..., step: _Optional[str] = ...) -> None: ...
