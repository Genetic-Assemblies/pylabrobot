from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ErrorKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ERROR_KIND_UNSPECIFIED: _ClassVar[ErrorKind]
    ERROR_KIND_VALUE: _ClassVar[ErrorKind]
    ERROR_KIND_RUNTIME: _ClassVar[ErrorKind]
    ERROR_KIND_TIMEOUT: _ClassVar[ErrorKind]
    ERROR_KIND_KEY: _ClassVar[ErrorKind]
    ERROR_KIND_TYPE: _ClassVar[ErrorKind]
    ERROR_KIND_NOT_IMPLEMENTED: _ClassVar[ErrorKind]
    ERROR_KIND_CONNECTION: _ClassVar[ErrorKind]

class SystemStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SYSTEM_STATUS_IDLE: _ClassVar[SystemStatus]
    SYSTEM_STATUS_SINGLE_CYCLE: _ClassVar[SystemStatus]
    SYSTEM_STATUS_REPEAT_CYCLE: _ClassVar[SystemStatus]
    SYSTEM_STATUS_ERROR: _ClassVar[SystemStatus]
    SYSTEM_STATUS_FINISH: _ClassVar[SystemStatus]

class HeaterBlockStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    HEATER_BLOCK_STATUS_HEATER_OFF: _ClassVar[HeaterBlockStatus]
    HEATER_BLOCK_STATUS_READY: _ClassVar[HeaterBlockStatus]
    HEATER_BLOCK_STATUS_HEATING: _ClassVar[HeaterBlockStatus]
    HEATER_BLOCK_STATUS_COOLING: _ClassVar[HeaterBlockStatus]
    HEATER_BLOCK_STATUS_CONVERGING: _ClassVar[HeaterBlockStatus]
ERROR_KIND_UNSPECIFIED: ErrorKind
ERROR_KIND_VALUE: ErrorKind
ERROR_KIND_RUNTIME: ErrorKind
ERROR_KIND_TIMEOUT: ErrorKind
ERROR_KIND_KEY: ErrorKind
ERROR_KIND_TYPE: ErrorKind
ERROR_KIND_NOT_IMPLEMENTED: ErrorKind
ERROR_KIND_CONNECTION: ErrorKind
SYSTEM_STATUS_IDLE: SystemStatus
SYSTEM_STATUS_SINGLE_CYCLE: SystemStatus
SYSTEM_STATUS_REPEAT_CYCLE: SystemStatus
SYSTEM_STATUS_ERROR: SystemStatus
SYSTEM_STATUS_FINISH: SystemStatus
HEATER_BLOCK_STATUS_HEATER_OFF: HeaterBlockStatus
HEATER_BLOCK_STATUS_READY: HeaterBlockStatus
HEATER_BLOCK_STATUS_HEATING: HeaterBlockStatus
HEATER_BLOCK_STATUS_COOLING: HeaterBlockStatus
HEATER_BLOCK_STATUS_CONVERGING: HeaterBlockStatus

class Error(_message.Message):
    __slots__ = ("kind", "message", "type_name")
    KIND_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TYPE_NAME_FIELD_NUMBER: _ClassVar[int]
    kind: ErrorKind
    message: str
    type_name: str
    def __init__(self, kind: _Optional[_Union[ErrorKind, str]] = ..., message: _Optional[str] = ..., type_name: _Optional[str] = ...) -> None: ...

class SensorStatus(_message.Message):
    __slots__ = ("shuttle_middle_sensor", "shuttle_open_sensor", "shuttle_close_sensor", "clean_door_sensor", "seal_roll_sensor", "heater_motor_up_sensor", "heater_motor_down_sensor")
    SHUTTLE_MIDDLE_SENSOR_FIELD_NUMBER: _ClassVar[int]
    SHUTTLE_OPEN_SENSOR_FIELD_NUMBER: _ClassVar[int]
    SHUTTLE_CLOSE_SENSOR_FIELD_NUMBER: _ClassVar[int]
    CLEAN_DOOR_SENSOR_FIELD_NUMBER: _ClassVar[int]
    SEAL_ROLL_SENSOR_FIELD_NUMBER: _ClassVar[int]
    HEATER_MOTOR_UP_SENSOR_FIELD_NUMBER: _ClassVar[int]
    HEATER_MOTOR_DOWN_SENSOR_FIELD_NUMBER: _ClassVar[int]
    shuttle_middle_sensor: bool
    shuttle_open_sensor: bool
    shuttle_close_sensor: bool
    clean_door_sensor: bool
    seal_roll_sensor: bool
    heater_motor_up_sensor: bool
    heater_motor_down_sensor: bool
    def __init__(self, shuttle_middle_sensor: _Optional[bool] = ..., shuttle_open_sensor: _Optional[bool] = ..., shuttle_close_sensor: _Optional[bool] = ..., clean_door_sensor: _Optional[bool] = ..., seal_roll_sensor: _Optional[bool] = ..., heater_motor_up_sensor: _Optional[bool] = ..., heater_motor_down_sensor: _Optional[bool] = ...) -> None: ...

