from pylabrobot.resources.server.v1 import types_pb2 as _types_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DoorState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DOOR_STATE_UNSPECIFIED: _ClassVar[DoorState]
    DOOR_STATE_OPEN: _ClassVar[DoorState]
    DOOR_STATE_CLOSED: _ClassVar[DoorState]
    DOOR_STATE_OPENING: _ClassVar[DoorState]
    DOOR_STATE_CLOSING: _ClassVar[DoorState]
    DOOR_STATE_UNKNOWN: _ClassVar[DoorState]

class NestState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NEST_STATE_UNSPECIFIED: _ClassVar[NestState]
    NEST_STATE_CLEAR: _ClassVar[NestState]
    NEST_STATE_OCCUPIED: _ClassVar[NestState]
    NEST_STATE_UNKNOWN: _ClassVar[NestState]

class TransferLocation(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TRANSFER_LOCATION_UNSPECIFIED: _ClassVar[TransferLocation]
    TRANSFER_LOCATION_SOURCE: _ClassVar[TransferLocation]
    TRANSFER_LOCATION_DESTINATION: _ClassVar[TransferLocation]
    TRANSFER_LOCATION_UNASSIGNED: _ClassVar[TransferLocation]

class SiteChoice(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SITE_CHOICE_UNSPECIFIED: _ClassVar[SiteChoice]
    SITE_CHOICE_SMALLEST: _ClassVar[SiteChoice]
    SITE_CHOICE_RANDOM: _ClassVar[SiteChoice]

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
    ERROR_KIND_ATTRIBUTE: _ClassVar[ErrorKind]
DOOR_STATE_UNSPECIFIED: DoorState
DOOR_STATE_OPEN: DoorState
DOOR_STATE_CLOSED: DoorState
DOOR_STATE_OPENING: DoorState
DOOR_STATE_CLOSING: DoorState
DOOR_STATE_UNKNOWN: DoorState
NEST_STATE_UNSPECIFIED: NestState
NEST_STATE_CLEAR: NestState
NEST_STATE_OCCUPIED: NestState
NEST_STATE_UNKNOWN: NestState
TRANSFER_LOCATION_UNSPECIFIED: TransferLocation
TRANSFER_LOCATION_SOURCE: TransferLocation
TRANSFER_LOCATION_DESTINATION: TransferLocation
TRANSFER_LOCATION_UNASSIGNED: TransferLocation
SITE_CHOICE_UNSPECIFIED: SiteChoice
SITE_CHOICE_SMALLEST: SiteChoice
SITE_CHOICE_RANDOM: SiteChoice
ERROR_KIND_UNSPECIFIED: ErrorKind
ERROR_KIND_VALUE: ErrorKind
ERROR_KIND_RUNTIME: ErrorKind
ERROR_KIND_TIMEOUT: ErrorKind
ERROR_KIND_KEY: ErrorKind
ERROR_KIND_TYPE: ErrorKind
ERROR_KIND_NOT_IMPLEMENTED: ErrorKind
ERROR_KIND_CONNECTION: ErrorKind
ERROR_KIND_ATTRIBUTE: ErrorKind

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Site(_message.Message):
    __slots__ = ("name", "slot", "size_z", "plate")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SLOT_FIELD_NUMBER: _ClassVar[int]
    SIZE_Z_FIELD_NUMBER: _ClassVar[int]
    PLATE_FIELD_NUMBER: _ClassVar[int]
    name: str
    slot: int
    size_z: float
    plate: str
    def __init__(self, name: _Optional[str] = ..., slot: _Optional[int] = ..., size_z: _Optional[float] = ..., plate: _Optional[str] = ...) -> None: ...

class Stacker(_message.Message):
    __slots__ = ("number", "name", "definition", "sites")
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DEFINITION_FIELD_NUMBER: _ClassVar[int]
    SITES_FIELD_NUMBER: _ClassVar[int]
    number: int
    name: str
    definition: str
    sites: _containers.RepeatedCompositeFieldContainer[Site]
    def __init__(self, number: _Optional[int] = ..., name: _Optional[str] = ..., definition: _Optional[str] = ..., sites: _Optional[_Iterable[_Union[Site, _Mapping]]] = ...) -> None: ...

class Nest(_message.Message):
    __slots__ = ("tray_index", "number", "name", "plate")
    TRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PLATE_FIELD_NUMBER: _ClassVar[int]
    tray_index: int
    number: int
    name: str
    plate: str
    def __init__(self, tray_index: _Optional[int] = ..., number: _Optional[int] = ..., name: _Optional[str] = ..., plate: _Optional[str] = ...) -> None: ...

class UnresolvedTransfer(_message.Message):
    __slots__ = ("plate", "source", "destination", "command", "error_type", "error_message")
    PLATE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    ERROR_TYPE_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    plate: str
    source: str
    destination: str
    command: str
    error_type: str
    error_message: str
    def __init__(self, plate: _Optional[str] = ..., source: _Optional[str] = ..., destination: _Optional[str] = ..., command: _Optional[str] = ..., error_type: _Optional[str] = ..., error_message: _Optional[str] = ...) -> None: ...

class Description(_message.Message):
    __slots__ = ("name", "model", "read_timeout", "motion_timeout", "stackers", "nests", "unresolved_transfer", "environment")
    NAME_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    READ_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    MOTION_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    STACKERS_FIELD_NUMBER: _ClassVar[int]
    NESTS_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_TRANSFER_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    name: str
    model: str
    read_timeout: float
    motion_timeout: float
    stackers: _containers.RepeatedCompositeFieldContainer[Stacker]
    nests: _containers.RepeatedCompositeFieldContainer[Nest]
    unresolved_transfer: UnresolvedTransfer
    environment: Environment
    def __init__(self, name: _Optional[str] = ..., model: _Optional[str] = ..., read_timeout: _Optional[float] = ..., motion_timeout: _Optional[float] = ..., stackers: _Optional[_Iterable[_Union[Stacker, _Mapping]]] = ..., nests: _Optional[_Iterable[_Union[Nest, _Mapping]]] = ..., unresolved_transfer: _Optional[_Union[UnresolvedTransfer, _Mapping]] = ..., environment: _Optional[_Union[Environment, _Mapping]] = ...) -> None: ...

class PlateDefinition(_message.Message):
    __slots__ = ("name", "definition", "size_z")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DEFINITION_FIELD_NUMBER: _ClassVar[int]
    SIZE_Z_FIELD_NUMBER: _ClassVar[int]
    name: str
    definition: str
    size_z: float
    def __init__(self, name: _Optional[str] = ..., definition: _Optional[str] = ..., size_z: _Optional[float] = ...) -> None: ...

class Placement(_message.Message):
    __slots__ = ("holder", "plate")
    HOLDER_FIELD_NUMBER: _ClassVar[int]
    PLATE_FIELD_NUMBER: _ClassVar[int]
    holder: _types_pb2.ResourceRef
    plate: PlateDefinition
    def __init__(self, holder: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., plate: _Optional[_Union[PlateDefinition, _Mapping]] = ...) -> None: ...

class PlacePlatesRequest(_message.Message):
    __slots__ = ("placements",)
    PLACEMENTS_FIELD_NUMBER: _ClassVar[int]
    placements: _containers.RepeatedCompositeFieldContainer[Placement]
    def __init__(self, placements: _Optional[_Iterable[_Union[Placement, _Mapping]]] = ...) -> None: ...

class Version(_message.Message):
    __slots__ = ("product_name", "serial_number", "firmware_version", "firmware_build", "raw")
    class RawEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    PRODUCT_NAME_FIELD_NUMBER: _ClassVar[int]
    SERIAL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    FIRMWARE_VERSION_FIELD_NUMBER: _ClassVar[int]
    FIRMWARE_BUILD_FIELD_NUMBER: _ClassVar[int]
    RAW_FIELD_NUMBER: _ClassVar[int]
    product_name: str
    serial_number: str
    firmware_version: str
    firmware_build: str
    raw: _containers.ScalarMap[str, str]
    def __init__(self, product_name: _Optional[str] = ..., serial_number: _Optional[str] = ..., firmware_version: _Optional[str] = ..., firmware_build: _Optional[str] = ..., raw: _Optional[_Mapping[str, str]] = ...) -> None: ...

class EnvironmentParameter(_message.Message):
    __slots__ = ("name", "current", "setpoint", "limit")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CURRENT_FIELD_NUMBER: _ClassVar[int]
    SETPOINT_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    name: str
    current: float
    setpoint: float
    limit: float
    def __init__(self, name: _Optional[str] = ..., current: _Optional[float] = ..., setpoint: _Optional[float] = ..., limit: _Optional[float] = ...) -> None: ...

class Environment(_message.Message):
    __slots__ = ("parameters",)
    class ParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: EnvironmentParameter
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[EnvironmentParameter, _Mapping]] = ...) -> None: ...
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    parameters: _containers.MessageMap[str, EnvironmentParameter]
    def __init__(self, parameters: _Optional[_Mapping[str, EnvironmentParameter]] = ...) -> None: ...

