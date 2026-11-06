from pylabrobot.resources.server.v1 import types_pb2 as _types_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CommandStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMMAND_STATUS_UNSPECIFIED: _ClassVar[CommandStatus]
    COMMAND_STATUS_OK: _ClassVar[CommandStatus]
    COMMAND_STATUS_ERROR: _ClassVar[CommandStatus]
    COMMAND_STATUS_ABORTED: _ClassVar[CommandStatus]
    COMMAND_STATUS_FAIL: _ClassVar[CommandStatus]
    COMMAND_STATUS_RUNNING: _ClassVar[CommandStatus]

class SpinPhase(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SPIN_PHASE_UNSPECIFIED: _ClassVar[SpinPhase]
    SPIN_PHASE_RUNNING: _ClassVar[SpinPhase]
    SPIN_PHASE_FINISHED: _ClassVar[SpinPhase]

class ErrorKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ERROR_KIND_UNSPECIFIED: _ClassVar[ErrorKind]
    ERROR_KIND_VALUE: _ClassVar[ErrorKind]
    ERROR_KIND_RUNTIME: _ClassVar[ErrorKind]
    ERROR_KIND_TIMEOUT: _ClassVar[ErrorKind]
    ERROR_KIND_CONNECTION: _ClassVar[ErrorKind]
    ERROR_KIND_MICROSPIN: _ClassVar[ErrorKind]
    ERROR_KIND_DOOR_LOCK_PIN: _ClassVar[ErrorKind]
    ERROR_KIND_AMPLIFIER_DISABLED: _ClassVar[ErrorKind]
    ERROR_KIND_NOT_HOMED: _ClassVar[ErrorKind]
    ERROR_KIND_QUEUE_TIMEOUT: _ClassVar[ErrorKind]
    ERROR_KIND_ABORTED: _ClassVar[ErrorKind]
    ERROR_KIND_MICROSPIN_TIMEOUT: _ClassVar[ErrorKind]
    ERROR_KIND_PROTOCOL: _ClassVar[ErrorKind]
    ERROR_KIND_RESOURCE_SERVER: _ClassVar[ErrorKind]
COMMAND_STATUS_UNSPECIFIED: CommandStatus
COMMAND_STATUS_OK: CommandStatus
COMMAND_STATUS_ERROR: CommandStatus
COMMAND_STATUS_ABORTED: CommandStatus
COMMAND_STATUS_FAIL: CommandStatus
COMMAND_STATUS_RUNNING: CommandStatus
SPIN_PHASE_UNSPECIFIED: SpinPhase
SPIN_PHASE_RUNNING: SpinPhase
SPIN_PHASE_FINISHED: SpinPhase
ERROR_KIND_UNSPECIFIED: ErrorKind
ERROR_KIND_VALUE: ErrorKind
ERROR_KIND_RUNTIME: ErrorKind
ERROR_KIND_TIMEOUT: ErrorKind
ERROR_KIND_CONNECTION: ErrorKind
ERROR_KIND_MICROSPIN: ErrorKind
ERROR_KIND_DOOR_LOCK_PIN: ErrorKind
ERROR_KIND_AMPLIFIER_DISABLED: ErrorKind
ERROR_KIND_NOT_HOMED: ErrorKind
ERROR_KIND_QUEUE_TIMEOUT: ErrorKind
ERROR_KIND_ABORTED: ErrorKind
ERROR_KIND_MICROSPIN_TIMEOUT: ErrorKind
ERROR_KIND_PROTOCOL: ErrorKind
ERROR_KIND_RESOURCE_SERVER: ErrorKind

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Settings(_message.Message):
    __slots__ = ("default_acceleration", "default_deceleration", "default_timeout", "default_home_timeout", "default_present_timeout", "default_spin_timeout_margin", "default_abort_timeout", "default_spindle_stop_timeout", "default_spindle_poll_interval")
    DEFAULT_ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_DECELERATION_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_HOME_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_PRESENT_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_SPIN_TIMEOUT_MARGIN_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ABORT_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_SPINDLE_STOP_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_SPINDLE_POLL_INTERVAL_FIELD_NUMBER: _ClassVar[int]
    default_acceleration: float
    default_deceleration: float
    default_timeout: float
    default_home_timeout: float
    default_present_timeout: float
    default_spin_timeout_margin: float
    default_abort_timeout: float
    default_spindle_stop_timeout: float
    default_spindle_poll_interval: float
    def __init__(self, default_acceleration: _Optional[float] = ..., default_deceleration: _Optional[float] = ..., default_timeout: _Optional[float] = ..., default_home_timeout: _Optional[float] = ..., default_present_timeout: _Optional[float] = ..., default_spin_timeout_margin: _Optional[float] = ..., default_abort_timeout: _Optional[float] = ..., default_spindle_stop_timeout: _Optional[float] = ..., default_spindle_poll_interval: _Optional[float] = ...) -> None: ...

class Description(_message.Message):
    __slots__ = ("name", "body", "rotor", "bucket_1", "bucket_2", "settings")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    ROTOR_FIELD_NUMBER: _ClassVar[int]
    BUCKET_1_FIELD_NUMBER: _ClassVar[int]
    BUCKET_2_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    body: _types_pb2.ResourceRef
    rotor: _types_pb2.ResourceRef
    bucket_1: _types_pb2.ResourceRef
    bucket_2: _types_pb2.ResourceRef
    settings: Settings
    def __init__(self, name: _Optional[str] = ..., body: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., rotor: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., bucket_1: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., bucket_2: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., settings: _Optional[_Union[Settings, _Mapping]] = ...) -> None: ...

class Version(_message.Message):
    __slots__ = ("fields",)
    class FieldsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    fields: _containers.ScalarMap[str, str]
    def __init__(self, fields: _Optional[_Mapping[str, str]] = ...) -> None: ...

class Homed(_message.Message):
    __slots__ = ("homed",)
    HOMED_FIELD_NUMBER: _ClassVar[int]
    homed: bool
    def __init__(self, homed: _Optional[bool] = ...) -> None: ...

class RequestStatusRequest(_message.Message):
    __slots__ = ("timeout",)
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    timeout: float
    def __init__(self, timeout: _Optional[float] = ...) -> None: ...

class Status(_message.Message):
    __slots__ = ("spindle_position", "door_position")
    SPINDLE_POSITION_FIELD_NUMBER: _ClassVar[int]
    DOOR_POSITION_FIELD_NUMBER: _ClassVar[int]
    spindle_position: int
    door_position: int
    def __init__(self, spindle_position: _Optional[int] = ..., door_position: _Optional[int] = ...) -> None: ...

class RequestErrorsRequest(_message.Message):
    __slots__ = ("count",)
    COUNT_FIELD_NUMBER: _ClassVar[int]
    count: int
    def __init__(self, count: _Optional[int] = ...) -> None: ...

class ErrorEntry(_message.Message):
    __slots__ = ("index", "time", "command_id", "message")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    index: int
    time: str
    command_id: int
    message: str
    def __init__(self, index: _Optional[int] = ..., time: _Optional[str] = ..., command_id: _Optional[int] = ..., message: _Optional[str] = ...) -> None: ...

class ErrorStack(_message.Message):
    __slots__ = ("entries",)
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[ErrorEntry]
    def __init__(self, entries: _Optional[_Iterable[_Union[ErrorEntry, _Mapping]]] = ...) -> None: ...

class RequestCommandStatusRequest(_message.Message):
    __slots__ = ("command_id",)
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    command_id: int
    def __init__(self, command_id: _Optional[int] = ...) -> None: ...

class CommandStatusResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: CommandStatus
    def __init__(self, status: _Optional[_Union[CommandStatus, str]] = ...) -> None: ...

class SpindleVelocity(_message.Message):
    __slots__ = ("rpm",)
    RPM_FIELD_NUMBER: _ClassVar[int]
    rpm: float
    def __init__(self, rpm: _Optional[float] = ...) -> None: ...

class WaitForSpindleStoppedRequest(_message.Message):
    __slots__ = ("timeout", "poll_interval")
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    POLL_INTERVAL_FIELD_NUMBER: _ClassVar[int]
    timeout: float
    poll_interval: float
    def __init__(self, timeout: _Optional[float] = ..., poll_interval: _Optional[float] = ...) -> None: ...

class PresentBucketRequest(_message.Message):
    __slots__ = ("bucket",)
    BUCKET_FIELD_NUMBER: _ClassVar[int]
    bucket: int
    def __init__(self, bucket: _Optional[int] = ...) -> None: ...

class SpinRequest(_message.Message):
    __slots__ = ("request_id", "g", "duration", "acceleration", "deceleration", "timeout")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    G_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    DECELERATION_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    request_id: bytes
    g: float
    duration: float
    acceleration: float
    deceleration: float
    timeout: float
    def __init__(self, request_id: _Optional[bytes] = ..., g: _Optional[float] = ..., duration: _Optional[float] = ..., acceleration: _Optional[float] = ..., deceleration: _Optional[float] = ..., timeout: _Optional[float] = ...) -> None: ...

class SpinUpdate(_message.Message):
    __slots__ = ("request", "phase", "elapsed", "rpm", "error")
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    PHASE_FIELD_NUMBER: _ClassVar[int]
    ELAPSED_FIELD_NUMBER: _ClassVar[int]
    RPM_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    request: SpinRequest
    phase: SpinPhase
    elapsed: float
    rpm: float
    error: Error
    def __init__(self, request: _Optional[_Union[SpinRequest, _Mapping]] = ..., phase: _Optional[_Union[SpinPhase, str]] = ..., elapsed: _Optional[float] = ..., rpm: _Optional[float] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class WatchSpinRequest(_message.Message):
    __slots__ = ("request_id",)
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    request_id: bytes
    def __init__(self, request_id: _Optional[bytes] = ...) -> None: ...

class ResetRequest(_message.Message):
    __slots__ = ("timeout",)
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    timeout: float
    def __init__(self, timeout: _Optional[float] = ...) -> None: ...

class Error(_message.Message):
    __slots__ = ("kind", "message", "command", "command_id", "lines", "timeout", "problem", "resource_name")
    KIND_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    LINES_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    PROBLEM_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_NAME_FIELD_NUMBER: _ClassVar[int]
    kind: ErrorKind
    message: str
    command: str
    command_id: int
    lines: _containers.RepeatedScalarFieldContainer[str]
    timeout: float
    problem: _types_pb2.Problem
    resource_name: str
    def __init__(self, kind: _Optional[_Union[ErrorKind, str]] = ..., message: _Optional[str] = ..., command: _Optional[str] = ..., command_id: _Optional[int] = ..., lines: _Optional[_Iterable[str]] = ..., timeout: _Optional[float] = ..., problem: _Optional[_Union[_types_pb2.Problem, str]] = ..., resource_name: _Optional[str] = ...) -> None: ...
