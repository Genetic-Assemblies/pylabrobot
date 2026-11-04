from pylabrobot.hamilton.star.server.v1 import types_pb2 as _types_pb2
from pylabrobot.resources.server.v1 import types_pb2 as _types_pb2_1
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PipettesConfiguration(_message.Message):
    __slots__ = ("hardware_query_first_year", "initialize_y_range", "initialize_begin_of_tip_deposit", "initialize_end_of_tip_deposit", "initialize_z_position_at_end", "initialize_tip_type", "initialize_discarding_method", "initialize_read_timeout", "x_reference_anchor", "y_reference_anchor", "z_reference_anchor", "y_drive_mm_per_increment", "z_drive_mm_per_increment", "z_range_increments", "y_range_increments", "y_drive_speed_range_increments", "y_drive_acceleration_level_range", "y_drive_current_limit_range", "clld_detection_edge_range", "clld_detection_drop_range", "lld_post_detection_distance_range_increments", "lld_max_delta_range_increments", "plld_detection_edge_range", "plld_detection_drop_range", "plld_foam_detection_drop_range", "plld_foam_detection_edge_tolerance_range", "plld_foam_ad_values_range", "plld_foam_search_speed_range_increments", "z_drive_speed_range_increments", "z_drive_acceleration_range_increments", "z_drive_current_limit_range", "z_touch_pwm_range", "drive_parameters", "z_range", "dispensing_drive_mm_per_increment", "dispensing_drive_uL_per_increment", "dispensing_drive_speed_range_increments", "dispensing_drive_acceleration_range_increments", "dispensing_drive_current_limit_range", "dispensing_drive_volume_range_increments", "dispensing_drive_position_range_increments", "dispensing_drive_move_acceleration_range_increments", "blow_out_air_draw_range_increments", "mechanical_clearance_steps_range", "pipetting_volume_range_increments", "pipetting_speed_range_increments", "pipetting_distance_range_increments", "swap_speed_range_increments", "transport_air_volume_range_increments", "blow_out_air_volume_range_increments", "pre_wetting_volume_range_increments", "clot_detection_height_range_increments", "settling_time_range_increments", "mix_cycles_range", "mix_position_range_increments", "second_section_ratio_range_increments", "lld_sensitivity_range", "z_touch_off_position_range_increments", "dual_lld_height_difference_range_increments", "limit_curve_index_range", "stop_back_volume_range_increments", "side_touch_off_distance_range_increments", "channel_size_z", "channels")
    class DriveParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    HARDWARE_QUERY_FIRST_YEAR_FIELD_NUMBER: _ClassVar[int]
    INITIALIZE_Y_RANGE_FIELD_NUMBER: _ClassVar[int]
    INITIALIZE_BEGIN_OF_TIP_DEPOSIT_FIELD_NUMBER: _ClassVar[int]
    INITIALIZE_END_OF_TIP_DEPOSIT_FIELD_NUMBER: _ClassVar[int]
    INITIALIZE_Z_POSITION_AT_END_FIELD_NUMBER: _ClassVar[int]
    INITIALIZE_TIP_TYPE_FIELD_NUMBER: _ClassVar[int]
    INITIALIZE_DISCARDING_METHOD_FIELD_NUMBER: _ClassVar[int]
    INITIALIZE_READ_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    X_REFERENCE_ANCHOR_FIELD_NUMBER: _ClassVar[int]
    Y_REFERENCE_ANCHOR_FIELD_NUMBER: _ClassVar[int]
    Z_REFERENCE_ANCHOR_FIELD_NUMBER: _ClassVar[int]
    Y_DRIVE_MM_PER_INCREMENT_FIELD_NUMBER: _ClassVar[int]
    Z_DRIVE_MM_PER_INCREMENT_FIELD_NUMBER: _ClassVar[int]
    Z_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    Y_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    Y_DRIVE_SPEED_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    Y_DRIVE_ACCELERATION_LEVEL_RANGE_FIELD_NUMBER: _ClassVar[int]
    Y_DRIVE_CURRENT_LIMIT_RANGE_FIELD_NUMBER: _ClassVar[int]
    CLLD_DETECTION_EDGE_RANGE_FIELD_NUMBER: _ClassVar[int]
    CLLD_DETECTION_DROP_RANGE_FIELD_NUMBER: _ClassVar[int]
    LLD_POST_DETECTION_DISTANCE_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    LLD_MAX_DELTA_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    PLLD_DETECTION_EDGE_RANGE_FIELD_NUMBER: _ClassVar[int]
    PLLD_DETECTION_DROP_RANGE_FIELD_NUMBER: _ClassVar[int]
    PLLD_FOAM_DETECTION_DROP_RANGE_FIELD_NUMBER: _ClassVar[int]
    PLLD_FOAM_DETECTION_EDGE_TOLERANCE_RANGE_FIELD_NUMBER: _ClassVar[int]
    PLLD_FOAM_AD_VALUES_RANGE_FIELD_NUMBER: _ClassVar[int]
    PLLD_FOAM_SEARCH_SPEED_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    Z_DRIVE_SPEED_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    Z_DRIVE_ACCELERATION_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    Z_DRIVE_CURRENT_LIMIT_RANGE_FIELD_NUMBER: _ClassVar[int]
    Z_TOUCH_PWM_RANGE_FIELD_NUMBER: _ClassVar[int]
    DRIVE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    Z_RANGE_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_DRIVE_MM_PER_INCREMENT_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_DRIVE_UL_PER_INCREMENT_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_DRIVE_SPEED_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_DRIVE_ACCELERATION_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_DRIVE_CURRENT_LIMIT_RANGE_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_DRIVE_VOLUME_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_DRIVE_POSITION_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_DRIVE_MOVE_ACCELERATION_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    BLOW_OUT_AIR_DRAW_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    MECHANICAL_CLEARANCE_STEPS_RANGE_FIELD_NUMBER: _ClassVar[int]
    PIPETTING_VOLUME_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    PIPETTING_SPEED_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    PIPETTING_DISTANCE_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    SWAP_SPEED_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    TRANSPORT_AIR_VOLUME_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    BLOW_OUT_AIR_VOLUME_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    PRE_WETTING_VOLUME_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    CLOT_DETECTION_HEIGHT_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    SETTLING_TIME_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    MIX_CYCLES_RANGE_FIELD_NUMBER: _ClassVar[int]
    MIX_POSITION_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    SECOND_SECTION_RATIO_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    LLD_SENSITIVITY_RANGE_FIELD_NUMBER: _ClassVar[int]
    Z_TOUCH_OFF_POSITION_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    DUAL_LLD_HEIGHT_DIFFERENCE_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    LIMIT_CURVE_INDEX_RANGE_FIELD_NUMBER: _ClassVar[int]
    STOP_BACK_VOLUME_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    SIDE_TOUCH_OFF_DISTANCE_RANGE_INCREMENTS_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_SIZE_Z_FIELD_NUMBER: _ClassVar[int]
    CHANNELS_FIELD_NUMBER: _ClassVar[int]
    hardware_query_first_year: int
    initialize_y_range: _types_pb2.DoubleRange
    initialize_begin_of_tip_deposit: float
    initialize_end_of_tip_deposit: float
    initialize_z_position_at_end: float
    initialize_tip_type: int
    initialize_discarding_method: int
    initialize_read_timeout: int
    x_reference_anchor: str
    y_reference_anchor: str
    z_reference_anchor: str
    y_drive_mm_per_increment: float
    z_drive_mm_per_increment: float
    z_range_increments: _types_pb2.Int32Range
    y_range_increments: _types_pb2.Int32Range
    y_drive_speed_range_increments: _types_pb2.Int32Range
    y_drive_acceleration_level_range: _types_pb2.Int32Range
    y_drive_current_limit_range: _types_pb2.Int32Range
    clld_detection_edge_range: _types_pb2.Int32Range
    clld_detection_drop_range: _types_pb2.Int32Range
    lld_post_detection_distance_range_increments: _types_pb2.Int32Range
    lld_max_delta_range_increments: _types_pb2.Int32Range
    plld_detection_edge_range: _types_pb2.Int32Range
    plld_detection_drop_range: _types_pb2.Int32Range
    plld_foam_detection_drop_range: _types_pb2.Int32Range
    plld_foam_detection_edge_tolerance_range: _types_pb2.Int32Range
    plld_foam_ad_values_range: _types_pb2.Int32Range
    plld_foam_search_speed_range_increments: _types_pb2.Int32Range
    z_drive_speed_range_increments: _types_pb2.Int32Range
    z_drive_acceleration_range_increments: _types_pb2.Int32Range
    z_drive_current_limit_range: _types_pb2.Int32Range
    z_touch_pwm_range: _types_pb2.Int32Range
    drive_parameters: _containers.ScalarMap[str, int]
    z_range: _types_pb2.DoubleRange
    dispensing_drive_mm_per_increment: float
    dispensing_drive_uL_per_increment: float
    dispensing_drive_speed_range_increments: _types_pb2.Int32Range
    dispensing_drive_acceleration_range_increments: _types_pb2.Int32Range
    dispensing_drive_current_limit_range: _types_pb2.Int32Range
    dispensing_drive_volume_range_increments: _types_pb2.Int32Range
    dispensing_drive_position_range_increments: _types_pb2.Int32Range
    dispensing_drive_move_acceleration_range_increments: _types_pb2.Int32Range
    blow_out_air_draw_range_increments: _types_pb2.Int32Range
    mechanical_clearance_steps_range: _types_pb2.Int32Range
    pipetting_volume_range_increments: _types_pb2.Int32Range
    pipetting_speed_range_increments: _types_pb2.Int32Range
    pipetting_distance_range_increments: _types_pb2.Int32Range
    swap_speed_range_increments: _types_pb2.Int32Range
    transport_air_volume_range_increments: _types_pb2.Int32Range
    blow_out_air_volume_range_increments: _types_pb2.Int32Range
    pre_wetting_volume_range_increments: _types_pb2.Int32Range
    clot_detection_height_range_increments: _types_pb2.Int32Range
    settling_time_range_increments: _types_pb2.Int32Range
    mix_cycles_range: _types_pb2.Int32Range
    mix_position_range_increments: _types_pb2.Int32Range
    second_section_ratio_range_increments: _types_pb2.Int32Range
    lld_sensitivity_range: _types_pb2.Int32Range
    z_touch_off_position_range_increments: _types_pb2.Int32Range
    dual_lld_height_difference_range_increments: _types_pb2.Int32Range
    limit_curve_index_range: _types_pb2.Int32Range
    stop_back_volume_range_increments: _types_pb2.Int32Range
    side_touch_off_distance_range_increments: _types_pb2.Int32Range
    channel_size_z: float
    channels: _containers.RepeatedCompositeFieldContainer[PipetteConfiguration]
    def __init__(self, hardware_query_first_year: _Optional[int] = ..., initialize_y_range: _Optional[_Union[_types_pb2.DoubleRange, _Mapping]] = ..., initialize_begin_of_tip_deposit: _Optional[float] = ..., initialize_end_of_tip_deposit: _Optional[float] = ..., initialize_z_position_at_end: _Optional[float] = ..., initialize_tip_type: _Optional[int] = ..., initialize_discarding_method: _Optional[int] = ..., initialize_read_timeout: _Optional[int] = ..., x_reference_anchor: _Optional[str] = ..., y_reference_anchor: _Optional[str] = ..., z_reference_anchor: _Optional[str] = ..., y_drive_mm_per_increment: _Optional[float] = ..., z_drive_mm_per_increment: _Optional[float] = ..., z_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., y_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., y_drive_speed_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., y_drive_acceleration_level_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., y_drive_current_limit_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., clld_detection_edge_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., clld_detection_drop_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., lld_post_detection_distance_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., lld_max_delta_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., plld_detection_edge_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., plld_detection_drop_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., plld_foam_detection_drop_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., plld_foam_detection_edge_tolerance_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., plld_foam_ad_values_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., plld_foam_search_speed_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., z_drive_speed_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., z_drive_acceleration_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., z_drive_current_limit_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., z_touch_pwm_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., drive_parameters: _Optional[_Mapping[str, int]] = ..., z_range: _Optional[_Union[_types_pb2.DoubleRange, _Mapping]] = ..., dispensing_drive_mm_per_increment: _Optional[float] = ..., dispensing_drive_uL_per_increment: _Optional[float] = ..., dispensing_drive_speed_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., dispensing_drive_acceleration_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., dispensing_drive_current_limit_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., dispensing_drive_volume_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., dispensing_drive_position_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., dispensing_drive_move_acceleration_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., blow_out_air_draw_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., mechanical_clearance_steps_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., pipetting_volume_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., pipetting_speed_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., pipetting_distance_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., swap_speed_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., transport_air_volume_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., blow_out_air_volume_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., pre_wetting_volume_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., clot_detection_height_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., settling_time_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., mix_cycles_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., mix_position_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., second_section_ratio_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., lld_sensitivity_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., z_touch_off_position_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., dual_lld_height_difference_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., limit_curve_index_range: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., stop_back_volume_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., side_touch_off_distance_range_increments: _Optional[_Union[_types_pb2.Int32Range, _Mapping]] = ..., channel_size_z: _Optional[float] = ..., channels: _Optional[_Iterable[_Union[PipetteConfiguration, _Mapping]]] = ...) -> None: ...

