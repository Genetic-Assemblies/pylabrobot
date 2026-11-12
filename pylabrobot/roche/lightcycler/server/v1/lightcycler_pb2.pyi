from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ExperimentStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EXPERIMENT_STATUS_UNSPECIFIED: _ClassVar[ExperimentStatus]
    EXPERIMENT_STATUS_PENDING: _ClassVar[ExperimentStatus]
    EXPERIMENT_STATUS_RUNNING: _ClassVar[ExperimentStatus]
    EXPERIMENT_STATUS_COMPLETE: _ClassVar[ExperimentStatus]
    EXPERIMENT_STATUS_ERROR: _ClassVar[ExperimentStatus]

class ErrorKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ERROR_KIND_UNSPECIFIED: _ClassVar[ErrorKind]
    ERROR_KIND_VALUE: _ClassVar[ErrorKind]
    ERROR_KIND_RUNTIME: _ClassVar[ErrorKind]
    ERROR_KIND_TIMEOUT: _ClassVar[ErrorKind]
    ERROR_KIND_KEY: _ClassVar[ErrorKind]
    ERROR_KIND_CONNECTION: _ClassVar[ErrorKind]
    ERROR_KIND_LIGHTCYCLER: _ClassVar[ErrorKind]
    ERROR_KIND_COMMAND_FAILED: _ClassVar[ErrorKind]
    ERROR_KIND_PROTOCOL: _ClassVar[ErrorKind]
    ERROR_KIND_EXPERIMENT_FAILED: _ClassVar[ErrorKind]
    ERROR_KIND_LIGHTCYCLER_TIMEOUT: _ClassVar[ErrorKind]
EXPERIMENT_STATUS_UNSPECIFIED: ExperimentStatus
EXPERIMENT_STATUS_PENDING: ExperimentStatus
EXPERIMENT_STATUS_RUNNING: ExperimentStatus
EXPERIMENT_STATUS_COMPLETE: ExperimentStatus
EXPERIMENT_STATUS_ERROR: ExperimentStatus
ERROR_KIND_UNSPECIFIED: ErrorKind
ERROR_KIND_VALUE: ErrorKind
ERROR_KIND_RUNTIME: ErrorKind
ERROR_KIND_TIMEOUT: ErrorKind
ERROR_KIND_KEY: ErrorKind
ERROR_KIND_CONNECTION: ErrorKind
ERROR_KIND_LIGHTCYCLER: ErrorKind
ERROR_KIND_COMMAND_FAILED: ErrorKind
ERROR_KIND_PROTOCOL: ErrorKind
ERROR_KIND_EXPERIMENT_FAILED: ErrorKind
ERROR_KIND_LIGHTCYCLER_TIMEOUT: ErrorKind

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Status(_message.Message):
    __slots__ = ("state", "controller", "firmware_version", "running_experiment")
    STATE_FIELD_NUMBER: _ClassVar[int]
    CONTROLLER_FIELD_NUMBER: _ClassVar[int]
    FIRMWARE_VERSION_FIELD_NUMBER: _ClassVar[int]
    RUNNING_EXPERIMENT_FIELD_NUMBER: _ClassVar[int]
    state: int
    controller: str
    firmware_version: str
    running_experiment: str
    def __init__(self, state: _Optional[int] = ..., controller: _Optional[str] = ..., firmware_version: _Optional[str] = ..., running_experiment: _Optional[str] = ...) -> None: ...

class TrayState(_message.Message):
    __slots__ = ("open", "plate_loaded", "barcode")
    OPEN_FIELD_NUMBER: _ClassVar[int]
    PLATE_LOADED_FIELD_NUMBER: _ClassVar[int]
    BARCODE_FIELD_NUMBER: _ClassVar[int]
    open: bool
    plate_loaded: bool
    barcode: str
    def __init__(self, open: _Optional[bool] = ..., plate_loaded: _Optional[bool] = ..., barcode: _Optional[str] = ...) -> None: ...

class RequestLogsRequest(_message.Message):
    __slots__ = ("since_id", "limit")
    SINCE_ID_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    since_id: int
    limit: int
    def __init__(self, since_id: _Optional[int] = ..., limit: _Optional[int] = ...) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ("id", "received_at", "kind", "timestamp", "code", "data")
    ID_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_AT_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    id: int
    received_at: float
    kind: str
    timestamp: str
    code: int
    data: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, id: _Optional[int] = ..., received_at: _Optional[float] = ..., kind: _Optional[str] = ..., timestamp: _Optional[str] = ..., code: _Optional[int] = ..., data: _Optional[_Iterable[str]] = ...) -> None: ...

class Logs(_message.Message):
    __slots__ = ("entries",)
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[LogEntry]
    def __init__(self, entries: _Optional[_Iterable[_Union[LogEntry, _Mapping]]] = ...) -> None: ...

class MoveTrayRequest(_message.Message):
    __slots__ = ("timeout",)
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    timeout: float
    def __init__(self, timeout: _Optional[float] = ...) -> None: ...

class Step(_message.Message):
    __slots__ = ("temperature", "hold_seconds", "rate", "acquire", "filter_set", "exposure")
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    HOLD_SECONDS_FIELD_NUMBER: _ClassVar[int]
    RATE_FIELD_NUMBER: _ClassVar[int]
    ACQUIRE_FIELD_NUMBER: _ClassVar[int]
    FILTER_SET_FIELD_NUMBER: _ClassVar[int]
    EXPOSURE_FIELD_NUMBER: _ClassVar[int]
    temperature: _containers.RepeatedScalarFieldContainer[float]
    hold_seconds: float
    rate: float
    acquire: bool
    filter_set: str
    exposure: int
    def __init__(self, temperature: _Optional[_Iterable[float]] = ..., hold_seconds: _Optional[float] = ..., rate: _Optional[float] = ..., acquire: _Optional[bool] = ..., filter_set: _Optional[str] = ..., exposure: _Optional[int] = ...) -> None: ...

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

