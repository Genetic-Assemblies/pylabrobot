from pylabrobot.legacy.storage.server.v1 import incubator_pb2 as _incubator_pb2
from pylabrobot.resources.server.v1 import types_pb2 as _types_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Description(_message.Message):
    __slots__ = ("model", "racks", "barcode_scanner")
    MODEL_FIELD_NUMBER: _ClassVar[int]
    RACKS_FIELD_NUMBER: _ClassVar[int]
    BARCODE_SCANNER_FIELD_NUMBER: _ClassVar[int]
    model: str
    racks: _containers.RepeatedCompositeFieldContainer[_incubator_pb2.Rack]
    barcode_scanner: bool
    def __init__(self, model: _Optional[str] = ..., racks: _Optional[_Iterable[_Union[_incubator_pb2.Rack, _Mapping]]] = ..., barcode_scanner: _Optional[bool] = ...) -> None: ...

class FetchPlateToLoadingTrayRequest(_message.Message):
    __slots__ = ("plate", "read_barcode")
    PLATE_FIELD_NUMBER: _ClassVar[int]
    READ_BARCODE_FIELD_NUMBER: _ClassVar[int]
    plate: _incubator_pb2.Plate
    read_barcode: bool
    def __init__(self, plate: _Optional[_Union[_incubator_pb2.Plate, _Mapping]] = ..., read_barcode: _Optional[bool] = ...) -> None: ...

class TakeInPlateRequest(_message.Message):
    __slots__ = ("plate", "site", "read_barcode")
    PLATE_FIELD_NUMBER: _ClassVar[int]
    SITE_FIELD_NUMBER: _ClassVar[int]
    READ_BARCODE_FIELD_NUMBER: _ClassVar[int]
    plate: _incubator_pb2.Plate
    site: _types_pb2.ResourceRef
    read_barcode: bool
    def __init__(self, plate: _Optional[_Union[_incubator_pb2.Plate, _Mapping]] = ..., site: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., read_barcode: _Optional[bool] = ...) -> None: ...

class MovePositionToPositionRequest(_message.Message):
    __slots__ = ("plate", "dest_site", "read_barcode")
    PLATE_FIELD_NUMBER: _ClassVar[int]
    DEST_SITE_FIELD_NUMBER: _ClassVar[int]
    READ_BARCODE_FIELD_NUMBER: _ClassVar[int]
    plate: _incubator_pb2.Plate
    dest_site: _types_pb2.ResourceRef
    read_barcode: bool
    def __init__(self, plate: _Optional[_Union[_incubator_pb2.Plate, _Mapping]] = ..., dest_site: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ..., read_barcode: _Optional[bool] = ...) -> None: ...

class ReadBarcodeInlineRequest(_message.Message):
    __slots__ = ("cassette", "plt_position")
    CASSETTE_FIELD_NUMBER: _ClassVar[int]
    PLT_POSITION_FIELD_NUMBER: _ClassVar[int]
    cassette: int
    plt_position: int
    def __init__(self, cassette: _Optional[int] = ..., plt_position: _Optional[int] = ...) -> None: ...

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

class Co2Level(_message.Message):
    __slots__ = ("co2_level",)
    CO2_LEVEL_FIELD_NUMBER: _ClassVar[int]
    co2_level: float
    def __init__(self, co2_level: _Optional[float] = ...) -> None: ...

class N2Level(_message.Message):
    __slots__ = ("n2_level",)
    N2_LEVEL_FIELD_NUMBER: _ClassVar[int]
    n2_level: float
    def __init__(self, n2_level: _Optional[float] = ...) -> None: ...

class Frequency(_message.Message):
    __slots__ = ("frequency",)
    FREQUENCY_FIELD_NUMBER: _ClassVar[int]
    frequency: float
    def __init__(self, frequency: _Optional[float] = ...) -> None: ...

class TurnSwapStationRequest(_message.Message):
    __slots__ = ("home",)
    HOME_FIELD_NUMBER: _ClassVar[int]
    home: bool
    def __init__(self, home: _Optional[bool] = ...) -> None: ...

class ShakerStatusResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: int
    def __init__(self, status: _Optional[int] = ...) -> None: ...

class Progress(_message.Message):
    __slots__ = ("elapsed", "done", "barcode", "value")
    ELAPSED_FIELD_NUMBER: _ClassVar[int]
    DONE_FIELD_NUMBER: _ClassVar[int]
    BARCODE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    elapsed: float
    done: bool
    barcode: _types_pb2.Barcode
    value: float
    def __init__(self, elapsed: _Optional[float] = ..., done: _Optional[bool] = ..., barcode: _Optional[_Union[_types_pb2.Barcode, _Mapping]] = ..., value: _Optional[float] = ...) -> None: ...