class TADMCurve(_message.Message):
    __slots__ = ("measurement_id", "operation", "had_error", "pressures")
    MEASUREMENT_ID_FIELD_NUMBER: _ClassVar[int]
    OPERATION_FIELD_NUMBER: _ClassVar[int]
    HAD_ERROR_FIELD_NUMBER: _ClassVar[int]
    PRESSURES_FIELD_NUMBER: _ClassVar[int]
    measurement_id: str
    operation: _types_pb2.TADMOperation
    had_error: bool
    pressures: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, measurement_id: _Optional[str] = ..., operation: _Optional[_Union[_types_pb2.TADMOperation, str]] = ..., had_error: _Optional[bool] = ..., pressures: _Optional[_Iterable[int]] = ...) -> None: ...

class PipetteMeasurement(_message.Message):
    __slots__ = ("channel", "lld_mode", "liquid_height", "tadm")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    LLD_MODE_FIELD_NUMBER: _ClassVar[int]
    LIQUID_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    TADM_FIELD_NUMBER: _ClassVar[int]
    channel: int
    lld_mode: _types_pb2.LLDMode
    liquid_height: float
    tadm: TADMCurve
    def __init__(self, channel: _Optional[int] = ..., lld_mode: _Optional[_Union[_types_pb2.LLDMode, str]] = ..., liquid_height: _Optional[float] = ..., tadm: _Optional[_Union[TADMCurve, _Mapping]] = ...) -> None: ...

class PipetteMeasurements(_message.Message):
    __slots__ = ("measurements",)
    MEASUREMENTS_FIELD_NUMBER: _ClassVar[int]
    measurements: _containers.RepeatedCompositeFieldContainer[PipetteMeasurement]
    def __init__(self, measurements: _Optional[_Iterable[_Union[PipetteMeasurement, _Mapping]]] = ...) -> None: ...

class PipetteConfiguration(_message.Message):
    __slots__ = ("channel_type", "head_type", "stop_disc_type", "pressure_adc", "firmware_version", "width")
    CHANNEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    HEAD_TYPE_FIELD_NUMBER: _ClassVar[int]
    STOP_DISC_TYPE_FIELD_NUMBER: _ClassVar[int]
    PRESSURE_ADC_FIELD_NUMBER: _ClassVar[int]
    FIRMWARE_VERSION_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    channel_type: _types_pb2.PipetteChannelType
    head_type: _types_pb2.PipetteHeadType
    stop_disc_type: _types_pb2.StopDiscType
    pressure_adc: _types_pb2.PressureADC
    firmware_version: str
    width: float
    def __init__(self, channel_type: _Optional[_Union[_types_pb2.PipetteChannelType, str]] = ..., head_type: _Optional[_Union[_types_pb2.PipetteHeadType, str]] = ..., stop_disc_type: _Optional[_Union[_types_pb2.StopDiscType, str]] = ..., pressure_adc: _Optional[_Union[_types_pb2.PressureADC, str]] = ..., firmware_version: _Optional[str] = ..., width: _Optional[float] = ...) -> None: ...

class PipettesSenseTipPresenceRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesSenseTipPresenceResponse(_message.Message):
    __slots__ = ("presence",)
    PRESENCE_FIELD_NUMBER: _ClassVar[int]
    presence: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, presence: _Optional[_Iterable[int]] = ...) -> None: ...

class PipettesRequestFirmwareVersionRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestFirmwareVersionResponse(_message.Message):
    __slots__ = ("version", "date")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    DATE_FIELD_NUMBER: _ClassVar[int]
    version: str
    date: _types_pb2.Date
    def __init__(self, version: _Optional[str] = ..., date: _Optional[_Union[_types_pb2.Date, _Mapping]] = ...) -> None: ...

class PipettesRequestMinPipetteWidthRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestMinPipetteWidthResponse(_message.Message):
    __slots__ = ("min_pipette_width",)
    MIN_PIPETTE_WIDTH_FIELD_NUMBER: _ClassVar[int]
    min_pipette_width: float
    def __init__(self, min_pipette_width: _Optional[float] = ...) -> None: ...

class PipettesRequestPipetteConfigurationRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestPipetteConfigurationResponse(_message.Message):
    __slots__ = ("configuration",)
    CONFIGURATION_FIELD_NUMBER: _ClassVar[int]
    configuration: PipetteConfiguration
    def __init__(self, configuration: _Optional[_Union[PipetteConfiguration, _Mapping]] = ...) -> None: ...

class PipettesDiscoverRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesDiscoverResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesGetReferencePointLocationsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesGetReferencePointLocationsResponse(_message.Message):
    __slots__ = ("reference_point_locations",)
    REFERENCE_POINT_LOCATIONS_FIELD_NUMBER: _ClassVar[int]
    reference_point_locations: _containers.RepeatedCompositeFieldContainer[_types_pb2.OptionalVec3]
    def __init__(self, reference_point_locations: _Optional[_Iterable[_Union[_types_pb2.OptionalVec3, _Mapping]]] = ...) -> None: ...

class PipettesGetReferencePointLocationRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesGetReferencePointLocationResponse(_message.Message):
    __slots__ = ("reference_point_location",)
    REFERENCE_POINT_LOCATION_FIELD_NUMBER: _ClassVar[int]
    reference_point_location: _types_pb2_1.Vec3
    def __init__(self, reference_point_location: _Optional[_Union[_types_pb2_1.Vec3, _Mapping]] = ...) -> None: ...

class PipettesUpdateLocationsByReferencePointRequest(_message.Message):
    __slots__ = ("positions",)
    class PositionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: int
        value: _types_pb2.ReferencePointYZ
        def __init__(self, key: _Optional[int] = ..., value: _Optional[_Union[_types_pb2.ReferencePointYZ, _Mapping]] = ...) -> None: ...
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    positions: _containers.MessageMap[int, _types_pb2.ReferencePointYZ]
    def __init__(self, positions: _Optional[_Mapping[int, _types_pb2.ReferencePointYZ]] = ...) -> None: ...

class PipettesUpdateLocationsByReferencePointResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesUpdateLocationByReferencePointRequest(_message.Message):
    __slots__ = ("channel", "y", "z")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    channel: int
    y: float
    z: float
    def __init__(self, channel: _Optional[int] = ..., y: _Optional[float] = ..., z: _Optional[float] = ...) -> None: ...

class PipettesUpdateLocationByReferencePointResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesRequestYPositionsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesRequestYPositionsResponse(_message.Message):
    __slots__ = ("y_positions",)
    Y_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    y_positions: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, y_positions: _Optional[_Iterable[float]] = ...) -> None: ...

class PipettesRequestYPositionRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestYPositionResponse(_message.Message):
    __slots__ = ("y_position",)
    Y_POSITION_FIELD_NUMBER: _ClassVar[int]
    y_position: float
    def __init__(self, y_position: _Optional[float] = ...) -> None: ...

class PipettesRequestStopDiscZPositionRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestStopDiscZPositionResponse(_message.Message):
    __slots__ = ("stop_disc_z_position",)
    STOP_DISC_Z_POSITION_FIELD_NUMBER: _ClassVar[int]
    stop_disc_z_position: float
    def __init__(self, stop_disc_z_position: _Optional[float] = ...) -> None: ...

class PipettesRequestStopDiscZPositionsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesRequestStopDiscZPositionsResponse(_message.Message):
    __slots__ = ("stop_disc_z_positions",)
    STOP_DISC_Z_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    stop_disc_z_positions: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, stop_disc_z_positions: _Optional[_Iterable[float]] = ...) -> None: ...

class PipettesRequestToolBottomZPositionsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesRequestToolBottomZPositionsResponse(_message.Message):
    __slots__ = ("tool_bottom_z_positions",)
    TOOL_BOTTOM_Z_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    tool_bottom_z_positions: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, tool_bottom_z_positions: _Optional[_Iterable[float]] = ...) -> None: ...

class PipettesRequestToolBottomZPositionRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestToolBottomZPositionResponse(_message.Message):
    __slots__ = ("tool_bottom_z_position",)
    TOOL_BOTTOM_Z_POSITION_FIELD_NUMBER: _ClassVar[int]
    tool_bottom_z_position: float
    def __init__(self, tool_bottom_z_position: _Optional[float] = ...) -> None: ...

class PipettesRequestTipOverhangRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestTipOverhangResponse(_message.Message):
    __slots__ = ("tip_overhang",)
    TIP_OVERHANG_FIELD_NUMBER: _ClassVar[int]
    tip_overhang: float
    def __init__(self, tip_overhang: _Optional[float] = ...) -> None: ...

class PipettesRequestYSpeedRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestYSpeedResponse(_message.Message):
    __slots__ = ("y_speed",)
    Y_SPEED_FIELD_NUMBER: _ClassVar[int]
    y_speed: float
    def __init__(self, y_speed: _Optional[float] = ...) -> None: ...

class PipettesRequestYAccelerationLevelRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestYAccelerationLevelResponse(_message.Message):
    __slots__ = ("y_acceleration_level",)
    Y_ACCELERATION_LEVEL_FIELD_NUMBER: _ClassVar[int]
    y_acceleration_level: int
    def __init__(self, y_acceleration_level: _Optional[int] = ...) -> None: ...

class PipettesRequestZSpeedRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestZSpeedResponse(_message.Message):
    __slots__ = ("z_speed",)
    Z_SPEED_FIELD_NUMBER: _ClassVar[int]
    z_speed: float
    def __init__(self, z_speed: _Optional[float] = ...) -> None: ...

class PipettesRequestZAccelerationRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestZAccelerationResponse(_message.Message):
    __slots__ = ("z_acceleration",)
    Z_ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    z_acceleration: float
    def __init__(self, z_acceleration: _Optional[float] = ...) -> None: ...

class PipettesRequestXPositionRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesRequestXPositionResponse(_message.Message):
    __slots__ = ("x_position",)
    X_POSITION_FIELD_NUMBER: _ClassVar[int]
    x_position: float
    def __init__(self, x_position: _Optional[float] = ...) -> None: ...

class PipettesMoveToXPositionRequest(_message.Message):
    __slots__ = ("x", "acceleration_level", "current_limit", "settle_reads")
    X_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_LEVEL_FIELD_NUMBER: _ClassVar[int]
    CURRENT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    SETTLE_READS_FIELD_NUMBER: _ClassVar[int]
    x: float
    acceleration_level: int
    current_limit: int
    settle_reads: int
    def __init__(self, x: _Optional[float] = ..., acceleration_level: _Optional[int] = ..., current_limit: _Optional[int] = ..., settle_reads: _Optional[int] = ...) -> None: ...

class PipettesMoveToXPositionResponse(_message.Message):
    __slots__ = ("reply",)
    REPLY_FIELD_NUMBER: _ClassVar[int]
    reply: _types_pb2.FirmwareReply
    def __init__(self, reply: _Optional[_Union[_types_pb2.FirmwareReply, _Mapping]] = ...) -> None: ...

class PipettesMoveToYPositionsRequest(_message.Message):
    __slots__ = ("ys", "make_space")
    class YsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: int
        value: float
        def __init__(self, key: _Optional[int] = ..., value: _Optional[float] = ...) -> None: ...
    YS_FIELD_NUMBER: _ClassVar[int]
    MAKE_SPACE_FIELD_NUMBER: _ClassVar[int]
    ys: _containers.ScalarMap[int, float]
    make_space: bool
    def __init__(self, ys: _Optional[_Mapping[int, float]] = ..., make_space: _Optional[bool] = ...) -> None: ...

class PipettesMoveToYPositionsResponse(_message.Message):
    __slots__ = ("reply",)
    REPLY_FIELD_NUMBER: _ClassVar[int]
    reply: _types_pb2.FirmwareReply
    def __init__(self, reply: _Optional[_Union[_types_pb2.FirmwareReply, _Mapping]] = ...) -> None: ...

class PipettesMoveToYPositionRequest(_message.Message):
    __slots__ = ("channel", "y", "make_space")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    MAKE_SPACE_FIELD_NUMBER: _ClassVar[int]
    channel: int
    y: float
    make_space: bool
    def __init__(self, channel: _Optional[int] = ..., y: _Optional[float] = ..., make_space: _Optional[bool] = ...) -> None: ...

class PipettesMoveToYPositionResponse(_message.Message):
    __slots__ = ("reply",)
    REPLY_FIELD_NUMBER: _ClassVar[int]
    reply: _types_pb2.FirmwareReply
    def __init__(self, reply: _Optional[_Union[_types_pb2.FirmwareReply, _Mapping]] = ...) -> None: ...

class PipettesMakeMaxSpaceForChannelRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesMakeMaxSpaceForChannelResponse(_message.Message):
    __slots__ = ("reply",)
    REPLY_FIELD_NUMBER: _ClassVar[int]
    reply: _types_pb2.FirmwareReply
    def __init__(self, reply: _Optional[_Union[_types_pb2.FirmwareReply, _Mapping]] = ...) -> None: ...

class PipettesMoveStopDiscToZPositionRequest(_message.Message):
    __slots__ = ("channel", "z", "speed", "acceleration", "current_limit")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    CURRENT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    channel: int
    z: float
    speed: float
    acceleration: float
    current_limit: int
    def __init__(self, channel: _Optional[int] = ..., z: _Optional[float] = ..., speed: _Optional[float] = ..., acceleration: _Optional[float] = ..., current_limit: _Optional[int] = ...) -> None: ...

class PipettesMoveStopDiscToZPositionResponse(_message.Message):
    __slots__ = ("reply",)
    REPLY_FIELD_NUMBER: _ClassVar[int]
    reply: _types_pb2.FirmwareReply
    def __init__(self, reply: _Optional[_Union[_types_pb2.FirmwareReply, _Mapping]] = ...) -> None: ...

class PipettesMoveStopDiscToZPositionsRequest(_message.Message):
    __slots__ = ("zs", "speed", "acceleration", "current_limit")
    class ZsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: int
        value: float
        def __init__(self, key: _Optional[int] = ..., value: _Optional[float] = ...) -> None: ...
    ZS_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    CURRENT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    zs: _containers.ScalarMap[int, float]
    speed: float
    acceleration: float
    current_limit: int
    def __init__(self, zs: _Optional[_Mapping[int, float]] = ..., speed: _Optional[float] = ..., acceleration: _Optional[float] = ..., current_limit: _Optional[int] = ...) -> None: ...

class PipettesMoveStopDiscToZPositionsResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesMoveToolBottomToZPositionsRequest(_message.Message):
    __slots__ = ("zs",)
    class ZsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: int
        value: float
        def __init__(self, key: _Optional[int] = ..., value: _Optional[float] = ...) -> None: ...
    ZS_FIELD_NUMBER: _ClassVar[int]
    zs: _containers.ScalarMap[int, float]
    def __init__(self, zs: _Optional[_Mapping[int, float]] = ...) -> None: ...

class PipettesMoveToolBottomToZPositionsResponse(_message.Message):
    __slots__ = ("reply",)
    REPLY_FIELD_NUMBER: _ClassVar[int]
    reply: _types_pb2.FirmwareReply
    def __init__(self, reply: _Optional[_Union[_types_pb2.FirmwareReply, _Mapping]] = ...) -> None: ...

class PipettesMoveToolBottomToZPositionRequest(_message.Message):
    __slots__ = ("channel", "z", "speed", "acceleration", "current_limit")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    CURRENT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    channel: int
    z: float
    speed: float
    acceleration: float
    current_limit: int
    def __init__(self, channel: _Optional[int] = ..., z: _Optional[float] = ..., speed: _Optional[float] = ..., acceleration: _Optional[float] = ..., current_limit: _Optional[int] = ...) -> None: ...

class PipettesMoveToolBottomToZPositionResponse(_message.Message):
    __slots__ = ("reply",)
    REPLY_FIELD_NUMBER: _ClassVar[int]
    reply: _types_pb2.FirmwareReply
    def __init__(self, reply: _Optional[_Union[_types_pb2.FirmwareReply, _Mapping]] = ...) -> None: ...

class PipettesProbeZMaxRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesProbeZMaxResponse(_message.Message):
    __slots__ = ("z_max",)
    Z_MAX_FIELD_NUMBER: _ClassVar[int]
    z_max: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, z_max: _Optional[_Iterable[float]] = ...) -> None: ...

class PipettesMoveToSafeZRequest(_message.Message):
    __slots__ = ("speed", "acceleration")
    SPEED_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    speed: float
    acceleration: float
    def __init__(self, speed: _Optional[float] = ..., acceleration: _Optional[float] = ...) -> None: ...

class PipettesMoveToSafeZResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesDispensingDriveRequestULPositionRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesDispensingDriveRequestULPositionResponse(_message.Message):
    __slots__ = ("position",)
    POSITION_FIELD_NUMBER: _ClassVar[int]
    position: float
    def __init__(self, position: _Optional[float] = ...) -> None: ...

class PipettesGetPistonPositionsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesGetPistonPositionsResponse(_message.Message):
    __slots__ = ("piston_positions",)
    PISTON_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    piston_positions: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, piston_positions: _Optional[_Iterable[float]] = ...) -> None: ...

class PipettesDispensingDrivesRequestULPositionsRequest(_message.Message):
    __slots__ = ("use_channels",)
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    use_channels: _types_pb2.Int32List
    def __init__(self, use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ...) -> None: ...

class PipettesDispensingDrivesRequestULPositionsResponse(_message.Message):
    __slots__ = ("positions",)
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    positions: _containers.RepeatedCompositeFieldContainer[_types_pb2.OptionalDouble]
    def __init__(self, positions: _Optional[_Iterable[_Union[_types_pb2.OptionalDouble, _Mapping]]] = ...) -> None: ...

class PipettesMoveToXyPositionsRequest(_message.Message):
    __slots__ = ("x", "ys", "make_space", "minimum_traverse_height_start")
    class YsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: int
        value: float
        def __init__(self, key: _Optional[int] = ..., value: _Optional[float] = ...) -> None: ...
    X_FIELD_NUMBER: _ClassVar[int]
    YS_FIELD_NUMBER: _ClassVar[int]
    MAKE_SPACE_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    x: float
    ys: _containers.ScalarMap[int, float]
    make_space: bool
    minimum_traverse_height_start: float
    def __init__(self, x: _Optional[float] = ..., ys: _Optional[_Mapping[int, float]] = ..., make_space: _Optional[bool] = ..., minimum_traverse_height_start: _Optional[float] = ...) -> None: ...

class PipettesMoveToXyPositionsResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesSpreadChannelsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesSpreadChannelsResponse(_message.Message):
    __slots__ = ("reply",)
    REPLY_FIELD_NUMBER: _ClassVar[int]
    reply: _types_pb2.FirmwareReply
    def __init__(self, reply: _Optional[_Union[_types_pb2.FirmwareReply, _Mapping]] = ...) -> None: ...

class PipettesGetToolsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesGetToolsResponse(_message.Message):
    __slots__ = ("tools",)
    TOOLS_FIELD_NUMBER: _ClassVar[int]
    tools: _containers.RepeatedCompositeFieldContainer[_types_pb2.OptionalResourceNode]
    def __init__(self, tools: _Optional[_Iterable[_Union[_types_pb2.OptionalResourceNode, _Mapping]]] = ...) -> None: ...

class PipettesGetMountedTipsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesGetMountedTipsResponse(_message.Message):
    __slots__ = ("mounted_tips",)
    MOUNTED_TIPS_FIELD_NUMBER: _ClassVar[int]
    mounted_tips: _containers.RepeatedCompositeFieldContainer[_types_pb2.OptionalResourceNode]
    def __init__(self, mounted_tips: _Optional[_Iterable[_Union[_types_pb2.OptionalResourceNode, _Mapping]]] = ...) -> None: ...

class PipettesGetMountedTipRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesGetMountedTipResponse(_message.Message):
    __slots__ = ("mounted_tip",)
    MOUNTED_TIP_FIELD_NUMBER: _ClassVar[int]
    mounted_tip: _types_pb2_1.ResourceNode
    def __init__(self, mounted_tip: _Optional[_Union[_types_pb2_1.ResourceNode, _Mapping]] = ...) -> None: ...

class PipettesDispensingDriveMoveToULPositionRequest(_message.Message):
    __slots__ = ("channel", "position", "flow_rate", "acceleration", "current_limit")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FLOW_RATE_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    CURRENT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    channel: int
    position: float
    flow_rate: float
    acceleration: float
    current_limit: int
    def __init__(self, channel: _Optional[int] = ..., position: _Optional[float] = ..., flow_rate: _Optional[float] = ..., acceleration: _Optional[float] = ..., current_limit: _Optional[int] = ...) -> None: ...

class PipettesDispensingDriveMoveToULPositionResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesEmptyTipRequest(_message.Message):
    __slots__ = ("channel", "position", "flow_rate", "acceleration", "current_limit", "reset_dispensing_drive_after")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FLOW_RATE_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    CURRENT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    RESET_DISPENSING_DRIVE_AFTER_FIELD_NUMBER: _ClassVar[int]
    channel: int
    position: float
    flow_rate: float
    acceleration: float
    current_limit: int
    reset_dispensing_drive_after: bool
    def __init__(self, channel: _Optional[int] = ..., position: _Optional[float] = ..., flow_rate: _Optional[float] = ..., acceleration: _Optional[float] = ..., current_limit: _Optional[int] = ..., reset_dispensing_drive_after: _Optional[bool] = ...) -> None: ...

class PipettesEmptyTipResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesEmptyTipsRequest(_message.Message):
    __slots__ = ("use_channels", "position", "flow_rate", "acceleration", "current_limit", "reset_dispensing_drive_after")
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FLOW_RATE_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    CURRENT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    RESET_DISPENSING_DRIVE_AFTER_FIELD_NUMBER: _ClassVar[int]
    use_channels: _types_pb2.Int32List
    position: float
    flow_rate: float
    acceleration: float
    current_limit: int
    reset_dispensing_drive_after: bool
    def __init__(self, use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., position: _Optional[float] = ..., flow_rate: _Optional[float] = ..., acceleration: _Optional[float] = ..., current_limit: _Optional[int] = ..., reset_dispensing_drive_after: _Optional[bool] = ...) -> None: ...

class PipettesEmptyTipsResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesInitializeRequest(_message.Message):
    __slots__ = ("x_position", "y_positions", "begin_of_tip_deposit_process", "end_of_tip_deposit_process", "minimum_traverse_height_end", "tip_pattern", "tip_type", "discarding_method", "z_position_at_end_of_a_command")
    X_POSITION_FIELD_NUMBER: _ClassVar[int]
    Y_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    BEGIN_OF_TIP_DEPOSIT_PROCESS_FIELD_NUMBER: _ClassVar[int]
    END_OF_TIP_DEPOSIT_PROCESS_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_END_FIELD_NUMBER: _ClassVar[int]
    TIP_PATTERN_FIELD_NUMBER: _ClassVar[int]
    TIP_TYPE_FIELD_NUMBER: _ClassVar[int]
    DISCARDING_METHOD_FIELD_NUMBER: _ClassVar[int]
    Z_POSITION_AT_END_OF_A_COMMAND_FIELD_NUMBER: _ClassVar[int]
    x_position: float
    y_positions: _types_pb2.DoubleList
    begin_of_tip_deposit_process: float
    end_of_tip_deposit_process: float
    minimum_traverse_height_end: float
    tip_pattern: _types_pb2.BoolList
    tip_type: int
    discarding_method: int
    z_position_at_end_of_a_command: float
    def __init__(self, x_position: _Optional[float] = ..., y_positions: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., begin_of_tip_deposit_process: _Optional[float] = ..., end_of_tip_deposit_process: _Optional[float] = ..., minimum_traverse_height_end: _Optional[float] = ..., tip_pattern: _Optional[_Union[_types_pb2.BoolList, _Mapping]] = ..., tip_type: _Optional[int] = ..., discarding_method: _Optional[int] = ..., z_position_at_end_of_a_command: _Optional[float] = ...) -> None: ...

class PipettesInitializeResponse(_message.Message):
    __slots__ = ("reply",)
    REPLY_FIELD_NUMBER: _ClassVar[int]
    reply: _types_pb2.FirmwareReply
    def __init__(self, reply: _Optional[_Union[_types_pb2.FirmwareReply, _Mapping]] = ...) -> None: ...

class PipettesProbeXUsingClldRequest(_message.Message):
    __slots__ = ("channel", "direction", "search_end_position", "post_detection_distance", "tip_bottom_diameter", "stop_disc_diameter", "allow_without_tip", "read_timeout")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_END_POSITION_FIELD_NUMBER: _ClassVar[int]
    POST_DETECTION_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    TIP_BOTTOM_DIAMETER_FIELD_NUMBER: _ClassVar[int]
    STOP_DISC_DIAMETER_FIELD_NUMBER: _ClassVar[int]
    ALLOW_WITHOUT_TIP_FIELD_NUMBER: _ClassVar[int]
    READ_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    channel: int
    direction: _types_pb2.XProbeDirection
    search_end_position: float
    post_detection_distance: float
    tip_bottom_diameter: float
    stop_disc_diameter: float
    allow_without_tip: bool
    read_timeout: int
    def __init__(self, channel: _Optional[int] = ..., direction: _Optional[_Union[_types_pb2.XProbeDirection, str]] = ..., search_end_position: _Optional[float] = ..., post_detection_distance: _Optional[float] = ..., tip_bottom_diameter: _Optional[float] = ..., stop_disc_diameter: _Optional[float] = ..., allow_without_tip: _Optional[bool] = ..., read_timeout: _Optional[int] = ...) -> None: ...

class PipettesProbeXUsingClldResponse(_message.Message):
    __slots__ = ("x_position",)
    X_POSITION_FIELD_NUMBER: _ClassVar[int]
    x_position: float
    def __init__(self, x_position: _Optional[float] = ...) -> None: ...

class PipettesProbeYUsingClldRequest(_message.Message):
    __slots__ = ("channel", "direction", "search_start_position", "search_end_position", "search_speed", "acceleration_level", "detection_edge", "current_limit", "post_detection_distance", "tip_bottom_diameter", "stop_disc_diameter", "allow_without_tip")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_START_POSITION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_END_POSITION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_SPEED_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_LEVEL_FIELD_NUMBER: _ClassVar[int]
    DETECTION_EDGE_FIELD_NUMBER: _ClassVar[int]
    CURRENT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    POST_DETECTION_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    TIP_BOTTOM_DIAMETER_FIELD_NUMBER: _ClassVar[int]
    STOP_DISC_DIAMETER_FIELD_NUMBER: _ClassVar[int]
    ALLOW_WITHOUT_TIP_FIELD_NUMBER: _ClassVar[int]
    channel: int
    direction: _types_pb2.YProbeDirection
    search_start_position: float
    search_end_position: float
    search_speed: float
    acceleration_level: int
    detection_edge: int
    current_limit: int
    post_detection_distance: float
    tip_bottom_diameter: float
    stop_disc_diameter: float
    allow_without_tip: bool
    def __init__(self, channel: _Optional[int] = ..., direction: _Optional[_Union[_types_pb2.YProbeDirection, str]] = ..., search_start_position: _Optional[float] = ..., search_end_position: _Optional[float] = ..., search_speed: _Optional[float] = ..., acceleration_level: _Optional[int] = ..., detection_edge: _Optional[int] = ..., current_limit: _Optional[int] = ..., post_detection_distance: _Optional[float] = ..., tip_bottom_diameter: _Optional[float] = ..., stop_disc_diameter: _Optional[float] = ..., allow_without_tip: _Optional[bool] = ...) -> None: ...

class PipettesProbeYUsingClldResponse(_message.Message):
    __slots__ = ("y_position",)
    Y_POSITION_FIELD_NUMBER: _ClassVar[int]
    y_position: float
    def __init__(self, y_position: _Optional[float] = ...) -> None: ...

class PipettesRequestLastLldZPositionsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesRequestLastLldZPositionsResponse(_message.Message):
    __slots__ = ("last_lld_z_positions",)
    LAST_LLD_Z_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    last_lld_z_positions: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, last_lld_z_positions: _Optional[_Iterable[float]] = ...) -> None: ...

class PipettesProbeZUsingClldRequest(_message.Message):
    __slots__ = ("channel", "search_start_position", "search_end_position", "search_speed", "acceleration", "detection_edge", "detection_drop", "post_detection_trajectory", "allow_without_tip", "post_detection_distance", "move_to_safe_z_position_after")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    SEARCH_START_POSITION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_END_POSITION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_SPEED_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    DETECTION_EDGE_FIELD_NUMBER: _ClassVar[int]
    DETECTION_DROP_FIELD_NUMBER: _ClassVar[int]
    POST_DETECTION_TRAJECTORY_FIELD_NUMBER: _ClassVar[int]
    ALLOW_WITHOUT_TIP_FIELD_NUMBER: _ClassVar[int]
    POST_DETECTION_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    MOVE_TO_SAFE_Z_POSITION_AFTER_FIELD_NUMBER: _ClassVar[int]
    channel: int
    search_start_position: float
    search_end_position: float
    search_speed: float
    acceleration: float
    detection_edge: int
    detection_drop: int
    post_detection_trajectory: int
    allow_without_tip: bool
    post_detection_distance: float
    move_to_safe_z_position_after: bool
    def __init__(self, channel: _Optional[int] = ..., search_start_position: _Optional[float] = ..., search_end_position: _Optional[float] = ..., search_speed: _Optional[float] = ..., acceleration: _Optional[float] = ..., detection_edge: _Optional[int] = ..., detection_drop: _Optional[int] = ..., post_detection_trajectory: _Optional[int] = ..., allow_without_tip: _Optional[bool] = ..., post_detection_distance: _Optional[float] = ..., move_to_safe_z_position_after: _Optional[bool] = ...) -> None: ...

