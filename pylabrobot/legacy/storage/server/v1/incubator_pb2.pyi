from pylabrobot.resources.server.v1 import types_pb2 as _types_pb2
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
    ERROR_KIND_ATTRIBUTE: _ClassVar[ErrorKind]
ERROR_KIND_UNSPECIFIED: ErrorKind
ERROR_KIND_VALUE: ErrorKind
ERROR_KIND_RUNTIME: ErrorKind
ERROR_KIND_TIMEOUT: ErrorKind
ERROR_KIND_KEY: ErrorKind
ERROR_KIND_TYPE: ErrorKind
ERROR_KIND_NOT_IMPLEMENTED: ErrorKind
ERROR_KIND_CONNECTION: ErrorKind
ERROR_KIND_ASSERTION: ErrorKind
ERROR_KIND_ATTRIBUTE: ErrorKind

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Flag(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: bool
    def __init__(self, value: _Optional[bool] = ...) -> None: ...

class Value(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: float
    def __init__(self, value: _Optional[float] = ...) -> None: ...

class Text(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class Site(_message.Message):
    __slots__ = ("name", "index", "size_z")
    NAME_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    SIZE_Z_FIELD_NUMBER: _ClassVar[int]
    name: str
    index: int
    size_z: float
    def __init__(self, name: _Optional[str] = ..., index: _Optional[int] = ..., size_z: _Optional[float] = ...) -> None: ...

class Rack(_message.Message):
    __slots__ = ("name", "model", "sites")
    NAME_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    SITES_FIELD_NUMBER: _ClassVar[int]
    name: str
    model: str
    sites: _containers.RepeatedCompositeFieldContainer[Site]
    def __init__(self, name: _Optional[str] = ..., model: _Optional[str] = ..., sites: _Optional[_Iterable[_Union[Site, _Mapping]]] = ...) -> None: ...

class SetRacksRequest(_message.Message):
    __slots__ = ("racks",)
    RACKS_FIELD_NUMBER: _ClassVar[int]
    racks: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, racks: _Optional[_Iterable[str]] = ...) -> None: ...

class Plate(_message.Message):
    __slots__ = ("name", "site", "barcode")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SITE_FIELD_NUMBER: _ClassVar[int]
    BARCODE_FIELD_NUMBER: _ClassVar[int]
    name: str
    site: _types_pb2.ResourceRef
    barcode: _types_pb2.Barcode
    def __init__(self, name: _Optional[str] = ..., site: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., barcode: _Optional[_Union[_types_pb2.Barcode, _Mapping]] = ...) -> None: ...

class SiteRequest(_message.Message):
    __slots__ = ("site",)
    SITE_FIELD_NUMBER: _ClassVar[int]
    site: _types_pb2.ResourceRef
    def __init__(self, site: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ...) -> None: ...

class Error(_message.Message):
    __slots__ = ("kind", "message", "type_name")
    KIND_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TYPE_NAME_FIELD_NUMBER: _ClassVar[int]
    kind: ErrorKind
    message: str
    type_name: str
    def __init__(self, kind: _Optional[_Union[ErrorKind, str]] = ..., message: _Optional[str] = ..., type_name: _Optional[str] = ...) -> None: ...
