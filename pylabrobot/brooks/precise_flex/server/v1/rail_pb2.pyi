from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class RailMoveRailRequest(_message.Message):
    __slots__ = ("rail_position",)
    RAIL_POSITION_FIELD_NUMBER: _ClassVar[int]
    rail_position: float
    def __init__(self, rail_position: _Optional[float] = ...) -> None: ...

class RailMoveRailResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