class AxisPositions(_message.Message):
    __slots__ = ("positions",)
    class PositionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: float
        def __init__(self, key: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    positions: _containers.ScalarMap[str, float]
    def __init__(self, positions: _Optional[_Mapping[str, float]] = ...) -> None: ...

class Doors(_message.Message):
    __slots__ = ("doors",)
    class DoorsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: DoorState
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[DoorState, str]] = ...) -> None: ...
    DOORS_FIELD_NUMBER: _ClassVar[int]
    doors: _containers.ScalarMap[str, DoorState]
    def __init__(self, doors: _Optional[_Mapping[str, DoorState]] = ...) -> None: ...

class NestStates(_message.Message):
    __slots__ = ("nests",)
    class NestsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: int
        value: NestState
        def __init__(self, key: _Optional[int] = ..., value: _Optional[_Union[NestState, str]] = ...) -> None: ...
    NESTS_FIELD_NUMBER: _ClassVar[int]
    nests: _containers.ScalarMap[int, NestState]
    def __init__(self, nests: _Optional[_Mapping[int, NestState]] = ...) -> None: ...

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

class Lines(_message.Message):
    __slots__ = ("lines",)
    LINES_FIELD_NUMBER: _ClassVar[int]
    lines: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, lines: _Optional[_Iterable[str]] = ...) -> None: ...

