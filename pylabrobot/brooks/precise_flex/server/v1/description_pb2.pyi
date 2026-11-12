from pylabrobot.brooks.precise_flex.server.v1 import types_pb2 as _types_pb2
from pylabrobot.resources.server.v1 import types_pb2 as _types_pb2_1
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DescribeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Description(_message.Message):
    __slots__ = ("name", "model", "size_x", "size_y", "size_z", "configuration_json", "has_rail", "has_vision", "vision_configuration_json", "vision_server_connected", "gripper", "settings", "resources", "holding")
    NAME_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    SIZE_X_FIELD_NUMBER: _ClassVar[int]
    SIZE_Y_FIELD_NUMBER: _ClassVar[int]
    SIZE_Z_FIELD_NUMBER: _ClassVar[int]
    CONFIGURATION_JSON_FIELD_NUMBER: _ClassVar[int]
    HAS_RAIL_FIELD_NUMBER: _ClassVar[int]
    HAS_VISION_FIELD_NUMBER: _ClassVar[int]
    VISION_CONFIGURATION_JSON_FIELD_NUMBER: _ClassVar[int]
    VISION_SERVER_CONNECTED_FIELD_NUMBER: _ClassVar[int]
    GRIPPER_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_FIELD_NUMBER: _ClassVar[int]
    RESOURCES_FIELD_NUMBER: _ClassVar[int]
    HOLDING_FIELD_NUMBER: _ClassVar[int]
    name: str
    model: str
    size_x: float
    size_y: float
    size_z: float
    configuration_json: str
    has_rail: bool
    has_vision: bool
    vision_configuration_json: str
    vision_server_connected: bool
    gripper: GripperDescription
    settings: Settings
    resources: Resources
    holding: bool
    def __init__(self, name: _Optional[str] = ..., model: _Optional[str] = ..., size_x: _Optional[float] = ..., size_y: _Optional[float] = ..., size_z: _Optional[float] = ..., configuration_json: _Optional[str] = ..., has_rail: _Optional[bool] = ..., has_vision: _Optional[bool] = ..., vision_configuration_json: _Optional[str] = ..., vision_server_connected: _Optional[bool] = ..., gripper: _Optional[_Union[GripperDescription, _Mapping]] = ..., settings: _Optional[_Union[Settings, _Mapping]] = ..., resources: _Optional[_Union[Resources, _Mapping]] = ..., holding: _Optional[bool] = ...) -> None: ...

class GripperDescription(_message.Message):
    __slots__ = ("closed_gripper_position", "jaw_width_range", "is_dual_gripper")
    CLOSED_GRIPPER_POSITION_FIELD_NUMBER: _ClassVar[int]
    JAW_WIDTH_RANGE_FIELD_NUMBER: _ClassVar[int]
    IS_DUAL_GRIPPER_FIELD_NUMBER: _ClassVar[int]
    closed_gripper_position: float
    jaw_width_range: _types_pb2.Range
    is_dual_gripper: bool
    def __init__(self, closed_gripper_position: _Optional[float] = ..., jaw_width_range: _Optional[_Union[_types_pb2.Range, _Mapping]] = ..., is_dual_gripper: _Optional[bool] = ...) -> None: ...

class Resources(_message.Message):
    __slots__ = ("device", "base_plate", "arm", "link_1", "link_2", "gripper")
    DEVICE_FIELD_NUMBER: _ClassVar[int]
    BASE_PLATE_FIELD_NUMBER: _ClassVar[int]
    ARM_FIELD_NUMBER: _ClassVar[int]
    LINK_1_FIELD_NUMBER: _ClassVar[int]
    LINK_2_FIELD_NUMBER: _ClassVar[int]
    GRIPPER_FIELD_NUMBER: _ClassVar[int]
    device: _types_pb2_1.ResourceRef
    base_plate: _types_pb2_1.ResourceRef
    arm: _types_pb2_1.ResourceRef
    link_1: _types_pb2_1.ResourceRef
    link_2: _types_pb2_1.ResourceRef
    gripper: _types_pb2_1.ResourceRef
    def __init__(self, device: _Optional[_Union[_types_pb2_1.ResourceRef, _Mapping]] = ..., base_plate: _Optional[_Union[_types_pb2_1.ResourceRef, _Mapping]] = ..., arm: _Optional[_Union[_types_pb2_1.ResourceRef, _Mapping]] = ..., link_1: _Optional[_Union[_types_pb2_1.ResourceRef, _Mapping]] = ..., link_2: _Optional[_Union[_types_pb2_1.ResourceRef, _Mapping]] = ..., gripper: _Optional[_Union[_types_pb2_1.ResourceRef, _Mapping]] = ...) -> None: ...

class Settings(_message.Message):
    __slots__ = ("arm", "gripper")
    ARM_FIELD_NUMBER: _ClassVar[int]
    GRIPPER_FIELD_NUMBER: _ClassVar[int]
    arm: ArmSettings
    gripper: GripperSettings
    def __init__(self, arm: _Optional[_Union[ArmSettings, _Mapping]] = ..., gripper: _Optional[_Union[GripperSettings, _Mapping]] = ...) -> None: ...

class ArmSettings(_message.Message):
    __slots__ = ("parking_position", "profile_index", "station_index", "station_z_clearance", "horizontal_compliance", "horizontal_compliance_torque", "default_recovery_speed_percent", "default_ztouch_search_speed_percent", "default_ztouch_approach_speed_percent")
    PARKING_POSITION_FIELD_NUMBER: _ClassVar[int]
    PROFILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    STATION_INDEX_FIELD_NUMBER: _ClassVar[int]
    STATION_Z_CLEARANCE_FIELD_NUMBER: _ClassVar[int]
    HORIZONTAL_COMPLIANCE_FIELD_NUMBER: _ClassVar[int]
    HORIZONTAL_COMPLIANCE_TORQUE_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_RECOVERY_SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ZTOUCH_SEARCH_SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ZTOUCH_APPROACH_SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    parking_position: _types_pb2.JointState
    profile_index: int
    station_index: int
    station_z_clearance: float
    horizontal_compliance: bool
    horizontal_compliance_torque: int
    default_recovery_speed_percent: float
    default_ztouch_search_speed_percent: int
    default_ztouch_approach_speed_percent: float
    def __init__(self, parking_position: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ..., profile_index: _Optional[int] = ..., station_index: _Optional[int] = ..., station_z_clearance: _Optional[float] = ..., horizontal_compliance: _Optional[bool] = ..., horizontal_compliance_torque: _Optional[int] = ..., default_recovery_speed_percent: _Optional[float] = ..., default_ztouch_search_speed_percent: _Optional[int] = ..., default_ztouch_approach_speed_percent: _Optional[float] = ...) -> None: ...

class GripperSettings(_message.Message):
    __slots__ = ("default_finger_speed_percent", "default_grasp_force")
    DEFAULT_FINGER_SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_GRASP_FORCE_FIELD_NUMBER: _ClassVar[int]
    default_finger_speed_percent: float
    default_grasp_force: float
    def __init__(self, default_finger_speed_percent: _Optional[float] = ..., default_grasp_force: _Optional[float] = ...) -> None: ...
