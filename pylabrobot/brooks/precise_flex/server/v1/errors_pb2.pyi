from pylabrobot.brooks.precise_flex.server.v1 import types_pb2 as _types_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ErrorKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ERROR_KIND_UNSPECIFIED: _ClassVar[ErrorKind]
    ERROR_KIND_PRECISE_FLEX: _ClassVar[ErrorKind]
    ERROR_KIND_OUT_OF_RANGE_OF_MOTION: _ClassVar[ErrorKind]
    ERROR_KIND_IK: _ClassVar[ErrorKind]
    ERROR_KIND_OPERATION_INTERRUPTED: _ClassVar[ErrorKind]
    ERROR_KIND_RESOURCE_SERVER: _ClassVar[ErrorKind]
    ERROR_KIND_NOT_IMPLEMENTED: _ClassVar[ErrorKind]
    ERROR_KIND_TIMEOUT: _ClassVar[ErrorKind]
    ERROR_KIND_CONNECTION: _ClassVar[ErrorKind]
    ERROR_KIND_KEY: _ClassVar[ErrorKind]
    ERROR_KIND_INDEX: _ClassVar[ErrorKind]
    ERROR_KIND_ASSERTION: _ClassVar[ErrorKind]
    ERROR_KIND_TYPE: _ClassVar[ErrorKind]
    ERROR_KIND_VALUE: _ClassVar[ErrorKind]
    ERROR_KIND_RUNTIME: _ClassVar[ErrorKind]
    ERROR_KIND_ATTRIBUTE: _ClassVar[ErrorKind]
ERROR_KIND_UNSPECIFIED: ErrorKind
ERROR_KIND_PRECISE_FLEX: ErrorKind
ERROR_KIND_OUT_OF_RANGE_OF_MOTION: ErrorKind
ERROR_KIND_IK: ErrorKind
ERROR_KIND_OPERATION_INTERRUPTED: ErrorKind
ERROR_KIND_RESOURCE_SERVER: ErrorKind
ERROR_KIND_NOT_IMPLEMENTED: ErrorKind
ERROR_KIND_TIMEOUT: ErrorKind
ERROR_KIND_CONNECTION: ErrorKind
ERROR_KIND_KEY: ErrorKind
ERROR_KIND_INDEX: ErrorKind
ERROR_KIND_ASSERTION: ErrorKind
ERROR_KIND_TYPE: ErrorKind
ERROR_KIND_VALUE: ErrorKind
ERROR_KIND_RUNTIME: ErrorKind
ERROR_KIND_ATTRIBUTE: ErrorKind

class Error(_message.Message):
    __slots__ = ("kind", "message", "type_name", "replycode", "axis_positions", "axis_limits")
    KIND_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TYPE_NAME_FIELD_NUMBER: _ClassVar[int]
    REPLYCODE_FIELD_NUMBER: _ClassVar[int]
    AXIS_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    AXIS_LIMITS_FIELD_NUMBER: _ClassVar[int]
    kind: ErrorKind
    message: str
    type_name: str
    replycode: int
    axis_positions: _types_pb2.JointState
    axis_limits: _types_pb2.JointLimits
    def __init__(self, kind: _Optional[_Union[ErrorKind, str]] = ..., message: _Optional[str] = ..., type_name: _Optional[str] = ..., replycode: _Optional[int] = ..., axis_positions: _Optional[_Union[_types_pb2.JointState, _Mapping]] = ..., axis_limits: _Optional[_Union[_types_pb2.JointLimits, _Mapping]] = ...) -> None: ...