class NestRequest(_message.Message):
    __slots__ = ("nest",)
    NEST_FIELD_NUMBER: _ClassVar[int]
    nest: int
    def __init__(self, nest: _Optional[int] = ...) -> None: ...

class StackerDimensions(_message.Message):
    __slots__ = ("stacker", "zero_offset", "slot_height", "slot_count")
    STACKER_FIELD_NUMBER: _ClassVar[int]
    ZERO_OFFSET_FIELD_NUMBER: _ClassVar[int]
    SLOT_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    SLOT_COUNT_FIELD_NUMBER: _ClassVar[int]
    stacker: int
    zero_offset: float
    slot_height: float
    slot_count: int
    def __init__(self, stacker: _Optional[int] = ..., zero_offset: _Optional[float] = ..., slot_height: _Optional[float] = ..., slot_count: _Optional[int] = ...) -> None: ...

class StackerDimensionsList(_message.Message):
    __slots__ = ("stackers",)
    STACKERS_FIELD_NUMBER: _ClassVar[int]
    stackers: _containers.RepeatedCompositeFieldContainer[StackerDimensions]
    def __init__(self, stackers: _Optional[_Iterable[_Union[StackerDimensions, _Mapping]]] = ...) -> None: ...

class Pressures(_message.Message):
    __slots__ = ("pressures",)
    class PressuresEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: float
        def __init__(self, key: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...
    PRESSURES_FIELD_NUMBER: _ClassVar[int]
    pressures: _containers.ScalarMap[str, float]
    def __init__(self, pressures: _Optional[_Mapping[str, float]] = ...) -> None: ...

class SetupRequest(_message.Message):
    __slots__ = ("home",)
    HOME_FIELD_NUMBER: _ClassVar[int]
    home: bool
    def __init__(self, home: _Optional[bool] = ...) -> None: ...

class RequestStackerBarcodesRequest(_message.Message):
    __slots__ = ("number", "all", "slot")
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    ALL_FIELD_NUMBER: _ClassVar[int]
    SLOT_FIELD_NUMBER: _ClassVar[int]
    number: int
    all: bool
    slot: int
    def __init__(self, number: _Optional[int] = ..., all: _Optional[bool] = ..., slot: _Optional[int] = ...) -> None: ...

class ResolveUnresolvedTransferRequest(_message.Message):
    __slots__ = ("location",)
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    location: TransferLocation
    def __init__(self, location: _Optional[_Union[TransferLocation, str]] = ...) -> None: ...

class PlateName(_message.Message):
    __slots__ = ("plate",)
    PLATE_FIELD_NUMBER: _ClassVar[int]
    plate: str
    def __init__(self, plate: _Optional[str] = ...) -> None: ...

class FetchPlateToLoadingTrayRequest(_message.Message):
    __slots__ = ("plate", "tray_index")
    PLATE_FIELD_NUMBER: _ClassVar[int]
    TRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    plate: _types_pb2.ResourceRef
    tray_index: int
    def __init__(self, plate: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., tray_index: _Optional[int] = ...) -> None: ...

class TakeInPlateRequest(_message.Message):
    __slots__ = ("tray_index", "holder", "choice")
    TRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    HOLDER_FIELD_NUMBER: _ClassVar[int]
    CHOICE_FIELD_NUMBER: _ClassVar[int]
    tray_index: int
    holder: _types_pb2.ResourceRef
    choice: SiteChoice
    def __init__(self, tray_index: _Optional[int] = ..., holder: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., choice: _Optional[_Union[SiteChoice, str]] = ...) -> None: ...

class StorePlateRequest(_message.Message):
    __slots__ = ("plate", "site", "tray_index")
    PLATE_FIELD_NUMBER: _ClassVar[int]
    SITE_FIELD_NUMBER: _ClassVar[int]
    TRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    plate: _types_pb2.ResourceRef
    site: _types_pb2.ResourceRef
    tray_index: int
    def __init__(self, plate: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., site: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., tray_index: _Optional[int] = ...) -> None: ...

class TransferPlateBetweenNestsRequest(_message.Message):
    __slots__ = ("source_tray_index", "destination_tray_index")
    SOURCE_TRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_TRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    source_tray_index: int
    destination_tray_index: int
    def __init__(self, source_tray_index: _Optional[int] = ..., destination_tray_index: _Optional[int] = ...) -> None: ...

class Temperature(_message.Message):
    __slots__ = ("temperature",)
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    temperature: float
    def __init__(self, temperature: _Optional[float] = ...) -> None: ...

class Humidity(_message.Message):
    __slots__ = ("humidity",)
    HUMIDITY_FIELD_NUMBER: _ClassVar[int]
    humidity: float
    def __init__(self, humidity: _Optional[float] = ...) -> None: ...

class Co2(_message.Message):
    __slots__ = ("co2",)
    CO2_FIELD_NUMBER: _ClassVar[int]
    co2: float
    def __init__(self, co2: _Optional[float] = ...) -> None: ...

class O2(_message.Message):
    __slots__ = ("o2",)
    O2_FIELD_NUMBER: _ClassVar[int]
    o2: float
    def __init__(self, o2: _Optional[float] = ...) -> None: ...

class Progress(_message.Message):
    __slots__ = ("elapsed", "done", "plate", "value", "lines")
    ELAPSED_FIELD_NUMBER: _ClassVar[int]
    DONE_FIELD_NUMBER: _ClassVar[int]
    PLATE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    LINES_FIELD_NUMBER: _ClassVar[int]
    elapsed: float
    done: bool
    plate: str
    value: bool
    lines: Lines
    def __init__(self, elapsed: _Optional[float] = ..., done: _Optional[bool] = ..., plate: _Optional[str] = ..., value: _Optional[bool] = ..., lines: _Optional[_Union[Lines, _Mapping]] = ...) -> None: ...

class Error(_message.Message):
    __slots__ = ("kind", "message", "type_name", "command", "error_lines", "response", "detail")
    KIND_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TYPE_NAME_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    ERROR_LINES_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    kind: ErrorKind
    message: str
    type_name: str
    command: str
    error_lines: _containers.RepeatedScalarFieldContainer[str]
    response: str
    detail: str
    def __init__(self, kind: _Optional[_Union[ErrorKind, str]] = ..., message: _Optional[str] = ..., type_name: _Optional[str] = ..., command: _Optional[str] = ..., error_lines: _Optional[_Iterable[str]] = ..., response: _Optional[str] = ..., detail: _Optional[str] = ...) -> None: ...
