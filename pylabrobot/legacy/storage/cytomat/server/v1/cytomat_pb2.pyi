from pylabrobot.legacy.storage.server.v1 import incubator_pb2 as _incubator_pb2
from pylabrobot.resources.server.v1 import types_pb2 as _types_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Description(_message.Message):
    __slots__ = ("model", "racks")
    MODEL_FIELD_NUMBER: _ClassVar[int]
    RACKS_FIELD_NUMBER: _ClassVar[int]
    model: str
    racks: _containers.RepeatedCompositeFieldContainer[_incubator_pb2.Rack]
    def __init__(self, model: _Optional[str] = ..., racks: _Optional[_Iterable[_Union[_incubator_pb2.Rack, _Mapping]]] = ...) -> None: ...

class OverviewRegister(_message.Message):
    __slots__ = ("transfer_station_occupied", "device_door_open", "automatic_gate_open", "handler_occupied", "error_register_set", "warning_register_set", "ready_bit_set", "busy_bit_set")
    TRANSFER_STATION_OCCUPIED_FIELD_NUMBER: _ClassVar[int]
    DEVICE_DOOR_OPEN_FIELD_NUMBER: _ClassVar[int]
    AUTOMATIC_GATE_OPEN_FIELD_NUMBER: _ClassVar[int]
    HANDLER_OCCUPIED_FIELD_NUMBER: _ClassVar[int]
    ERROR_REGISTER_SET_FIELD_NUMBER: _ClassVar[int]
    WARNING_REGISTER_SET_FIELD_NUMBER: _ClassVar[int]
    READY_BIT_SET_FIELD_NUMBER: _ClassVar[int]
    BUSY_BIT_SET_FIELD_NUMBER: _ClassVar[int]
    transfer_station_occupied: bool
    device_door_open: bool
    automatic_gate_open: bool
    handler_occupied: bool
    error_register_set: bool
    warning_register_set: bool
    ready_bit_set: bool
    busy_bit_set: bool
    def __init__(self, transfer_station_occupied: _Optional[bool] = ..., device_door_open: _Optional[bool] = ..., automatic_gate_open: _Optional[bool] = ..., handler_occupied: _Optional[bool] = ..., error_register_set: _Optional[bool] = ..., warning_register_set: _Optional[bool] = ..., ready_bit_set: _Optional[bool] = ..., busy_bit_set: _Optional[bool] = ...) -> None: ...

