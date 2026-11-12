from pylabrobot.brooks.precise_flex.server.v1 import types_pb2 as _types_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DriverAttachRequest(_message.Message):
    __slots__ = ("attach_state",)
    ATTACH_STATE_FIELD_NUMBER: _ClassVar[int]
    attach_state: int
    def __init__(self, attach_state: _Optional[int] = ...) -> None: ...

class DriverAttachResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class DriverConnectRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverConnectResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverDetachRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverDetachResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverDisconnectRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverDisconnectResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverDiscoverRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverDiscoverResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverHomeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverHomeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverHomeAllRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverHomeAllResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverInitializeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverInitializeResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverNopRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverNopResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverPowerOffRobotRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverPowerOffRobotResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverPowerOnRobotRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverPowerOnRobotResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverReadNextVisionServerResultRequest(_message.Message):
    __slots__ = ("timeout",)
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    timeout: float
    def __init__(self, timeout: _Optional[float] = ...) -> None: ...

class DriverReadNextVisionServerResultResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.VisionServerResult
    def __init__(self, value: _Optional[_Union[_types_pb2.VisionServerResult, _Mapping]] = ...) -> None: ...

class DriverRecoverFromFaultRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRecoverFromFaultResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestAxisCountRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestAxisCountResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class DriverRequestAxisMaskRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestAxisMaskResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class DriverRequestControllerModelRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestControllerModelResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverRequestControllerSerialRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestControllerSerialResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverRequestExtraAxisCountRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestExtraAxisCountResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class DriverRequestGplVersionRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestGplVersionResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverRequestHardwareVersionRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestHardwareVersionResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverRequestManufacturerRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestManufacturerResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverRequestModeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestModeResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.ResponseMode
    def __init__(self, value: _Optional[_Union[_types_pb2.ResponseMode, str]] = ...) -> None: ...

class DriverRequestParameterRequest(_message.Message):
    __slots__ = ("data_id", "unit_number", "sub_unit", "array_index")
    DATA_ID_FIELD_NUMBER: _ClassVar[int]
    UNIT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    SUB_UNIT_FIELD_NUMBER: _ClassVar[int]
    ARRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    data_id: int
    unit_number: int
    sub_unit: int
    array_index: int
    def __init__(self, data_id: _Optional[int] = ..., unit_number: _Optional[int] = ..., sub_unit: _Optional[int] = ..., array_index: _Optional[int] = ...) -> None: ...

class DriverRequestParameterResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverRequestPowerStateRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestPowerStateResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class DriverRequestRobotNameRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestRobotNameResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverRequestRobotTypeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestRobotTypeResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class DriverRequestSelectedRobotRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestSelectedRobotResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class DriverRequestSignalRequest(_message.Message):
    __slots__ = ("signal_number",)
    SIGNAL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    signal_number: int
    def __init__(self, signal_number: _Optional[int] = ...) -> None: ...

class DriverRequestSignalResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class DriverRequestSystemStateRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestSystemStateResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class DriverRequestVersionRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverRequestVersionResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverRequestVisionServerPropertyRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class DriverRequestVisionServerPropertyResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverResetRequest(_message.Message):
    __slots__ = ("robot_number",)
    ROBOT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    robot_number: int
    def __init__(self, robot_number: _Optional[int] = ...) -> None: ...

class DriverResetResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverSelectRobotRequest(_message.Message):
    __slots__ = ("robot_number",)
    ROBOT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    robot_number: int
    def __init__(self, robot_number: _Optional[int] = ...) -> None: ...

class DriverSelectRobotResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverSendCommandRequest(_message.Message):
    __slots__ = ("command", "use_server")
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    USE_SERVER_FIELD_NUMBER: _ClassVar[int]
    command: str
    use_server: _types_pb2.CommandServer
    def __init__(self, command: _Optional[str] = ..., use_server: _Optional[_Union[_types_pb2.CommandServer, str]] = ...) -> None: ...

class DriverSendCommandResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class DriverSetAxisParameterRequest(_message.Message):
    __slots__ = ("data_id", "axis", "value", "robot_number")
    DATA_ID_FIELD_NUMBER: _ClassVar[int]
    AXIS_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ROBOT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    data_id: int
    axis: _types_pb2.Axis
    value: _types_pb2.ParameterValue
    robot_number: int
    def __init__(self, data_id: _Optional[int] = ..., axis: _Optional[_Union[_types_pb2.Axis, str]] = ..., value: _Optional[_Union[_types_pb2.ParameterValue, _Mapping]] = ..., robot_number: _Optional[int] = ...) -> None: ...

class DriverSetAxisParameterResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverSetParameterRequest(_message.Message):
    __slots__ = ("data_id", "value", "unit_number", "sub_unit", "array_index")
    DATA_ID_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    UNIT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    SUB_UNIT_FIELD_NUMBER: _ClassVar[int]
    ARRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    data_id: int
    value: _types_pb2.ParameterValue
    unit_number: int
    sub_unit: int
    array_index: int
    def __init__(self, data_id: _Optional[int] = ..., value: _Optional[_Union[_types_pb2.ParameterValue, _Mapping]] = ..., unit_number: _Optional[int] = ..., sub_unit: _Optional[int] = ..., array_index: _Optional[int] = ...) -> None: ...

class DriverSetParameterResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverSetPowerRequest(_message.Message):
    __slots__ = ("enable", "timeout")
    ENABLE_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    enable: bool
    timeout: int
    def __init__(self, enable: _Optional[bool] = ..., timeout: _Optional[int] = ...) -> None: ...

class DriverSetPowerResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverSetResponseModeRequest(_message.Message):
    __slots__ = ("mode",)
    MODE_FIELD_NUMBER: _ClassVar[int]
    mode: _types_pb2.ResponseMode
    def __init__(self, mode: _Optional[_Union[_types_pb2.ResponseMode, str]] = ...) -> None: ...

class DriverSetResponseModeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverSetSignalRequest(_message.Message):
    __slots__ = ("signal_number", "value")
    SIGNAL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    signal_number: int
    value: int
    def __init__(self, signal_number: _Optional[int] = ..., value: _Optional[int] = ...) -> None: ...

class DriverSetSignalResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverSetupRequest(_message.Message):
    __slots__ = ("skip_home", "skip_vision_setup")
    SKIP_HOME_FIELD_NUMBER: _ClassVar[int]
    SKIP_VISION_SETUP_FIELD_NUMBER: _ClassVar[int]
    skip_home: bool
    skip_vision_setup: bool
    def __init__(self, skip_home: _Optional[bool] = ..., skip_vision_setup: _Optional[bool] = ...) -> None: ...

class DriverSetupResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverStopRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DriverStopResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
