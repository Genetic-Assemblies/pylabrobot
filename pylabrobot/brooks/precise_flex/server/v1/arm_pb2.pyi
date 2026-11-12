from pylabrobot.brooks.precise_flex.server.v1 import types_pb2 as _types_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ArmChangeElbowOrientationRequest(_message.Message):
    __slots__ = ("grip_mode", "close_gripper_without_force_sensing")
    GRIP_MODE_FIELD_NUMBER: _ClassVar[int]
    CLOSE_GRIPPER_WITHOUT_FORCE_SENSING_FIELD_NUMBER: _ClassVar[int]
    grip_mode: int
    close_gripper_without_force_sensing: bool
    def __init__(self, grip_mode: _Optional[int] = ..., close_gripper_without_force_sensing: _Optional[bool] = ...) -> None: ...

class ArmChangeElbowOrientationResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmChangeElbowOrientationByAlgorithmRequest(_message.Message):
    __slots__ = ("grip_mode", "close_gripper_without_force_sensing")
    GRIP_MODE_FIELD_NUMBER: _ClassVar[int]
    CLOSE_GRIPPER_WITHOUT_FORCE_SENSING_FIELD_NUMBER: _ClassVar[int]
    grip_mode: int
    close_gripper_without_force_sensing: bool
    def __init__(self, grip_mode: _Optional[int] = ..., close_gripper_without_force_sensing: _Optional[bool] = ...) -> None: ...

class ArmChangeElbowOrientationByAlgorithmResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmDropAtJointStateRequest(_message.Message):
    __slots__ = ("joint_state", "resource_width")
    JOINT_STATE_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_WIDTH_FIELD_NUMBER: _ClassVar[int]
    joint_state: _types_pb2.JointState
    resource_width: float
    def __init__(self, joint_state: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ..., resource_width: _Optional[float] = ...) -> None: ...

class ArmDropAtJointStateResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmDropAtLocationRequest(_message.Message):
    __slots__ = ("location", "direction", "resource_width", "orientation", "wrist", "rail_position")
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_WIDTH_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    WRIST_FIELD_NUMBER: _ClassVar[int]
    RAIL_POSITION_FIELD_NUMBER: _ClassVar[int]
    location: _types_pb2.Coordinate
    direction: float
    resource_width: float
    orientation: _types_pb2.ElbowOrientation
    wrist: _types_pb2.Wrist
    rail_position: float
    def __init__(self, location: _Optional[_Union[_types_pb2.Coordinate, _Mapping]] = ..., direction: _Optional[float] = ..., resource_width: _Optional[float] = ..., orientation: _Optional[_Union[_types_pb2.ElbowOrientation, str]] = ..., wrist: _Optional[_Union[_types_pb2.Wrist, str]] = ..., rail_position: _Optional[float] = ...) -> None: ...

class ArmDropAtLocationResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmHaltRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmHaltResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmMoveThroughCartesianPosesRequest(_message.Message):
    __slots__ = ("poses", "speed_percent", "blend")
    POSES_FIELD_NUMBER: _ClassVar[int]
    SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    BLEND_FIELD_NUMBER: _ClassVar[int]
    poses: _containers.RepeatedCompositeFieldContainer[_types_pb2.CartesianPose]
    speed_percent: float
    blend: bool
    def __init__(self, poses: _Optional[_Iterable[_Union[_types_pb2.CartesianPose, _Mapping]]] = ..., speed_percent: _Optional[float] = ..., blend: _Optional[bool] = ...) -> None: ...

class ArmMoveThroughCartesianPosesResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmMoveToJointStateRequest(_message.Message):
    __slots__ = ("joint_state", "speed_percent", "close_gripper_without_force_sensing")
    JOINT_STATE_FIELD_NUMBER: _ClassVar[int]
    SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    CLOSE_GRIPPER_WITHOUT_FORCE_SENSING_FIELD_NUMBER: _ClassVar[int]
    joint_state: _types_pb2.JointState
    speed_percent: float
    close_gripper_without_force_sensing: bool
    def __init__(self, joint_state: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ..., speed_percent: _Optional[float] = ..., close_gripper_without_force_sensing: _Optional[bool] = ...) -> None: ...

class ArmMoveToJointStateResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmMoveToLocationRequest(_message.Message):
    __slots__ = ("location", "direction", "speed_percent", "orientation", "wrist", "rail_position")
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    WRIST_FIELD_NUMBER: _ClassVar[int]
    RAIL_POSITION_FIELD_NUMBER: _ClassVar[int]
    location: _types_pb2.Coordinate
    direction: float
    speed_percent: float
    orientation: _types_pb2.ElbowOrientation
    wrist: _types_pb2.Wrist
    rail_position: float
    def __init__(self, location: _Optional[_Union[_types_pb2.Coordinate, _Mapping]] = ..., direction: _Optional[float] = ..., speed_percent: _Optional[float] = ..., orientation: _Optional[_Union[_types_pb2.ElbowOrientation, str]] = ..., wrist: _Optional[_Union[_types_pb2.Wrist, str]] = ..., rail_position: _Optional[float] = ...) -> None: ...

class ArmMoveToLocationResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmParkRequest(_message.Message):
    __slots__ = ("close_gripper_without_force_sensing",)
    CLOSE_GRIPPER_WITHOUT_FORCE_SENSING_FIELD_NUMBER: _ClassVar[int]
    close_gripper_without_force_sensing: bool
    def __init__(self, close_gripper_without_force_sensing: _Optional[bool] = ...) -> None: ...

class ArmParkResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmPickUpAtJointStateRequest(_message.Message):
    __slots__ = ("joint_state", "resource_width", "finger_speed_percent", "grasp_force")
    JOINT_STATE_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_WIDTH_FIELD_NUMBER: _ClassVar[int]
    FINGER_SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    GRASP_FORCE_FIELD_NUMBER: _ClassVar[int]
    joint_state: _types_pb2.JointState
    resource_width: float
    finger_speed_percent: float
    grasp_force: float
    def __init__(self, joint_state: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ..., resource_width: _Optional[float] = ..., finger_speed_percent: _Optional[float] = ..., grasp_force: _Optional[float] = ...) -> None: ...

class ArmPickUpAtJointStateResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmPickUpAtLocationRequest(_message.Message):
    __slots__ = ("location", "direction", "resource_width", "finger_speed_percent", "grasp_force", "orientation", "wrist", "rail_position")
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_WIDTH_FIELD_NUMBER: _ClassVar[int]
    FINGER_SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    GRASP_FORCE_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    WRIST_FIELD_NUMBER: _ClassVar[int]
    RAIL_POSITION_FIELD_NUMBER: _ClassVar[int]
    location: _types_pb2.Coordinate
    direction: float
    resource_width: float
    finger_speed_percent: float
    grasp_force: float
    orientation: _types_pb2.ElbowOrientation
    wrist: _types_pb2.Wrist
    rail_position: float
    def __init__(self, location: _Optional[_Union[_types_pb2.Coordinate, _Mapping]] = ..., direction: _Optional[float] = ..., resource_width: _Optional[float] = ..., finger_speed_percent: _Optional[float] = ..., grasp_force: _Optional[float] = ..., orientation: _Optional[_Union[_types_pb2.ElbowOrientation, str]] = ..., wrist: _Optional[_Union[_types_pb2.Wrist, str]] = ..., rail_position: _Optional[float] = ...) -> None: ...

class ArmPickUpAtLocationResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmProbeZUsingZtouchRequest(_message.Message):
    __slots__ = ("search_start_position", "search_end_position", "approach_speed_percent", "search_speed_percent", "detection_force", "perform_second_measurement_on_lift_off", "post_detection_distance", "move_to_parking_position_after", "read_timeout")
    SEARCH_START_POSITION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_END_POSITION_FIELD_NUMBER: _ClassVar[int]
    APPROACH_SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    SEARCH_SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    DETECTION_FORCE_FIELD_NUMBER: _ClassVar[int]
    PERFORM_SECOND_MEASUREMENT_ON_LIFT_OFF_FIELD_NUMBER: _ClassVar[int]
    POST_DETECTION_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    MOVE_TO_PARKING_POSITION_AFTER_FIELD_NUMBER: _ClassVar[int]
    READ_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    search_start_position: float
    search_end_position: float
    approach_speed_percent: float
    search_speed_percent: int
    detection_force: float
    perform_second_measurement_on_lift_off: bool
    post_detection_distance: float
    move_to_parking_position_after: bool
    read_timeout: float
    def __init__(self, search_start_position: _Optional[float] = ..., search_end_position: _Optional[float] = ..., approach_speed_percent: _Optional[float] = ..., search_speed_percent: _Optional[int] = ..., detection_force: _Optional[float] = ..., perform_second_measurement_on_lift_off: _Optional[bool] = ..., post_detection_distance: _Optional[float] = ..., move_to_parking_position_after: _Optional[bool] = ..., read_timeout: _Optional[float] = ...) -> None: ...

class ArmProbeZUsingZtouchResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRecoverAxesWithinLimitsRequest(_message.Message):
    __slots__ = ("speed_percent", "max_distance")
    SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    MAX_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    speed_percent: float
    max_distance: _types_pb2.OptionalDouble
    def __init__(self, speed_percent: _Optional[float] = ..., max_distance: _Optional[_Union[_types_pb2.OptionalDouble, _Mapping]] = ...) -> None: ...

class ArmRecoverAxesWithinLimitsResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.JointState
    def __init__(self, value: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ...) -> None: ...

class ArmReengageBrakeRequest(_message.Message):
    __slots__ = ("axis",)
    AXIS_FIELD_NUMBER: _ClassVar[int]
    axis: int
    def __init__(self, axis: _Optional[int] = ...) -> None: ...

class ArmReengageBrakeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmReleaseBrakeRequest(_message.Message):
    __slots__ = ("axis",)
    AXIS_FIELD_NUMBER: _ClassVar[int]
    axis: int
    def __init__(self, axis: _Optional[int] = ...) -> None: ...

class ArmReleaseBrakeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestBaseRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestBaseResponse(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, values: _Optional[_Iterable[float]] = ...) -> None: ...

class ArmRequestDestinationJointStateRequest(_message.Message):
    __slots__ = ("mode",)
    MODE_FIELD_NUMBER: _ClassVar[int]
    mode: int
    def __init__(self, mode: _Optional[int] = ...) -> None: ...

class ArmRequestDestinationJointStateResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.JointState
    def __init__(self, value: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ...) -> None: ...

class ArmRequestGripperPoseRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestGripperPoseResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.CartesianPose
    def __init__(self, value: _Optional[_Union[_types_pb2.CartesianPose, _Mapping]] = ...) -> None: ...

class ArmRequestJointLimitsRequest(_message.Message):
    __slots__ = ("hard",)
    HARD_FIELD_NUMBER: _ClassVar[int]
    hard: bool
    def __init__(self, hard: _Optional[bool] = ...) -> None: ...

class ArmRequestJointLimitsResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.JointLimits
    def __init__(self, value: _Optional[_Union[_types_pb2.JointLimits, _Mapping]] = ...) -> None: ...

class ArmRequestJointStateRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestJointStateResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.JointState
    def __init__(self, value: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ...) -> None: ...

class ArmRequestKinematicParametersRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestKinematicParametersResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.KinematicParameters
    def __init__(self, value: _Optional[_Union[_types_pb2.KinematicParameters, _Mapping]] = ...) -> None: ...

class ArmRequestLinkLengthsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestLinkLengthsResponse(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, values: _Optional[_Iterable[float]] = ...) -> None: ...

class ArmRequestMaxAccelerationPercentRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestMaxAccelerationPercentResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestMaxDecelerationPercentRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestMaxDecelerationPercentResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestMaxSpeedPercentRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestMaxSpeedPercentResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestMonitorSpeedRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestMonitorSpeedResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class ArmRequestMotionProfileValuesRequest(_message.Message):
    __slots__ = ("profile",)
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    profile: int
    def __init__(self, profile: _Optional[int] = ...) -> None: ...

class ArmRequestMotionProfileValuesResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.MotionProfile
    def __init__(self, value: _Optional[_Union[_types_pb2.MotionProfile, _Mapping]] = ...) -> None: ...

class ArmRequestPayloadRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestPayloadResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class ArmRequestPoseRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestPoseResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.Pose
    def __init__(self, value: _Optional[_Union[_types_pb2.Pose, _Mapping]] = ...) -> None: ...

class ArmRequestProfileAccelerationRequest(_message.Message):
    __slots__ = ("profile_index",)
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    def __init__(self, profile_index: _Optional[int] = ...) -> None: ...

class ArmRequestProfileAccelerationResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestProfileAccelerationRampRequest(_message.Message):
    __slots__ = ("profile_index",)
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    def __init__(self, profile_index: _Optional[int] = ...) -> None: ...

class ArmRequestProfileAccelerationRampResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestProfileDecelerationRequest(_message.Message):
    __slots__ = ("profile_index",)
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    def __init__(self, profile_index: _Optional[int] = ...) -> None: ...

class ArmRequestProfileDecelerationResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestProfileDecelerationRampRequest(_message.Message):
    __slots__ = ("profile_index",)
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    def __init__(self, profile_index: _Optional[int] = ...) -> None: ...

class ArmRequestProfileDecelerationRampResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestProfileInRangeRequest(_message.Message):
    __slots__ = ("profile_index",)
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    def __init__(self, profile_index: _Optional[int] = ...) -> None: ...

class ArmRequestProfileInRangeResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestProfileSpeedRequest(_message.Message):
    __slots__ = ("profile_index",)
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    def __init__(self, profile_index: _Optional[int] = ...) -> None: ...

class ArmRequestProfileSpeedResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestProfileSpeed2Request(_message.Message):
    __slots__ = ("profile_index",)
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    def __init__(self, profile_index: _Optional[int] = ...) -> None: ...

class ArmRequestProfileSpeed2Response(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestProfileStraightRequest(_message.Message):
    __slots__ = ("profile_index",)
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    def __init__(self, profile_index: _Optional[int] = ...) -> None: ...

class ArmRequestProfileStraightResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: bool
    def __init__(self, value: _Optional[bool] = ...) -> None: ...

class ArmRequestReferenceAccelerationRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestReferenceAccelerationResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.JointState
    def __init__(self, value: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ...) -> None: ...

class ArmRequestReferenceCartesianAccelerationRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestReferenceCartesianAccelerationResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestReferenceCartesianSpeedRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestReferenceCartesianSpeedResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestReferenceSpeedRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestReferenceSpeedResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.JointState
    def __init__(self, value: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ...) -> None: ...

class ArmRequestStateRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestStateResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class ArmRequestToolLengthRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestToolLengthResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class ArmRequestToolTransformationValuesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmRequestToolTransformationValuesResponse(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, values: _Optional[_Iterable[float]] = ...) -> None: ...

class ArmSetBaseRequest(_message.Message):
    __slots__ = ("x_offset", "y_offset", "z_offset", "z_rotation")
    X_OFFSET_FIELD_NUMBER: _ClassVar[int]
    Y_OFFSET_FIELD_NUMBER: _ClassVar[int]
    Z_OFFSET_FIELD_NUMBER: _ClassVar[int]
    Z_ROTATION_FIELD_NUMBER: _ClassVar[int]
    x_offset: float
    y_offset: float
    z_offset: float
    z_rotation: float
    def __init__(self, x_offset: _Optional[float] = ..., y_offset: _Optional[float] = ..., z_offset: _Optional[float] = ..., z_rotation: _Optional[float] = ...) -> None: ...

class ArmSetBaseResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetMonitorSpeedRequest(_message.Message):
    __slots__ = ("speed_percent",)
    SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    speed_percent: int
    def __init__(self, speed_percent: _Optional[int] = ...) -> None: ...

class ArmSetMonitorSpeedResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetMotionProfileValuesRequest(_message.Message):
    __slots__ = ("profile", "speed_percent", "speed2_percent", "acceleration_percent", "deceleration_percent", "acceleration_ramp", "deceleration_ramp", "in_range", "straight")
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    SPEED2_PERCENT_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_PERCENT_FIELD_NUMBER: _ClassVar[int]
    DECELERATION_PERCENT_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_RAMP_FIELD_NUMBER: _ClassVar[int]
    DECELERATION_RAMP_FIELD_NUMBER: _ClassVar[int]
    IN_RANGE_FIELD_NUMBER: _ClassVar[int]
    STRAIGHT_FIELD_NUMBER: _ClassVar[int]
    profile: int
    speed_percent: float
    speed2_percent: float
    acceleration_percent: float
    deceleration_percent: float
    acceleration_ramp: float
    deceleration_ramp: float
    in_range: float
    straight: bool
    def __init__(self, profile: _Optional[int] = ..., speed_percent: _Optional[float] = ..., speed2_percent: _Optional[float] = ..., acceleration_percent: _Optional[float] = ..., deceleration_percent: _Optional[float] = ..., acceleration_ramp: _Optional[float] = ..., deceleration_ramp: _Optional[float] = ..., in_range: _Optional[float] = ..., straight: _Optional[bool] = ...) -> None: ...

class ArmSetMotionProfileValuesResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetPayloadRequest(_message.Message):
    __slots__ = ("payload_percent",)
    PAYLOAD_PERCENT_FIELD_NUMBER: _ClassVar[int]
    payload_percent: int
    def __init__(self, payload_percent: _Optional[int] = ...) -> None: ...

class ArmSetPayloadResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetProfileAccelerationRequest(_message.Message):
    __slots__ = ("profile_index", "acceleration_percent")
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_PERCENT_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    acceleration_percent: float
    def __init__(self, profile_index: _Optional[int] = ..., acceleration_percent: _Optional[float] = ...) -> None: ...

class ArmSetProfileAccelerationResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetProfileAccelerationRampRequest(_message.Message):
    __slots__ = ("profile_index", "acceleration_ramp_seconds")
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_RAMP_SECONDS_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    acceleration_ramp_seconds: float
    def __init__(self, profile_index: _Optional[int] = ..., acceleration_ramp_seconds: _Optional[float] = ...) -> None: ...

class ArmSetProfileAccelerationRampResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetProfileDecelerationRequest(_message.Message):
    __slots__ = ("profile_index", "deceleration_percent")
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    DECELERATION_PERCENT_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    deceleration_percent: float
    def __init__(self, profile_index: _Optional[int] = ..., deceleration_percent: _Optional[float] = ...) -> None: ...

class ArmSetProfileDecelerationResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetProfileDecelerationRampRequest(_message.Message):
    __slots__ = ("profile_index", "deceleration_ramp_seconds")
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    DECELERATION_RAMP_SECONDS_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    deceleration_ramp_seconds: float
    def __init__(self, profile_index: _Optional[int] = ..., deceleration_ramp_seconds: _Optional[float] = ...) -> None: ...

class ArmSetProfileDecelerationRampResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetProfileInRangeRequest(_message.Message):
    __slots__ = ("profile_index", "in_range_value")
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    IN_RANGE_VALUE_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    in_range_value: float
    def __init__(self, profile_index: _Optional[int] = ..., in_range_value: _Optional[float] = ...) -> None: ...

class ArmSetProfileInRangeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetProfileSpeedRequest(_message.Message):
    __slots__ = ("profile_index", "speed_percent")
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    speed_percent: float
    def __init__(self, profile_index: _Optional[int] = ..., speed_percent: _Optional[float] = ...) -> None: ...

class ArmSetProfileSpeedResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetProfileSpeed2Request(_message.Message):
    __slots__ = ("profile_index", "speed2_percent")
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    SPEED2_PERCENT_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    speed2_percent: float
    def __init__(self, profile_index: _Optional[int] = ..., speed2_percent: _Optional[float] = ...) -> None: ...

class ArmSetProfileSpeed2Response(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetProfileStraightRequest(_message.Message):
    __slots__ = ("profile_index", "straight_mode")
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    STRAIGHT_MODE_FIELD_NUMBER: _ClassVar[int]
    profile_index: int
    straight_mode: bool
    def __init__(self, profile_index: _Optional[int] = ..., straight_mode: _Optional[bool] = ...) -> None: ...

class ArmSetProfileStraightResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmSetStationToCurrentJointStateRequest(_message.Message):
    __slots__ = ("station_index",)
    STATION_INDEX_FIELD_NUMBER: _ClassVar[int]
    station_index: int
    def __init__(self, station_index: _Optional[int] = ...) -> None: ...

class ArmSetStationToCurrentJointStateResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmStartFreedriveModeRequest(_message.Message):
    __slots__ = ("free_axes",)
    FREE_AXES_FIELD_NUMBER: _ClassVar[int]
    free_axes: _types_pb2.IntList
    def __init__(self, free_axes: _Optional[_Union[_types_pb2.IntList, _Mapping]] = ...) -> None: ...

class ArmStartFreedriveModeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmStartZeroTorqueRequest(_message.Message):
    __slots__ = ("axis_mask",)
    AXIS_MASK_FIELD_NUMBER: _ClassVar[int]
    axis_mask: int
    def __init__(self, axis_mask: _Optional[int] = ...) -> None: ...

class ArmStartZeroTorqueResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmStopFreedriveModeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmStopFreedriveModeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmStopZeroTorqueRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ArmStopZeroTorqueResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