class ExperimentRequest(_message.Message):
    __slots__ = ("protocol", "well_count", "volume", "experiment_id")
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    WELL_COUNT_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENT_ID_FIELD_NUMBER: _ClassVar[int]
    protocol: Protocol
    well_count: int
    volume: int
    experiment_id: str
    def __init__(self, protocol: _Optional[_Union[Protocol, _Mapping]] = ..., well_count: _Optional[int] = ..., volume: _Optional[int] = ..., experiment_id: _Optional[str] = ...) -> None: ...

class StartExperimentResponse(_message.Message):
    __slots__ = ("experiment_id",)
    EXPERIMENT_ID_FIELD_NUMBER: _ClassVar[int]
    experiment_id: str
    def __init__(self, experiment_id: _Optional[str] = ...) -> None: ...

class Acquisition(_message.Message):
    __slots__ = ("number", "stage_index", "cycle", "step_index", "temperature", "time", "filter_set", "ref_channel", "values")
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    STAGE_INDEX_FIELD_NUMBER: _ClassVar[int]
    CYCLE_FIELD_NUMBER: _ClassVar[int]
    STEP_INDEX_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    FILTER_SET_FIELD_NUMBER: _ClassVar[int]
    REF_CHANNEL_FIELD_NUMBER: _ClassVar[int]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    number: int
    stage_index: int
    cycle: int
    step_index: int
    temperature: float
    time: float
    filter_set: str
    ref_channel: int
    values: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, number: _Optional[int] = ..., stage_index: _Optional[int] = ..., cycle: _Optional[int] = ..., step_index: _Optional[int] = ..., temperature: _Optional[float] = ..., time: _Optional[float] = ..., filter_set: _Optional[str] = ..., ref_channel: _Optional[int] = ..., values: _Optional[_Iterable[int]] = ...) -> None: ...

class Experiment(_message.Message):
    __slots__ = ("id", "status", "protocol", "well_count", "volume", "created_at", "finished_at", "error", "acquisitions_total", "acquisitions")
    ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    WELL_COUNT_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    FINISHED_AT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ACQUISITIONS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    ACQUISITIONS_FIELD_NUMBER: _ClassVar[int]
    id: str
    status: ExperimentStatus
    protocol: Protocol
    well_count: int
    volume: int
    created_at: float
    finished_at: float
    error: str
    acquisitions_total: int
    acquisitions: _containers.RepeatedCompositeFieldContainer[Acquisition]
    def __init__(self, id: _Optional[str] = ..., status: _Optional[_Union[ExperimentStatus, str]] = ..., protocol: _Optional[_Union[Protocol, _Mapping]] = ..., well_count: _Optional[int] = ..., volume: _Optional[int] = ..., created_at: _Optional[float] = ..., finished_at: _Optional[float] = ..., error: _Optional[str] = ..., acquisitions_total: _Optional[int] = ..., acquisitions: _Optional[_Iterable[_Union[Acquisition, _Mapping]]] = ...) -> None: ...

class ExperimentUpdate(_message.Message):
    __slots__ = ("experiment",)
    EXPERIMENT_FIELD_NUMBER: _ClassVar[int]
    experiment: Experiment
    def __init__(self, experiment: _Optional[_Union[Experiment, _Mapping]] = ...) -> None: ...

class ExperimentId(_message.Message):
    __slots__ = ("experiment_id",)
    EXPERIMENT_ID_FIELD_NUMBER: _ClassVar[int]
    experiment_id: str
    def __init__(self, experiment_id: _Optional[str] = ...) -> None: ...

class ListExperimentsRequest(_message.Message):
    __slots__ = ("limit",)
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    limit: int
    def __init__(self, limit: _Optional[int] = ...) -> None: ...

class ExperimentSummary(_message.Message):
    __slots__ = ("id", "status", "created_at", "finished_at", "error", "acquisitions_done", "acquisitions_total")
    ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    FINISHED_AT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ACQUISITIONS_DONE_FIELD_NUMBER: _ClassVar[int]
    ACQUISITIONS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    id: str
    status: ExperimentStatus
    created_at: float
    finished_at: float
    error: str
    acquisitions_done: int
    acquisitions_total: int
    def __init__(self, id: _Optional[str] = ..., status: _Optional[_Union[ExperimentStatus, str]] = ..., created_at: _Optional[float] = ..., finished_at: _Optional[float] = ..., error: _Optional[str] = ..., acquisitions_done: _Optional[int] = ..., acquisitions_total: _Optional[int] = ...) -> None: ...

class ExperimentList(_message.Message):
    __slots__ = ("experiments",)
    EXPERIMENTS_FIELD_NUMBER: _ClassVar[int]
    experiments: _containers.RepeatedCompositeFieldContainer[ExperimentSummary]
    def __init__(self, experiments: _Optional[_Iterable[_Union[ExperimentSummary, _Mapping]]] = ...) -> None: ...

class Error(_message.Message):
    __slots__ = ("kind", "message", "command", "fields", "experiment_id", "reason", "timeout")
    KIND_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENT_ID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    kind: ErrorKind
    message: str
    command: str
    fields: _containers.RepeatedScalarFieldContainer[str]
    experiment_id: str
    reason: str
    timeout: float
    def __init__(self, kind: _Optional[_Union[ErrorKind, str]] = ..., message: _Optional[str] = ..., command: _Optional[str] = ..., fields: _Optional[_Iterable[str]] = ..., experiment_id: _Optional[str] = ..., reason: _Optional[str] = ..., timeout: _Optional[float] = ...) -> None: ...
