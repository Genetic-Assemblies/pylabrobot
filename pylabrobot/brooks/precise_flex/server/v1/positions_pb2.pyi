from pylabrobot.brooks.precise_flex.server.v1 import types_pb2 as _types_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Position(_message.Message):
    __slots__ = ("name", "joint_state")
    NAME_FIELD_NUMBER: _ClassVar[int]
    JOINT_STATE_FIELD_NUMBER: _ClassVar[int]
    name: str
    joint_state: _types_pb2.JointState
    def __init__(self, name: _Optional[str] = ..., joint_state: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ...) -> None: ...

class Grip(_message.Message):
    __slots__ = ("width", "height", "plate_height")
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    PLATE_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    width: float
    height: float
    plate_height: float
    def __init__(self, width: _Optional[float] = ..., height: _Optional[float] = ..., plate_height: _Optional[float] = ...) -> None: ...

class ListRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListResponse(_message.Message):
    __slots__ = ("positions",)
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    positions: _containers.RepeatedCompositeFieldContainer[Position]
    def __init__(self, positions: _Optional[_Iterable[_Union[Position, _Mapping]]] = ...) -> None: ...

class TeachRequest(_message.Message):
    __slots__ = ("name", "joint_state")
    NAME_FIELD_NUMBER: _ClassVar[int]
    JOINT_STATE_FIELD_NUMBER: _ClassVar[int]
    name: str
    joint_state: _types_pb2.JointState
    def __init__(self, name: _Optional[str] = ..., joint_state: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ...) -> None: ...

class TeachResponse(_message.Message):
    __slots__ = ("position",)
    POSITION_FIELD_NUMBER: _ClassVar[int]
    position: Position
    def __init__(self, position: _Optional[_Union[Position, _Mapping]] = ...) -> None: ...

class ForgetRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class ForgetResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class CarryRequest(_message.Message):
    __slots__ = ("from_position", "to_position", "grip")
    FROM_POSITION_FIELD_NUMBER: _ClassVar[int]
    TO_POSITION_FIELD_NUMBER: _ClassVar[int]
    GRIP_FIELD_NUMBER: _ClassVar[int]
    from_position: str
    to_position: str
    grip: Grip
    def __init__(self, from_position: _Optional[str] = ..., to_position: _Optional[str] = ..., grip: _Optional[_Union[Grip, _Mapping]] = ...) -> None: ...

class GetHoldingRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetHoldingResponse(_message.Message):
    __slots__ = ("holding",)
    HOLDING_FIELD_NUMBER: _ClassVar[int]
    holding: bool
    def __init__(self, holding: _Optional[bool] = ...) -> None: ...