class Register(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class ActionRegisterState(_message.Message):
    __slots__ = ("target", "action")
    TARGET_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    target: str
    action: str
    def __init__(self, target: _Optional[str] = ..., action: _Optional[str] = ...) -> None: ...

class SwapStationState(_message.Message):
    __slots__ = ("position", "load_status_front_of_gate", "load_status_at_processor")
    POSITION_FIELD_NUMBER: _ClassVar[int]
    LOAD_STATUS_FRONT_OF_GATE_FIELD_NUMBER: _ClassVar[int]
    LOAD_STATUS_AT_PROCESSOR_FIELD_NUMBER: _ClassVar[int]
    position: int
    load_status_front_of_gate: int
    load_status_at_processor: int
    def __init__(self, position: _Optional[int] = ..., load_status_front_of_gate: _Optional[int] = ..., load_status_at_processor: _Optional[int] = ...) -> None: ...

class SensorStates(_message.Message):
    __slots__ = ("states",)
    class StatesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: _Optional[bool] = ...) -> None: ...
    STATES_FIELD_NUMBER: _ClassVar[int]
    states: _containers.ScalarMap[str, bool]
    def __init__(self, states: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class IncubationResponse(_message.Message):
    __slots__ = ("nominal_value", "actual_value")
    NOMINAL_VALUE_FIELD_NUMBER: _ClassVar[int]
    ACTUAL_VALUE_FIELD_NUMBER: _ClassVar[int]
    nominal_value: float
    actual_value: float
    def __init__(self, nominal_value: _Optional[float] = ..., actual_value: _Optional[float] = ...) -> None: ...

class SendCommandRequest(_message.Message):
    __slots__ = ("command_type", "command", "params")
    COMMAND_TYPE_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    command_type: str
    command: str
    params: str
    def __init__(self, command_type: _Optional[str] = ..., command: _Optional[str] = ..., params: _Optional[str] = ...) -> None: ...

class OptionalInt(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class SendActionRequest(_message.Message):
    __slots__ = ("command_type", "command", "params", "timeout")
    COMMAND_TYPE_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    command_type: str
    command: str
    params: str
    timeout: OptionalInt
    def __init__(self, command_type: _Optional[str] = ..., command: _Optional[str] = ..., params: _Optional[str] = ..., timeout: _Optional[_Union[OptionalInt, _Mapping]] = ...) -> None: ...

class ReadBarcodeRequest(_message.Message):
    __slots__ = ("site_number_a", "site_number_b")
    SITE_NUMBER_A_FIELD_NUMBER: _ClassVar[int]
    SITE_NUMBER_B_FIELD_NUMBER: _ClassVar[int]
    site_number_a: str
    site_number_b: str
    def __init__(self, site_number_a: _Optional[str] = ..., site_number_b: _Optional[str] = ...) -> None: ...

class WaitForTransferStationRequest(_message.Message):
    __slots__ = ("occupied",)
    OCCUPIED_FIELD_NUMBER: _ClassVar[int]
    occupied: bool
    def __init__(self, occupied: _Optional[bool] = ...) -> None: ...

class WaitForTaskCompletionRequest(_message.Message):
    __slots__ = ("timeout",)
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    timeout: float
    def __init__(self, timeout: _Optional[float] = ...) -> None: ...

class Shakers(_message.Message):
    __slots__ = ("shakers",)
    SHAKERS_FIELD_NUMBER: _ClassVar[int]
    shakers: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, shakers: _Optional[_Iterable[int]] = ...) -> None: ...

class StartShakingRequest(_message.Message):
    __slots__ = ("frequency", "shakers")
    FREQUENCY_FIELD_NUMBER: _ClassVar[int]
    SHAKERS_FIELD_NUMBER: _ClassVar[int]
    frequency: float
    shakers: Shakers
    def __init__(self, frequency: _Optional[float] = ..., shakers: _Optional[_Union[Shakers, _Mapping]] = ...) -> None: ...

class SetShakingFrequencyRequest(_message.Message):
    __slots__ = ("frequency", "shakers")
    FREQUENCY_FIELD_NUMBER: _ClassVar[int]
    SHAKERS_FIELD_NUMBER: _ClassVar[int]
    frequency: int
    shakers: Shakers
    def __init__(self, frequency: _Optional[int] = ..., shakers: _Optional[_Union[Shakers, _Mapping]] = ...) -> None: ...

class Texts(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class IncubationQueryRequest(_message.Message):
    __slots__ = ("query",)
    QUERY_FIELD_NUMBER: _ClassVar[int]
    query: str
    def __init__(self, query: _Optional[str] = ...) -> None: ...

class PlateRequest(_message.Message):
    __slots__ = ("plate",)
    PLATE_FIELD_NUMBER: _ClassVar[int]
    plate: _incubator_pb2.Plate
    def __init__(self, plate: _Optional[_Union[_incubator_pb2.Plate, _Mapping]] = ...) -> None: ...

class TakeInPlateRequest(_message.Message):
    __slots__ = ("plate", "site")
    PLATE_FIELD_NUMBER: _ClassVar[int]
    SITE_FIELD_NUMBER: _ClassVar[int]
    plate: _incubator_pb2.Plate
    site: _types_pb2.ResourceRef
    def __init__(self, plate: _Optional[_Union[_incubator_pb2.Plate, _Mapping]] = ..., site: _Optional[_Union[_types_pb2.ResourceRef, _Mapping]] = ...) -> None: ...

class SetTemperatureRequest(_message.Message):
    __slots__ = ("temperature",)
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    temperature: float
    def __init__(self, temperature: _Optional[float] = ...) -> None: ...

class Progress(_message.Message):
    __slots__ = ("elapsed", "done", "overview")
    ELAPSED_FIELD_NUMBER: _ClassVar[int]
    DONE_FIELD_NUMBER: _ClassVar[int]
    OVERVIEW_FIELD_NUMBER: _ClassVar[int]
    elapsed: float
    done: bool
    overview: OverviewRegister
    def __init__(self, elapsed: _Optional[float] = ..., done: _Optional[bool] = ..., overview: _Optional[_Union[OverviewRegister, _Mapping]] = ...) -> None: ...
