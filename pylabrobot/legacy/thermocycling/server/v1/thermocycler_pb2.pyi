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
    ERROR_KIND_ASSERTION: _ClassVar[ErrorKind]

class LidStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LID_STATUS_IDLE: _ClassVar[LidStatus]
    LID_STATUS_HOLDING_AT_TARGET: _ClassVar[LidStatus]

class BlockStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BLOCK_STATUS_IDLE: _ClassVar[BlockStatus]
    BLOCK_STATUS_HOLDING_AT_TARGET: _ClassVar[BlockStatus]
ERROR_KIND_UNSPECIFIED: ErrorKind
ERROR_KIND_VALUE: ErrorKind
ERROR_KIND_RUNTIME: ErrorKind
ERROR_KIND_TIMEOUT: ErrorKind
ERROR_KIND_KEY: ErrorKind
ERROR_KIND_TYPE: ErrorKind
ERROR_KIND_NOT_IMPLEMENTED: ErrorKind
ERROR_KIND_CONNECTION: ErrorKind
ERROR_KIND_ASSERTION: ErrorKind
LID_STATUS_IDLE: LidStatus
LID_STATUS_HOLDING_AT_TARGET: LidStatus
BLOCK_STATUS_IDLE: BlockStatus
BLOCK_STATUS_HOLDING_AT_TARGET: BlockStatus

class Error(_message.Message):
    __slots__ = ("kind", "message", "type_name")
    KIND_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TYPE_NAME_FIELD_NUMBER: _ClassVar[int]
    kind: ErrorKind
    message: str
    type_name: str
    def __init__(self, kind: _Optional[_Union[ErrorKind, str]] = ..., message: _Optional[str] = ..., type_name: _Optional[str] = ...) -> None: ...

class Step(_message.Message):
    __slots__ = ("temperature", "hold_seconds", "rate")
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    HOLD_SECONDS_FIELD_NUMBER: _ClassVar[int]
    RATE_FIELD_NUMBER: _ClassVar[int]
    temperature: _containers.RepeatedScalarFieldContainer[float]
    hold_seconds: float
    rate: float
    def __init__(self, temperature: _Optional[_Iterable[float]] = ..., hold_seconds: _Optional[float] = ..., rate: _Optional[float] = ...) -> None: ...

class Stage(_message.Message):
    __slots__ = ("steps", "repeats")
    STEPS_FIELD_NUMBER: _ClassVar[int]
    REPEATS_FIELD_NUMBER: _ClassVar[int]
    steps: _containers.RepeatedCompositeFieldContainer[Step]
    repeats: int
    def __init__(self, steps: _Optional[_Iterable[_Union[Step, _Mapping]]] = ..., repeats: _Optional[int] = ...) -> None: ...

class Protocol(_message.Message):
    __slots__ = ("stages",)
    STAGES_FIELD_NUMBER: _ClassVar[int]
    stages: _containers.RepeatedCompositeFieldContainer[Stage]
    def __init__(self, stages: _Optional[_Iterable[_Union[Stage, _Mapping]]] = ...) -> None: ...

class Progress(_message.Message):
    __slots__ = ("elapsed", "done")
    ELAPSED_FIELD_NUMBER: _ClassVar[int]
    DONE_FIELD_NUMBER: _ClassVar[int]
    elapsed: float
    done: bool
    def __init__(self, elapsed: _Optional[float] = ..., done: _Optional[bool] = ...) -> None: ...

class Thermocycler(_message.Message):
    __slots__ = ("name", "backend")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BACKEND_FIELD_NUMBER: _ClassVar[int]
    name: str
    backend: str
    def __init__(self, name: _Optional[str] = ..., backend: _Optional[str] = ...) -> None: ...

class DescribeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DescribeResponse(_message.Message):
    __slots__ = ("thermocyclers",)
    THERMOCYCLERS_FIELD_NUMBER: _ClassVar[int]
    thermocyclers: _containers.RepeatedCompositeFieldContainer[Thermocycler]
    def __init__(self, thermocyclers: _Optional[_Iterable[_Union[Thermocycler, _Mapping]]] = ...) -> None: ...

