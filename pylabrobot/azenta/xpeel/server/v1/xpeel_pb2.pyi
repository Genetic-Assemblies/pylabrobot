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

class SealCheck(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SEAL_CHECK_UNSPECIFIED: _ClassVar[SealCheck]
    SEAL_CHECK_SEAL_DETECTED: _ClassVar[SealCheck]
    SEAL_CHECK_NO_SEAL: _ClassVar[SealCheck]
    SEAL_CHECK_PLATE_NOT_DETECTED: _ClassVar[SealCheck]
ERROR_KIND_UNSPECIFIED: ErrorKind
ERROR_KIND_VALUE: ErrorKind
ERROR_KIND_RUNTIME: ErrorKind
ERROR_KIND_TIMEOUT: ErrorKind
ERROR_KIND_KEY: ErrorKind
ERROR_KIND_TYPE: ErrorKind
ERROR_KIND_NOT_IMPLEMENTED: ErrorKind
ERROR_KIND_CONNECTION: ErrorKind
SEAL_CHECK_UNSPECIFIED: SealCheck
SEAL_CHECK_SEAL_DETECTED: SealCheck
SEAL_CHECK_NO_SEAL: SealCheck
SEAL_CHECK_PLATE_NOT_DETECTED: SealCheck

class Error(_message.Message):
    __slots__ = ("kind", "message", "type_name")
    KIND_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TYPE_NAME_FIELD_NUMBER: _ClassVar[int]
    kind: ErrorKind
    message: str
    type_name: str
    def __init__(self, kind: _Optional[_Union[ErrorKind, str]] = ..., message: _Optional[str] = ..., type_name: _Optional[str] = ...) -> None: ...

class Lines(_message.Message):
    __slots__ = ("lines",)
    LINES_FIELD_NUMBER: _ClassVar[int]
    lines: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, lines: _Optional[_Iterable[str]] = ...) -> None: ...

class TapeRemaining(_message.Message):
    __slots__ = ("supply_remaining", "takeup_remaining")
    SUPPLY_REMAINING_FIELD_NUMBER: _ClassVar[int]
    TAKEUP_REMAINING_FIELD_NUMBER: _ClassVar[int]
    supply_remaining: int
    takeup_remaining: int
    def __init__(self, supply_remaining: _Optional[int] = ..., takeup_remaining: _Optional[int] = ...) -> None: ...

class Progress(_message.Message):
    __slots__ = ("elapsed", "done", "lines", "seal_check", "tape_remaining")
    ELAPSED_FIELD_NUMBER: _ClassVar[int]
    DONE_FIELD_NUMBER: _ClassVar[int]
    LINES_FIELD_NUMBER: _ClassVar[int]
    SEAL_CHECK_FIELD_NUMBER: _ClassVar[int]
    TAPE_REMAINING_FIELD_NUMBER: _ClassVar[int]
    elapsed: float
    done: bool
    lines: Lines
    seal_check: SealCheck
    tape_remaining: TapeRemaining
    def __init__(self, elapsed: _Optional[float] = ..., done: _Optional[bool] = ..., lines: _Optional[_Union[Lines, _Mapping]] = ..., seal_check: _Optional[_Union[SealCheck, str]] = ..., tape_remaining: _Optional[_Union[TapeRemaining, _Mapping]] = ...) -> None: ...

class Peeler(_message.Message):
    __slots__ = ("name", "port", "response_timeout")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    name: str
    port: str
    response_timeout: float
    def __init__(self, name: _Optional[str] = ..., port: _Optional[str] = ..., response_timeout: _Optional[float] = ...) -> None: ...

class DescribeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DescribeResponse(_message.Message):
    __slots__ = ("peelers",)
    PEELERS_FIELD_NUMBER: _ClassVar[int]
    peelers: _containers.RepeatedCompositeFieldContainer[Peeler]
    def __init__(self, peelers: _Optional[_Iterable[_Union[Peeler, _Mapping]]] = ...) -> None: ...

class SetupRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class SetupResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class StopRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class StopResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class SendCommandRequest(_message.Message):
    __slots__ = ("name", "cmd", "expect_ack", "wait_for_ready", "clear_buffer")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CMD_FIELD_NUMBER: _ClassVar[int]
    EXPECT_ACK_FIELD_NUMBER: _ClassVar[int]
    WAIT_FOR_READY_FIELD_NUMBER: _ClassVar[int]
    CLEAR_BUFFER_FIELD_NUMBER: _ClassVar[int]
    name: str
    cmd: str
    expect_ack: bool
    wait_for_ready: bool
    clear_buffer: bool
    def __init__(self, name: _Optional[str] = ..., cmd: _Optional[str] = ..., expect_ack: _Optional[bool] = ..., wait_for_ready: _Optional[bool] = ..., clear_buffer: _Optional[bool] = ...) -> None: ...

class RequestStatusRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class RequestStatusResponse(_message.Message):
    __slots__ = ("first", "second", "third")
    FIRST_FIELD_NUMBER: _ClassVar[int]
    SECOND_FIELD_NUMBER: _ClassVar[int]
    THIRD_FIELD_NUMBER: _ClassVar[int]
    first: int
    second: int
    third: int
    def __init__(self, first: _Optional[int] = ..., second: _Optional[int] = ..., third: _Optional[int] = ...) -> None: ...

class RequestVersionRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class RequestVersionResponse(_message.Message):
    __slots__ = ("lines",)
    LINES_FIELD_NUMBER: _ClassVar[int]
    lines: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, lines: _Optional[_Iterable[str]] = ...) -> None: ...

class ResetRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class SealCheckRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class RequestTapeRemainingRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class EnablePlateCheckRequest(_message.Message):
    __slots__ = ("name", "enabled")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    name: str
    enabled: bool
    def __init__(self, name: _Optional[str] = ..., enabled: _Optional[bool] = ...) -> None: ...

class RequestSealSensorStatusRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class SetSealThresholdUpperRequest(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: int
    def __init__(self, name: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...

class SetSealThresholdLowerRequest(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: int
    def __init__(self, name: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...

class MoveConveyorOutRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class MoveConveyorInRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class MoveElevatorDownRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class MoveElevatorUpRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class AdvanceTapeRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class PeelRequest(_message.Message):
    __slots__ = ("name", "begin_location", "fast", "adhere_time")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BEGIN_LOCATION_FIELD_NUMBER: _ClassVar[int]
    FAST_FIELD_NUMBER: _ClassVar[int]
    ADHERE_TIME_FIELD_NUMBER: _ClassVar[int]
    name: str
    begin_location: int
    fast: bool
    adhere_time: float
    def __init__(self, name: _Optional[str] = ..., begin_location: _Optional[int] = ..., fast: _Optional[bool] = ..., adhere_time: _Optional[float] = ...) -> None: ...

class RestartRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...