class PipettesProbeZUsingClldResponse(_message.Message):
    __slots__ = ("height",)
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    height: float
    def __init__(self, height: _Optional[float] = ...) -> None: ...

class PipettesProbeZUsingPlldRequest(_message.Message):
    __slots__ = ("channel", "search_start_position", "search_end_position", "pressure_mode", "allow_without_tip", "post_detection_distance", "move_to_safe_z_position_after", "approach_speed", "search_speed", "acceleration", "z_current_limit", "tip_has_filter", "dispensing_speed", "dispensing_acceleration", "dispensing_max_speed", "dispensing_current_limit", "detection_edge", "detection_drop", "clld_verification", "clld_detection_edge", "clld_detection_drop", "max_delta_plld_clld", "foam_detection_drop", "foam_detection_edge_tolerance", "foam_ad_values", "foam_search_speed", "dispense_back_volume", "post_detection_trajectory", "read_timeout")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    SEARCH_START_POSITION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_END_POSITION_FIELD_NUMBER: _ClassVar[int]
    PRESSURE_MODE_FIELD_NUMBER: _ClassVar[int]
    ALLOW_WITHOUT_TIP_FIELD_NUMBER: _ClassVar[int]
    POST_DETECTION_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    MOVE_TO_SAFE_Z_POSITION_AFTER_FIELD_NUMBER: _ClassVar[int]
    APPROACH_SPEED_FIELD_NUMBER: _ClassVar[int]
    SEARCH_SPEED_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    Z_CURRENT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    TIP_HAS_FILTER_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_SPEED_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_MAX_SPEED_FIELD_NUMBER: _ClassVar[int]
    DISPENSING_CURRENT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    DETECTION_EDGE_FIELD_NUMBER: _ClassVar[int]
    DETECTION_DROP_FIELD_NUMBER: _ClassVar[int]
    CLLD_VERIFICATION_FIELD_NUMBER: _ClassVar[int]
    CLLD_DETECTION_EDGE_FIELD_NUMBER: _ClassVar[int]
    CLLD_DETECTION_DROP_FIELD_NUMBER: _ClassVar[int]
    MAX_DELTA_PLLD_CLLD_FIELD_NUMBER: _ClassVar[int]
    FOAM_DETECTION_DROP_FIELD_NUMBER: _ClassVar[int]
    FOAM_DETECTION_EDGE_TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    FOAM_AD_VALUES_FIELD_NUMBER: _ClassVar[int]
    FOAM_SEARCH_SPEED_FIELD_NUMBER: _ClassVar[int]
    DISPENSE_BACK_VOLUME_FIELD_NUMBER: _ClassVar[int]
    POST_DETECTION_TRAJECTORY_FIELD_NUMBER: _ClassVar[int]
    READ_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    channel: int
    search_start_position: float
    search_end_position: float
    pressure_mode: _types_pb2.PressureLLDMode
    allow_without_tip: bool
    post_detection_distance: float
    move_to_safe_z_position_after: bool
    approach_speed: float
    search_speed: float
    acceleration: float
    z_current_limit: int
    tip_has_filter: bool
    dispensing_speed: float
    dispensing_acceleration: float
    dispensing_max_speed: float
    dispensing_current_limit: int
    detection_edge: int
    detection_drop: int
    clld_verification: bool
    clld_detection_edge: int
    clld_detection_drop: int
    max_delta_plld_clld: float
    foam_detection_drop: int
    foam_detection_edge_tolerance: int
    foam_ad_values: int
    foam_search_speed: float
    dispense_back_volume: float
    post_detection_trajectory: int
    read_timeout: int
    def __init__(self, channel: _Optional[int] = ..., search_start_position: _Optional[float] = ..., search_end_position: _Optional[float] = ..., pressure_mode: _Optional[_Union[_types_pb2.PressureLLDMode, str]] = ..., allow_without_tip: _Optional[bool] = ..., post_detection_distance: _Optional[float] = ..., move_to_safe_z_position_after: _Optional[bool] = ..., approach_speed: _Optional[float] = ..., search_speed: _Optional[float] = ..., acceleration: _Optional[float] = ..., z_current_limit: _Optional[int] = ..., tip_has_filter: _Optional[bool] = ..., dispensing_speed: _Optional[float] = ..., dispensing_acceleration: _Optional[float] = ..., dispensing_max_speed: _Optional[float] = ..., dispensing_current_limit: _Optional[int] = ..., detection_edge: _Optional[int] = ..., detection_drop: _Optional[int] = ..., clld_verification: _Optional[bool] = ..., clld_detection_edge: _Optional[int] = ..., clld_detection_drop: _Optional[int] = ..., max_delta_plld_clld: _Optional[float] = ..., foam_detection_drop: _Optional[int] = ..., foam_detection_edge_tolerance: _Optional[int] = ..., foam_ad_values: _Optional[int] = ..., foam_search_speed: _Optional[float] = ..., dispense_back_volume: _Optional[float] = ..., post_detection_trajectory: _Optional[int] = ..., read_timeout: _Optional[int] = ...) -> None: ...

class PipettesProbeZUsingPlldResponse(_message.Message):
    __slots__ = ("heights",)
    HEIGHTS_FIELD_NUMBER: _ClassVar[int]
    heights: _types_pb2.DoubleList
    def __init__(self, heights: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ...) -> None: ...

class PipettesProbeZUsingZtouchRequest(_message.Message):
    __slots__ = ("channel", "search_start_position", "search_end_position", "search_speed", "approach_speed", "acceleration", "detection_limiter_pwm", "push_force_pwm", "allow_without_tip", "post_detection_distance", "move_to_safe_z_position_after")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    SEARCH_START_POSITION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_END_POSITION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_SPEED_FIELD_NUMBER: _ClassVar[int]
    APPROACH_SPEED_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    DETECTION_LIMITER_PWM_FIELD_NUMBER: _ClassVar[int]
    PUSH_FORCE_PWM_FIELD_NUMBER: _ClassVar[int]
    ALLOW_WITHOUT_TIP_FIELD_NUMBER: _ClassVar[int]
    POST_DETECTION_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    MOVE_TO_SAFE_Z_POSITION_AFTER_FIELD_NUMBER: _ClassVar[int]
    channel: int
    search_start_position: float
    search_end_position: float
    search_speed: float
    approach_speed: float
    acceleration: float
    detection_limiter_pwm: int
    push_force_pwm: int
    allow_without_tip: bool
    post_detection_distance: float
    move_to_safe_z_position_after: bool
    def __init__(self, channel: _Optional[int] = ..., search_start_position: _Optional[float] = ..., search_end_position: _Optional[float] = ..., search_speed: _Optional[float] = ..., approach_speed: _Optional[float] = ..., acceleration: _Optional[float] = ..., detection_limiter_pwm: _Optional[int] = ..., push_force_pwm: _Optional[int] = ..., allow_without_tip: _Optional[bool] = ..., post_detection_distance: _Optional[float] = ..., move_to_safe_z_position_after: _Optional[bool] = ...) -> None: ...

class PipettesProbeZUsingZtouchResponse(_message.Message):
    __slots__ = ("height",)
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    height: float
    def __init__(self, height: _Optional[float] = ...) -> None: ...

class PipettesProbeLiquidHeightsRequest(_message.Message):
    __slots__ = ("containers", "use_channels", "resource_offsets", "lld_mode_lldmode", "lld_mode_each", "search_speed", "n_replicates", "minimum_traverse_height_start", "minimum_traverse_height_during", "minimum_traverse_height_end", "x_grouping_tolerance")
    CONTAINERS_FIELD_NUMBER: _ClassVar[int]
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_OFFSETS_FIELD_NUMBER: _ClassVar[int]
    LLD_MODE_LLDMODE_FIELD_NUMBER: _ClassVar[int]
    LLD_MODE_EACH_FIELD_NUMBER: _ClassVar[int]
    SEARCH_SPEED_FIELD_NUMBER: _ClassVar[int]
    N_REPLICATES_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_DURING_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_END_FIELD_NUMBER: _ClassVar[int]
    X_GROUPING_TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    containers: _containers.RepeatedCompositeFieldContainer[_types_pb2_1.ResourceRef]
    use_channels: _types_pb2.Int32List
    resource_offsets: _types_pb2.Vec3List
    lld_mode_lldmode: _types_pb2.LLDMode
    lld_mode_each: _types_pb2.LLDModeList
    search_speed: float
    n_replicates: int
    minimum_traverse_height_start: float
    minimum_traverse_height_during: float
    minimum_traverse_height_end: float
    x_grouping_tolerance: float
    def __init__(self, containers: _Optional[_Iterable[_Union[_types_pb2_1.ResourceRef, _Mapping]]] = ..., use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., resource_offsets: _Optional[_Union[_types_pb2.Vec3List, _Mapping]] = ..., lld_mode_lldmode: _Optional[_Union[_types_pb2.LLDMode, str]] = ..., lld_mode_each: _Optional[_Union[_types_pb2.LLDModeList, _Mapping]] = ..., search_speed: _Optional[float] = ..., n_replicates: _Optional[int] = ..., minimum_traverse_height_start: _Optional[float] = ..., minimum_traverse_height_during: _Optional[float] = ..., minimum_traverse_height_end: _Optional[float] = ..., x_grouping_tolerance: _Optional[float] = ...) -> None: ...

class PipettesProbeLiquidHeightsResponse(_message.Message):
    __slots__ = ("heights",)
    HEIGHTS_FIELD_NUMBER: _ClassVar[int]
    heights: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, heights: _Optional[_Iterable[float]] = ...) -> None: ...

class PipettesProbeLiquidVolumesRequest(_message.Message):
    __slots__ = ("containers", "use_channels", "resource_offsets", "lld_mode_lldmode", "lld_mode_each", "search_speed", "n_replicates", "minimum_traverse_height_start", "minimum_traverse_height_during", "minimum_traverse_height_end", "x_grouping_tolerance")
    CONTAINERS_FIELD_NUMBER: _ClassVar[int]
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_OFFSETS_FIELD_NUMBER: _ClassVar[int]
    LLD_MODE_LLDMODE_FIELD_NUMBER: _ClassVar[int]
    LLD_MODE_EACH_FIELD_NUMBER: _ClassVar[int]
    SEARCH_SPEED_FIELD_NUMBER: _ClassVar[int]
    N_REPLICATES_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_DURING_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_END_FIELD_NUMBER: _ClassVar[int]
    X_GROUPING_TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    containers: _containers.RepeatedCompositeFieldContainer[_types_pb2_1.ResourceRef]
    use_channels: _types_pb2.Int32List
    resource_offsets: _types_pb2.Vec3List
    lld_mode_lldmode: _types_pb2.LLDMode
    lld_mode_each: _types_pb2.LLDModeList
    search_speed: float
    n_replicates: int
    minimum_traverse_height_start: float
    minimum_traverse_height_during: float
    minimum_traverse_height_end: float
    x_grouping_tolerance: float
    def __init__(self, containers: _Optional[_Iterable[_Union[_types_pb2_1.ResourceRef, _Mapping]]] = ..., use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., resource_offsets: _Optional[_Union[_types_pb2.Vec3List, _Mapping]] = ..., lld_mode_lldmode: _Optional[_Union[_types_pb2.LLDMode, str]] = ..., lld_mode_each: _Optional[_Union[_types_pb2.LLDModeList, _Mapping]] = ..., search_speed: _Optional[float] = ..., n_replicates: _Optional[int] = ..., minimum_traverse_height_start: _Optional[float] = ..., minimum_traverse_height_during: _Optional[float] = ..., minimum_traverse_height_end: _Optional[float] = ..., x_grouping_tolerance: _Optional[float] = ...) -> None: ...