class A4SStatus(_message.Message):
    __slots__ = ("current_temperature", "system_status", "heater_block_status", "error_code", "warning_code", "sensor_status", "remaining_time")
    CURRENT_TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_STATUS_FIELD_NUMBER: _ClassVar[int]
    HEATER_BLOCK_STATUS_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    WARNING_CODE_FIELD_NUMBER: _ClassVar[int]
    SENSOR_STATUS_FIELD_NUMBER: _ClassVar[int]
    REMAINING_TIME_FIELD_NUMBER: _ClassVar[int]
    current_temperature: float
    system_status: SystemStatus
    heater_block_status: HeaterBlockStatus
    error_code: int
    warning_code: int
    sensor_status: SensorStatus
    remaining_time: int
    def __init__(self, current_temperature: _Optional[float] = ..., system_status: _Optional[_Union[SystemStatus, str]] = ..., heater_block_status: _Optional[_Union[HeaterBlockStatus, str]] = ..., error_code: _Optional[int] = ..., warning_code: _Optional[int] = ..., sensor_status: _Optional[_Union[SensorStatus, _Mapping]] = ..., remaining_time: _Optional[int] = ...) -> None: ...

class Progress(_message.Message):
    __slots__ = ("elapsed", "done", "status")
    ELAPSED_FIELD_NUMBER: _ClassVar[int]
    DONE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    elapsed: float
    done: bool
    status: A4SStatus
    def __init__(self, elapsed: _Optional[float] = ..., done: _Optional[bool] = ..., status: _Optional[_Union[A4SStatus, _Mapping]] = ...) -> None: ...

class Sealer(_message.Message):
    __slots__ = ("name", "port", "timeout")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    name: str
    port: str
    timeout: int
    def __init__(self, name: _Optional[str] = ..., port: _Optional[str] = ..., timeout: _Optional[int] = ...) -> None: ...

class DescribeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DescribeResponse(_message.Message):
    __slots__ = ("sealers",)
    SEALERS_FIELD_NUMBER: _ClassVar[int]
    sealers: _containers.RepeatedCompositeFieldContainer[Sealer]
    def __init__(self, sealers: _Optional[_Iterable[_Union[Sealer, _Mapping]]] = ...) -> None: ...

class SetupRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class StopRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class SendCommandRequest(_message.Message):
    __slots__ = ("name", "command")
    NAME_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    name: str
    command: str
    def __init__(self, name: _Optional[str] = ..., command: _Optional[str] = ...) -> None: ...

class SendCommandResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ReadMessageRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class ReadMessageResponse(_message.Message):
    __slots__ = ("message",)
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: _Optional[str] = ...) -> None: ...

class RequestStatusRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class WaitForStatusRequest(_message.Message):
    __slots__ = ("name", "statuses")
    NAME_FIELD_NUMBER: _ClassVar[int]
    STATUSES_FIELD_NUMBER: _ClassVar[int]
    name: str
    statuses: _containers.RepeatedScalarFieldContainer[SystemStatus]
    def __init__(self, name: _Optional[str] = ..., statuses: _Optional[_Iterable[_Union[SystemStatus, str]]] = ...) -> None: ...

class WaitForShuttleOpenSensorRequest(_message.Message):
    __slots__ = ("name", "shuttle_open", "timeout")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SHUTTLE_OPEN_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    name: str
    shuttle_open: bool
    timeout: float
    def __init__(self, name: _Optional[str] = ..., shuttle_open: _Optional[bool] = ..., timeout: _Optional[float] = ...) -> None: ...

class SystemResetRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class SetHeaterRequest(_message.Message):
    __slots__ = ("name", "on")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ON_FIELD_NUMBER: _ClassVar[int]
    name: str
    on: bool
    def __init__(self, name: _Optional[str] = ..., on: _Optional[bool] = ...) -> None: ...

class SetTimeRequest(_message.Message):
    __slots__ = ("name", "seconds")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SECONDS_FIELD_NUMBER: _ClassVar[int]
    name: str
    seconds: float
    def __init__(self, name: _Optional[str] = ..., seconds: _Optional[float] = ...) -> None: ...

class SetTimeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class RequestRemainingTimeRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class RequestRemainingTimeResponse(_message.Message):
    __slots__ = ("remaining_time",)
    REMAINING_TIME_FIELD_NUMBER: _ClassVar[int]
    remaining_time: int
    def __init__(self, remaining_time: _Optional[int] = ...) -> None: ...

class SealRequest(_message.Message):
    __slots__ = ("name", "temperature", "duration")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    name: str
    temperature: float
    duration: float
    def __init__(self, name: _Optional[str] = ..., temperature: _Optional[float] = ..., duration: _Optional[float] = ...) -> None: ...

class OpenShuttleRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class CloseShuttleRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class SetTemperatureRequest(_message.Message):
    __slots__ = ("name", "temperature")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    name: str
    temperature: float
    def __init__(self, name: _Optional[str] = ..., temperature: _Optional[float] = ...) -> None: ...

class RequestCurrentTemperatureRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class RequestCurrentTemperatureResponse(_message.Message):
    __slots__ = ("temperature",)
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    temperature: float
    def __init__(self, temperature: _Optional[float] = ...) -> None: ...

class DeactivateRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...