class SetupRequest(_message.Message):
    __slots__ = ("name", "backend_kwargs")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BACKEND_KWARGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    backend_kwargs: str
    def __init__(self, name: _Optional[str] = ..., backend_kwargs: _Optional[str] = ...) -> None: ...

class StopRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class StopResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class OpenLidRequest(_message.Message):
    __slots__ = ("name", "backend_kwargs")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BACKEND_KWARGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    backend_kwargs: str
    def __init__(self, name: _Optional[str] = ..., backend_kwargs: _Optional[str] = ...) -> None: ...

class CloseLidRequest(_message.Message):
    __slots__ = ("name", "backend_kwargs")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BACKEND_KWARGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    backend_kwargs: str
    def __init__(self, name: _Optional[str] = ..., backend_kwargs: _Optional[str] = ...) -> None: ...

class SetBlockTemperatureRequest(_message.Message):
    __slots__ = ("name", "temperature", "backend_kwargs")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    BACKEND_KWARGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    temperature: _containers.RepeatedScalarFieldContainer[float]
    backend_kwargs: str
    def __init__(self, name: _Optional[str] = ..., temperature: _Optional[_Iterable[float]] = ..., backend_kwargs: _Optional[str] = ...) -> None: ...

class SetLidTemperatureRequest(_message.Message):
    __slots__ = ("name", "temperature", "backend_kwargs")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    BACKEND_KWARGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    temperature: _containers.RepeatedScalarFieldContainer[float]
    backend_kwargs: str
    def __init__(self, name: _Optional[str] = ..., temperature: _Optional[_Iterable[float]] = ..., backend_kwargs: _Optional[str] = ...) -> None: ...

class DeactivateBlockRequest(_message.Message):
    __slots__ = ("name", "backend_kwargs")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BACKEND_KWARGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    backend_kwargs: str
    def __init__(self, name: _Optional[str] = ..., backend_kwargs: _Optional[str] = ...) -> None: ...

class DeactivateBlockResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DeactivateLidRequest(_message.Message):
    __slots__ = ("name", "backend_kwargs")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BACKEND_KWARGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    backend_kwargs: str
    def __init__(self, name: _Optional[str] = ..., backend_kwargs: _Optional[str] = ...) -> None: ...

class DeactivateLidResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class RunProtocolRequest(_message.Message):
    __slots__ = ("name", "protocol", "block_max_volume", "backend_kwargs")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    BLOCK_MAX_VOLUME_FIELD_NUMBER: _ClassVar[int]
    BACKEND_KWARGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    protocol: Protocol
    block_max_volume: float
    backend_kwargs: str
    def __init__(self, name: _Optional[str] = ..., protocol: _Optional[_Union[Protocol, _Mapping]] = ..., block_max_volume: _Optional[float] = ..., backend_kwargs: _Optional[str] = ...) -> None: ...

class GetRequest(_message.Message):
    __slots__ = ("name", "backend_kwargs")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BACKEND_KWARGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    backend_kwargs: str
    def __init__(self, name: _Optional[str] = ..., backend_kwargs: _Optional[str] = ...) -> None: ...

class TemperatureResponse(_message.Message):
    __slots__ = ("temperature",)
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    temperature: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, temperature: _Optional[_Iterable[float]] = ...) -> None: ...

class GetLidOpenResponse(_message.Message):
    __slots__ = ("open",)
    OPEN_FIELD_NUMBER: _ClassVar[int]
    open: bool
    def __init__(self, open: _Optional[bool] = ...) -> None: ...

class GetLidStatusResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: LidStatus
    def __init__(self, status: _Optional[_Union[LidStatus, str]] = ...) -> None: ...

class GetBlockStatusResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: BlockStatus
    def __init__(self, status: _Optional[_Union[BlockStatus, str]] = ...) -> None: ...

class GetHoldTimeResponse(_message.Message):
    __slots__ = ("seconds",)
    SECONDS_FIELD_NUMBER: _ClassVar[int]
    seconds: float
    def __init__(self, seconds: _Optional[float] = ...) -> None: ...

class IntegerResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...