class PipettesProbeLiquidVolumesResponse(_message.Message):
    __slots__ = ("volumes",)
    VOLUMES_FIELD_NUMBER: _ClassVar[int]
    volumes: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, volumes: _Optional[_Iterable[float]] = ...) -> None: ...

class PipettesProbeZHeightsUsingZtouchRequest(_message.Message):
    __slots__ = ("containers", "use_channels", "resource_offsets", "search_speed", "n_replicates", "approach_speed", "minimum_traverse_height_start", "minimum_traverse_height_during", "minimum_traverse_height_end", "x_grouping_tolerance")
    CONTAINERS_FIELD_NUMBER: _ClassVar[int]
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_OFFSETS_FIELD_NUMBER: _ClassVar[int]
    SEARCH_SPEED_FIELD_NUMBER: _ClassVar[int]
    N_REPLICATES_FIELD_NUMBER: _ClassVar[int]
    APPROACH_SPEED_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_DURING_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_END_FIELD_NUMBER: _ClassVar[int]
    X_GROUPING_TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    containers: _containers.RepeatedCompositeFieldContainer[_types_pb2_1.ResourceRef]
    use_channels: _types_pb2.Int32List
    resource_offsets: _types_pb2.Vec3List
    search_speed: float
    n_replicates: int
    approach_speed: float
    minimum_traverse_height_start: float
    minimum_traverse_height_during: float
    minimum_traverse_height_end: float
    x_grouping_tolerance: float
    def __init__(self, containers: _Optional[_Iterable[_Union[_types_pb2_1.ResourceRef, _Mapping]]] = ..., use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., resource_offsets: _Optional[_Union[_types_pb2.Vec3List, _Mapping]] = ..., search_speed: _Optional[float] = ..., n_replicates: _Optional[int] = ..., approach_speed: _Optional[float] = ..., minimum_traverse_height_start: _Optional[float] = ..., minimum_traverse_height_during: _Optional[float] = ..., minimum_traverse_height_end: _Optional[float] = ..., x_grouping_tolerance: _Optional[float] = ...) -> None: ...

class PipettesProbeZHeightsUsingZtouchResponse(_message.Message):
    __slots__ = ("heights",)
    HEIGHTS_FIELD_NUMBER: _ClassVar[int]
    heights: _containers.RepeatedCompositeFieldContainer[_types_pb2.OptionalDouble]
    def __init__(self, heights: _Optional[_Iterable[_Union[_types_pb2.OptionalDouble, _Mapping]]] = ...) -> None: ...

class PipettesPickUpTipsRequest(_message.Message):
    __slots__ = ("tip_spots", "use_channels", "offsets", "begin_tip_pick_up_process", "end_tip_pick_up_process", "minimum_traverse_height_start", "pickup_method", "x_tolerance")
    TIP_SPOTS_FIELD_NUMBER: _ClassVar[int]
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    OFFSETS_FIELD_NUMBER: _ClassVar[int]
    BEGIN_TIP_PICK_UP_PROCESS_FIELD_NUMBER: _ClassVar[int]
    END_TIP_PICK_UP_PROCESS_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    PICKUP_METHOD_FIELD_NUMBER: _ClassVar[int]
    X_TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    tip_spots: _containers.RepeatedCompositeFieldContainer[_types_pb2_1.ResourceRef]
    use_channels: _types_pb2.Int32List
    offsets: _types_pb2.Vec3List
    begin_tip_pick_up_process: float
    end_tip_pick_up_process: float
    minimum_traverse_height_start: float
    pickup_method: _types_pb2.TipPickupMethod
    x_tolerance: float
    def __init__(self, tip_spots: _Optional[_Iterable[_Union[_types_pb2_1.ResourceRef, _Mapping]]] = ..., use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., offsets: _Optional[_Union[_types_pb2.Vec3List, _Mapping]] = ..., begin_tip_pick_up_process: _Optional[float] = ..., end_tip_pick_up_process: _Optional[float] = ..., minimum_traverse_height_start: _Optional[float] = ..., pickup_method: _Optional[_Union[_types_pb2.TipPickupMethod, str]] = ..., x_tolerance: _Optional[float] = ...) -> None: ...

class PipettesPickUpTipsResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesDropTipsRequest(_message.Message):
    __slots__ = ("destinations", "use_channels", "offsets", "drop_method", "begin_tip_deposit_process", "end_tip_deposit_process", "minimum_traverse_height_start", "minimum_traverse_height_end", "x_tolerance")
    DESTINATIONS_FIELD_NUMBER: _ClassVar[int]
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    OFFSETS_FIELD_NUMBER: _ClassVar[int]
    DROP_METHOD_FIELD_NUMBER: _ClassVar[int]
    BEGIN_TIP_DEPOSIT_PROCESS_FIELD_NUMBER: _ClassVar[int]
    END_TIP_DEPOSIT_PROCESS_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_END_FIELD_NUMBER: _ClassVar[int]
    X_TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    destinations: _containers.RepeatedCompositeFieldContainer[_types_pb2.TipDestination]
    use_channels: _types_pb2.Int32List
    offsets: _types_pb2.Vec3List
    drop_method: _types_pb2.TipDropMethod
    begin_tip_deposit_process: float
    end_tip_deposit_process: float
    minimum_traverse_height_start: float
    minimum_traverse_height_end: float
    x_tolerance: float
    def __init__(self, destinations: _Optional[_Iterable[_Union[_types_pb2.TipDestination, _Mapping]]] = ..., use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., offsets: _Optional[_Union[_types_pb2.Vec3List, _Mapping]] = ..., drop_method: _Optional[_Union[_types_pb2.TipDropMethod, str]] = ..., begin_tip_deposit_process: _Optional[float] = ..., end_tip_deposit_process: _Optional[float] = ..., minimum_traverse_height_start: _Optional[float] = ..., minimum_traverse_height_end: _Optional[float] = ..., x_tolerance: _Optional[float] = ...) -> None: ...

class PipettesDropTipsResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesReturnTipsRequest(_message.Message):
    __slots__ = ("use_channels", "offsets", "drop_method", "begin_tip_deposit_process", "end_tip_deposit_process", "minimum_traverse_height_start", "minimum_traverse_height_end", "x_tolerance")
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    OFFSETS_FIELD_NUMBER: _ClassVar[int]
    DROP_METHOD_FIELD_NUMBER: _ClassVar[int]
    BEGIN_TIP_DEPOSIT_PROCESS_FIELD_NUMBER: _ClassVar[int]
    END_TIP_DEPOSIT_PROCESS_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_END_FIELD_NUMBER: _ClassVar[int]
    X_TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    use_channels: _types_pb2.Int32List
    offsets: _types_pb2.Vec3List
    drop_method: _types_pb2.TipDropMethod
    begin_tip_deposit_process: float
    end_tip_deposit_process: float
    minimum_traverse_height_start: float
    minimum_traverse_height_end: float
    x_tolerance: float
    def __init__(self, use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., offsets: _Optional[_Union[_types_pb2.Vec3List, _Mapping]] = ..., drop_method: _Optional[_Union[_types_pb2.TipDropMethod, str]] = ..., begin_tip_deposit_process: _Optional[float] = ..., end_tip_deposit_process: _Optional[float] = ..., minimum_traverse_height_start: _Optional[float] = ..., minimum_traverse_height_end: _Optional[float] = ..., x_tolerance: _Optional[float] = ...) -> None: ...

class PipettesReturnTipsResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesDiscardTipsRequest(_message.Message):
    __slots__ = ("use_channels", "offsets", "drop_method", "begin_tip_deposit_process", "end_tip_deposit_process", "minimum_traverse_height_start", "minimum_traverse_height_end", "x_tolerance")
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    OFFSETS_FIELD_NUMBER: _ClassVar[int]
    DROP_METHOD_FIELD_NUMBER: _ClassVar[int]
    BEGIN_TIP_DEPOSIT_PROCESS_FIELD_NUMBER: _ClassVar[int]
    END_TIP_DEPOSIT_PROCESS_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_END_FIELD_NUMBER: _ClassVar[int]
    X_TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    use_channels: _types_pb2.Int32List
    offsets: _types_pb2.Vec3List
    drop_method: _types_pb2.TipDropMethod
    begin_tip_deposit_process: float
    end_tip_deposit_process: float
    minimum_traverse_height_start: float
    minimum_traverse_height_end: float
    x_tolerance: float
    def __init__(self, use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., offsets: _Optional[_Union[_types_pb2.Vec3List, _Mapping]] = ..., drop_method: _Optional[_Union[_types_pb2.TipDropMethod, str]] = ..., begin_tip_deposit_process: _Optional[float] = ..., end_tip_deposit_process: _Optional[float] = ..., minimum_traverse_height_start: _Optional[float] = ..., minimum_traverse_height_end: _Optional[float] = ..., x_tolerance: _Optional[float] = ...) -> None: ...

class PipettesDiscardTipsResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesConsolidateTipInventoryRequest(_message.Message):
    __slots__ = ("tip_racks", "use_channels")
    TIP_RACKS_FIELD_NUMBER: _ClassVar[int]
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    tip_racks: _containers.RepeatedCompositeFieldContainer[_types_pb2_1.ResourceRef]
    use_channels: _types_pb2.Int32List
    def __init__(self, tip_racks: _Optional[_Iterable[_Union[_types_pb2_1.ResourceRef, _Mapping]]] = ..., use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ...) -> None: ...

class PipettesConsolidateTipInventoryResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesProbeTipPresenceViaPickupRequest(_message.Message):
    __slots__ = ("tip_spots", "use_channels", "minimum_traverse_height_start", "minimum_traverse_height_end")
    TIP_SPOTS_FIELD_NUMBER: _ClassVar[int]
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_END_FIELD_NUMBER: _ClassVar[int]
    tip_spots: _containers.RepeatedCompositeFieldContainer[_types_pb2_1.ResourceRef]
    use_channels: _types_pb2.Int32List
    minimum_traverse_height_start: float
    minimum_traverse_height_end: float
    def __init__(self, tip_spots: _Optional[_Iterable[_Union[_types_pb2_1.ResourceRef, _Mapping]]] = ..., use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., minimum_traverse_height_start: _Optional[float] = ..., minimum_traverse_height_end: _Optional[float] = ...) -> None: ...

class PipettesProbeTipPresenceViaPickupResponse(_message.Message):
    __slots__ = ("present",)
    class PresentEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: _Optional[bool] = ...) -> None: ...
    PRESENT_FIELD_NUMBER: _ClassVar[int]
    present: _containers.ScalarMap[str, bool]
    def __init__(self, present: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class PipettesProbeTipInventoryRequest(_message.Message):
    __slots__ = ("tip_spots", "use_channels", "minimum_traverse_height_start", "minimum_traverse_height_end")
    TIP_SPOTS_FIELD_NUMBER: _ClassVar[int]
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_END_FIELD_NUMBER: _ClassVar[int]
    tip_spots: _containers.RepeatedCompositeFieldContainer[_types_pb2_1.ResourceRef]
    use_channels: _types_pb2.Int32List
    minimum_traverse_height_start: float
    minimum_traverse_height_end: float
    def __init__(self, tip_spots: _Optional[_Iterable[_Union[_types_pb2_1.ResourceRef, _Mapping]]] = ..., use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., minimum_traverse_height_start: _Optional[float] = ..., minimum_traverse_height_end: _Optional[float] = ...) -> None: ...

class PipettesProbeTipInventoryResponse(_message.Message):
    __slots__ = ("present",)
    class PresentEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: _Optional[bool] = ...) -> None: ...
    PRESENT_FIELD_NUMBER: _ClassVar[int]
    present: _containers.ScalarMap[str, bool]
    def __init__(self, present: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class PipettesRequestChannelPressureRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestChannelPressureResponse(_message.Message):
    __slots__ = ("channel_pressure",)
    CHANNEL_PRESSURE_FIELD_NUMBER: _ClassVar[int]
    channel_pressure: int
    def __init__(self, channel_pressure: _Optional[int] = ...) -> None: ...

class PipettesAutoAdjustPressureSensorRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesAutoAdjustPressureSensorResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesSetTadmModeRequest(_message.Message):
    __slots__ = ("channel", "enabled")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    channel: int
    enabled: bool
    def __init__(self, channel: _Optional[int] = ..., enabled: _Optional[bool] = ...) -> None: ...

class PipettesSetTadmModeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesRequestTadmModeRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesRequestTadmModeResponse(_message.Message):
    __slots__ = ("enabled",)
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    def __init__(self, enabled: _Optional[bool] = ...) -> None: ...

class PipettesClearTadmFifoRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesClearTadmFifoResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesResetTadmLimitCurvesRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesResetTadmLimitCurvesResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesStartTadmMonitoringRequest(_message.Message):
    __slots__ = ("channel", "enforce_limit_curve_control", "storage_level", "limit_curve_index", "measurement_id")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    ENFORCE_LIMIT_CURVE_CONTROL_FIELD_NUMBER: _ClassVar[int]
    STORAGE_LEVEL_FIELD_NUMBER: _ClassVar[int]
    LIMIT_CURVE_INDEX_FIELD_NUMBER: _ClassVar[int]
    MEASUREMENT_ID_FIELD_NUMBER: _ClassVar[int]
    channel: int
    enforce_limit_curve_control: bool
    storage_level: _types_pb2.TADMStorageLevel
    limit_curve_index: int
    measurement_id: str
    def __init__(self, channel: _Optional[int] = ..., enforce_limit_curve_control: _Optional[bool] = ..., storage_level: _Optional[_Union[_types_pb2.TADMStorageLevel, str]] = ..., limit_curve_index: _Optional[int] = ..., measurement_id: _Optional[str] = ...) -> None: ...

class PipettesStartTadmMonitoringResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesStopTadmMonitoringRequest(_message.Message):
    __slots__ = ("channel",)
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    channel: int
    def __init__(self, channel: _Optional[int] = ...) -> None: ...

class PipettesStopTadmMonitoringResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PipettesReadTadmCurveRequest(_message.Message):
    __slots__ = ("channel", "points_per_read")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    POINTS_PER_READ_FIELD_NUMBER: _ClassVar[int]
    channel: int
    points_per_read: int
    def __init__(self, channel: _Optional[int] = ..., points_per_read: _Optional[int] = ...) -> None: ...

class PipettesReadTadmCurveResponse(_message.Message):
    __slots__ = ("curve",)
    CURVE_FIELD_NUMBER: _ClassVar[int]
    curve: TADMCurve
    def __init__(self, curve: _Optional[_Union[TADMCurve, _Mapping]] = ...) -> None: ...

class PipettesAspirateRequest(_message.Message):
    __slots__ = ("containers", "volumes", "use_channels", "resource_offsets", "liquid_heights", "lld_mode_lldmode", "lld_mode_each", "flow_rates", "hamilton_liquid_classes", "jet", "blow_out", "piston_volumes", "search_speed", "approach_speed", "blow_out_air_volumes", "immersion_depths", "minimum_allowed_z_positions_during", "pre_wetting_volumes", "pre_mixes", "mix_positions_from_liquid_surface", "surface_following_distances", "auto_surface_following", "second_section_heights", "second_section_ratios", "settling_times", "swap_speeds", "clot_detection_heights", "pull_out_distances_transport_air", "transport_air_volumes", "limit_curve_indices", "minimum_traverse_height_start", "minimum_traverse_height_during", "minimum_traverse_height_end", "x_grouping_tolerance", "tadm")
    CONTAINERS_FIELD_NUMBER: _ClassVar[int]
    VOLUMES_FIELD_NUMBER: _ClassVar[int]
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_OFFSETS_FIELD_NUMBER: _ClassVar[int]
    LIQUID_HEIGHTS_FIELD_NUMBER: _ClassVar[int]
    LLD_MODE_LLDMODE_FIELD_NUMBER: _ClassVar[int]
    LLD_MODE_EACH_FIELD_NUMBER: _ClassVar[int]
    FLOW_RATES_FIELD_NUMBER: _ClassVar[int]
    HAMILTON_LIQUID_CLASSES_FIELD_NUMBER: _ClassVar[int]
    JET_FIELD_NUMBER: _ClassVar[int]
    BLOW_OUT_FIELD_NUMBER: _ClassVar[int]
    PISTON_VOLUMES_FIELD_NUMBER: _ClassVar[int]
    SEARCH_SPEED_FIELD_NUMBER: _ClassVar[int]
    APPROACH_SPEED_FIELD_NUMBER: _ClassVar[int]
    BLOW_OUT_AIR_VOLUMES_FIELD_NUMBER: _ClassVar[int]
    IMMERSION_DEPTHS_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_ALLOWED_Z_POSITIONS_DURING_FIELD_NUMBER: _ClassVar[int]
    PRE_WETTING_VOLUMES_FIELD_NUMBER: _ClassVar[int]
    PRE_MIXES_FIELD_NUMBER: _ClassVar[int]
    MIX_POSITIONS_FROM_LIQUID_SURFACE_FIELD_NUMBER: _ClassVar[int]
    SURFACE_FOLLOWING_DISTANCES_FIELD_NUMBER: _ClassVar[int]
    AUTO_SURFACE_FOLLOWING_FIELD_NUMBER: _ClassVar[int]
    SECOND_SECTION_HEIGHTS_FIELD_NUMBER: _ClassVar[int]
    SECOND_SECTION_RATIOS_FIELD_NUMBER: _ClassVar[int]
    SETTLING_TIMES_FIELD_NUMBER: _ClassVar[int]
    SWAP_SPEEDS_FIELD_NUMBER: _ClassVar[int]
    CLOT_DETECTION_HEIGHTS_FIELD_NUMBER: _ClassVar[int]
    PULL_OUT_DISTANCES_TRANSPORT_AIR_FIELD_NUMBER: _ClassVar[int]
    TRANSPORT_AIR_VOLUMES_FIELD_NUMBER: _ClassVar[int]
    LIMIT_CURVE_INDICES_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_DURING_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_END_FIELD_NUMBER: _ClassVar[int]
    X_GROUPING_TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    TADM_FIELD_NUMBER: _ClassVar[int]
    containers: _containers.RepeatedCompositeFieldContainer[_types_pb2_1.ResourceRef]
    volumes: _types_pb2.DoubleList
    use_channels: _types_pb2.Int32List
    resource_offsets: _types_pb2.Vec3List
    liquid_heights: _types_pb2.OptionalDoubleList
    lld_mode_lldmode: _types_pb2.LLDMode
    lld_mode_each: _types_pb2.LLDModeList
    flow_rates: _types_pb2.DoubleList
    hamilton_liquid_classes: _types_pb2.LiquidClassList
    jet: _types_pb2.BoolList
    blow_out: _types_pb2.BoolList
    piston_volumes: _types_pb2.DoubleList
    search_speed: float
    approach_speed: float
    blow_out_air_volumes: _types_pb2.DoubleList
    immersion_depths: _types_pb2.DoubleList
    minimum_allowed_z_positions_during: _types_pb2.DoubleList
    pre_wetting_volumes: _types_pb2.DoubleList
    pre_mixes: _types_pb2.OptionalMixList
    mix_positions_from_liquid_surface: _types_pb2.DoubleList
    surface_following_distances: _types_pb2.DoubleList
    auto_surface_following: bool
    second_section_heights: _types_pb2.DoubleList
    second_section_ratios: _types_pb2.DoubleList
    settling_times: _types_pb2.DoubleList
    swap_speeds: _types_pb2.DoubleList
    clot_detection_heights: _types_pb2.DoubleList
    pull_out_distances_transport_air: _types_pb2.DoubleList
    transport_air_volumes: _types_pb2.DoubleList
    limit_curve_indices: _types_pb2.Int32List
    minimum_traverse_height_start: float
    minimum_traverse_height_during: float
    minimum_traverse_height_end: float
    x_grouping_tolerance: float
    tadm: bool
    def __init__(self, containers: _Optional[_Iterable[_Union[_types_pb2_1.ResourceRef, _Mapping]]] = ..., volumes: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., resource_offsets: _Optional[_Union[_types_pb2.Vec3List, _Mapping]] = ..., liquid_heights: _Optional[_Union[_types_pb2.OptionalDoubleList, _Mapping]] = ..., lld_mode_lldmode: _Optional[_Union[_types_pb2.LLDMode, str]] = ..., lld_mode_each: _Optional[_Union[_types_pb2.LLDModeList, _Mapping]] = ..., flow_rates: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., hamilton_liquid_classes: _Optional[_Union[_types_pb2.LiquidClassList, _Mapping]] = ..., jet: _Optional[_Union[_types_pb2.BoolList, _Mapping]] = ..., blow_out: _Optional[_Union[_types_pb2.BoolList, _Mapping]] = ..., piston_volumes: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., search_speed: _Optional[float] = ..., approach_speed: _Optional[float] = ..., blow_out_air_volumes: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., immersion_depths: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., minimum_allowed_z_positions_during: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., pre_wetting_volumes: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., pre_mixes: _Optional[_Union[_types_pb2.OptionalMixList, _Mapping]] = ..., mix_positions_from_liquid_surface: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., surface_following_distances: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., auto_surface_following: _Optional[bool] = ..., second_section_heights: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., second_section_ratios: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., settling_times: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., swap_speeds: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., clot_detection_heights: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., pull_out_distances_transport_air: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., transport_air_volumes: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., limit_curve_indices: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., minimum_traverse_height_start: _Optional[float] = ..., minimum_traverse_height_during: _Optional[float] = ..., minimum_traverse_height_end: _Optional[float] = ..., x_grouping_tolerance: _Optional[float] = ..., tadm: _Optional[bool] = ...) -> None: ...

class PipettesAspirateResponse(_message.Message):
    __slots__ = ("measurements",)
    MEASUREMENTS_FIELD_NUMBER: _ClassVar[int]
    measurements: _containers.RepeatedCompositeFieldContainer[PipetteMeasurement]
    def __init__(self, measurements: _Optional[_Iterable[_Union[PipetteMeasurement, _Mapping]]] = ...) -> None: ...

class PipettesDispenseRequest(_message.Message):
    __slots__ = ("containers", "volumes", "use_channels", "resource_offsets", "liquid_heights", "lld_mode_lldmode", "lld_mode_each", "flow_rates", "hamilton_liquid_classes", "jet", "blow_out", "empty", "piston_volumes", "search_speed", "approach_speed", "side_touch_off_distance", "immersion_depths", "minimum_allowed_z_positions_during", "transport_air_volumes", "cut_off_speeds", "stop_back_volumes", "surface_following_distances", "auto_surface_following", "second_section_heights", "second_section_ratios", "blow_out_air_volumes", "post_mixes", "mix_positions_from_liquid_surface", "settling_times", "swap_speeds", "pull_out_distances_transport_air", "limit_curve_indices", "minimum_traverse_height_start", "minimum_traverse_height_during", "minimum_traverse_height_end", "x_grouping_tolerance", "tadm")
    CONTAINERS_FIELD_NUMBER: _ClassVar[int]
    VOLUMES_FIELD_NUMBER: _ClassVar[int]
    USE_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_OFFSETS_FIELD_NUMBER: _ClassVar[int]
    LIQUID_HEIGHTS_FIELD_NUMBER: _ClassVar[int]
    LLD_MODE_LLDMODE_FIELD_NUMBER: _ClassVar[int]
    LLD_MODE_EACH_FIELD_NUMBER: _ClassVar[int]
    FLOW_RATES_FIELD_NUMBER: _ClassVar[int]
    HAMILTON_LIQUID_CLASSES_FIELD_NUMBER: _ClassVar[int]
    JET_FIELD_NUMBER: _ClassVar[int]
    BLOW_OUT_FIELD_NUMBER: _ClassVar[int]
    EMPTY_FIELD_NUMBER: _ClassVar[int]
    PISTON_VOLUMES_FIELD_NUMBER: _ClassVar[int]
    SEARCH_SPEED_FIELD_NUMBER: _ClassVar[int]
    APPROACH_SPEED_FIELD_NUMBER: _ClassVar[int]
    SIDE_TOUCH_OFF_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    IMMERSION_DEPTHS_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_ALLOWED_Z_POSITIONS_DURING_FIELD_NUMBER: _ClassVar[int]
    TRANSPORT_AIR_VOLUMES_FIELD_NUMBER: _ClassVar[int]
    CUT_OFF_SPEEDS_FIELD_NUMBER: _ClassVar[int]
    STOP_BACK_VOLUMES_FIELD_NUMBER: _ClassVar[int]
    SURFACE_FOLLOWING_DISTANCES_FIELD_NUMBER: _ClassVar[int]
    AUTO_SURFACE_FOLLOWING_FIELD_NUMBER: _ClassVar[int]
    SECOND_SECTION_HEIGHTS_FIELD_NUMBER: _ClassVar[int]
    SECOND_SECTION_RATIOS_FIELD_NUMBER: _ClassVar[int]
    BLOW_OUT_AIR_VOLUMES_FIELD_NUMBER: _ClassVar[int]
    POST_MIXES_FIELD_NUMBER: _ClassVar[int]
    MIX_POSITIONS_FROM_LIQUID_SURFACE_FIELD_NUMBER: _ClassVar[int]
    SETTLING_TIMES_FIELD_NUMBER: _ClassVar[int]
    SWAP_SPEEDS_FIELD_NUMBER: _ClassVar[int]
    PULL_OUT_DISTANCES_TRANSPORT_AIR_FIELD_NUMBER: _ClassVar[int]
    LIMIT_CURVE_INDICES_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_START_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_DURING_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_TRAVERSE_HEIGHT_END_FIELD_NUMBER: _ClassVar[int]
    X_GROUPING_TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    TADM_FIELD_NUMBER: _ClassVar[int]
    containers: _containers.RepeatedCompositeFieldContainer[_types_pb2_1.ResourceRef]
    volumes: _types_pb2.DoubleList
    use_channels: _types_pb2.Int32List
    resource_offsets: _types_pb2.Vec3List
    liquid_heights: _types_pb2.OptionalDoubleList
    lld_mode_lldmode: _types_pb2.LLDMode
    lld_mode_each: _types_pb2.LLDModeList
    flow_rates: _types_pb2.DoubleList
    hamilton_liquid_classes: _types_pb2.LiquidClassList
    jet: _types_pb2.BoolList
    blow_out: _types_pb2.BoolList
    empty: _types_pb2.BoolList
    piston_volumes: _types_pb2.DoubleList
    search_speed: float
    approach_speed: float
    side_touch_off_distance: float
    immersion_depths: _types_pb2.DoubleList
    minimum_allowed_z_positions_during: _types_pb2.DoubleList
    transport_air_volumes: _types_pb2.DoubleList
    cut_off_speeds: _types_pb2.DoubleList
    stop_back_volumes: _types_pb2.DoubleList
    surface_following_distances: _types_pb2.DoubleList
    auto_surface_following: bool
    second_section_heights: _types_pb2.DoubleList
    second_section_ratios: _types_pb2.DoubleList
    blow_out_air_volumes: _types_pb2.DoubleList
    post_mixes: _types_pb2.OptionalMixList
    mix_positions_from_liquid_surface: _types_pb2.DoubleList
    settling_times: _types_pb2.DoubleList
    swap_speeds: _types_pb2.DoubleList
    pull_out_distances_transport_air: _types_pb2.DoubleList
    limit_curve_indices: _types_pb2.Int32List
    minimum_traverse_height_start: float
    minimum_traverse_height_during: float
    minimum_traverse_height_end: float
    x_grouping_tolerance: float
    tadm: bool
    def __init__(self, containers: _Optional[_Iterable[_Union[_types_pb2_1.ResourceRef, _Mapping]]] = ..., volumes: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., use_channels: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., resource_offsets: _Optional[_Union[_types_pb2.Vec3List, _Mapping]] = ..., liquid_heights: _Optional[_Union[_types_pb2.OptionalDoubleList, _Mapping]] = ..., lld_mode_lldmode: _Optional[_Union[_types_pb2.LLDMode, str]] = ..., lld_mode_each: _Optional[_Union[_types_pb2.LLDModeList, _Mapping]] = ..., flow_rates: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., hamilton_liquid_classes: _Optional[_Union[_types_pb2.LiquidClassList, _Mapping]] = ..., jet: _Optional[_Union[_types_pb2.BoolList, _Mapping]] = ..., blow_out: _Optional[_Union[_types_pb2.BoolList, _Mapping]] = ..., empty: _Optional[_Union[_types_pb2.BoolList, _Mapping]] = ..., piston_volumes: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., search_speed: _Optional[float] = ..., approach_speed: _Optional[float] = ..., side_touch_off_distance: _Optional[float] = ..., immersion_depths: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., minimum_allowed_z_positions_during: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., transport_air_volumes: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., cut_off_speeds: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., stop_back_volumes: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., surface_following_distances: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., auto_surface_following: _Optional[bool] = ..., second_section_heights: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., second_section_ratios: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., blow_out_air_volumes: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., post_mixes: _Optional[_Union[_types_pb2.OptionalMixList, _Mapping]] = ..., mix_positions_from_liquid_surface: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., settling_times: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., swap_speeds: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., pull_out_distances_transport_air: _Optional[_Union[_types_pb2.DoubleList, _Mapping]] = ..., limit_curve_indices: _Optional[_Union[_types_pb2.Int32List, _Mapping]] = ..., minimum_traverse_height_start: _Optional[float] = ..., minimum_traverse_height_during: _Optional[float] = ..., minimum_traverse_height_end: _Optional[float] = ..., x_grouping_tolerance: _Optional[float] = ..., tadm: _Optional[bool] = ...) -> None: ...

class PipettesDispenseResponse(_message.Message):
    __slots__ = ("measurements",)
    MEASUREMENTS_FIELD_NUMBER: _ClassVar[int]
    measurements: _containers.RepeatedCompositeFieldContainer[PipetteMeasurement]
    def __init__(self, measurements: _Optional[_Iterable[_Union[PipetteMeasurement, _Mapping]]] = ...) -> None: ...

class PipettesSettings(_message.Message):
    __slots__ = ("default_y_speed", "default_y_acceleration_level", "default_z_speed", "default_z_acceleration", "default_z_current_limit", "default_minimum_traverse_height", "default_x_grouping_tolerance")
    DEFAULT_Y_SPEED_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_Y_ACCELERATION_LEVEL_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_Z_SPEED_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_Z_ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_Z_CURRENT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_MINIMUM_TRAVERSE_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_X_GROUPING_TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    default_y_speed: float
    default_y_acceleration_level: int
    default_z_speed: float
    default_z_acceleration: float
    default_z_current_limit: int
    default_minimum_traverse_height: float
    default_x_grouping_tolerance: float
    def __init__(self, default_y_speed: _Optional[float] = ..., default_y_acceleration_level: _Optional[int] = ..., default_z_speed: _Optional[float] = ..., default_z_acceleration: _Optional[float] = ..., default_z_current_limit: _Optional[int] = ..., default_minimum_traverse_height: _Optional[float] = ..., default_x_grouping_tolerance: _Optional[float] = ...) -> None: ...
