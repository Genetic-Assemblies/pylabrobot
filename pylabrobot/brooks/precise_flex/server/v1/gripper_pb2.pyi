from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class GripperMoveToJawPositionRequest(_message.Message):
    __slots__ = ("width", "force_sensing")
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    FORCE_SENSING_FIELD_NUMBER: _ClassVar[int]
    width: float
    force_sensing: bool
    def __init__(self, width: _Optional[float] = ..., force_sensing: _Optional[bool] = ...) -> None: ...

class GripperMoveToJawPositionResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GripperMoveToJawPositionFirmwareUnitsRequest(_message.Message):
    __slots__ = ("position", "force_sensing")
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FORCE_SENSING_FIELD_NUMBER: _ClassVar[int]
    position: float
    force_sensing: bool
    def __init__(self, position: _Optional[float] = ..., force_sensing: _Optional[bool] = ...) -> None: ...

class GripperMoveToJawPositionFirmwareUnitsResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GripperSenseEachFullyClosedRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GripperSenseEachFullyClosedResponse(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[bool]
    def __init__(self, values: _Optional[_Iterable[bool]] = ...) -> None: ...

class GripperSenseFullyClosedRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GripperSenseFullyClosedResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: bool
    def __init__(self, value: _Optional[bool] = ...) -> None: ...
