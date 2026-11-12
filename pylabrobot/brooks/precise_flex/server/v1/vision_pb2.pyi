from pylabrobot.brooks.precise_flex.server.v1 import types_pb2 as _types_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class VisionCaptureImageRequest(_message.Message):
    __slots__ = ("camera",)
    CAMERA_FIELD_NUMBER: _ClassVar[int]
    camera: _types_pb2.Camera
    def __init__(self, camera: _Optional[_Union[_types_pb2.Camera, _Mapping]] = ...) -> None: ...

class VisionCaptureImageResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.Image
    def __init__(self, value: _Optional[_Union[_types_pb2.Image, _Mapping]] = ...) -> None: ...

class VisionDiscoverConfigurationRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionDiscoverConfigurationResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class VisionEnumerateProjectRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionEnumerateProjectResponse(_message.Message):
    __slots__ = ("value",)
    class ValueEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _types_pb2.StringList
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_types_pb2.StringList, _Mapping]] = ...) -> None: ...
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _containers.MessageMap[str, _types_pb2.StringList]
    def __init__(self, value: _Optional[_Mapping[str, _types_pb2.StringList]] = ...) -> None: ...

class VisionRequestCameraCountRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionRequestCameraCountResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class VisionRequestCameraHeightRequest(_message.Message):
    __slots__ = ("camera",)
    CAMERA_FIELD_NUMBER: _ClassVar[int]
    camera: _types_pb2.Camera
    def __init__(self, camera: _Optional[_Union[_types_pb2.Camera, _Mapping]] = ...) -> None: ...

class VisionRequestCameraHeightResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class VisionRequestCameraNameRequest(_message.Message):
    __slots__ = ("camera",)
    CAMERA_FIELD_NUMBER: _ClassVar[int]
    camera: _types_pb2.Camera
    def __init__(self, camera: _Optional[_Union[_types_pb2.Camera, _Mapping]] = ...) -> None: ...

class VisionRequestCameraNameResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class VisionRequestCameraResolutionsRequest(_message.Message):
    __slots__ = ("camera",)
    CAMERA_FIELD_NUMBER: _ClassVar[int]
    camera: _types_pb2.Camera
    def __init__(self, camera: _Optional[_Union[_types_pb2.Camera, _Mapping]] = ...) -> None: ...

class VisionRequestCameraResolutionsResponse(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class VisionRequestCameraTypeRequest(_message.Message):
    __slots__ = ("camera",)
    CAMERA_FIELD_NUMBER: _ClassVar[int]
    camera: _types_pb2.Camera
    def __init__(self, camera: _Optional[_Union[_types_pb2.Camera, _Mapping]] = ...) -> None: ...

class VisionRequestCameraTypeResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class VisionRequestCameraWidthRequest(_message.Message):
    __slots__ = ("camera",)
    CAMERA_FIELD_NUMBER: _ClassVar[int]
    camera: _types_pb2.Camera
    def __init__(self, camera: _Optional[_Union[_types_pb2.Camera, _Mapping]] = ...) -> None: ...

class VisionRequestCameraWidthResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class VisionRequestIsLicensedRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionRequestIsLicensedResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: bool
    def __init__(self, value: _Optional[bool] = ...) -> None: ...

class VisionRequestProcessesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionRequestProcessesResponse(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class VisionRequestProjectNameRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionRequestProjectNameResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class VisionRequestProjectsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionRequestProjectsResponse(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class VisionRequestStereoParametersRequest(_message.Message):
    __slots__ = ("robot_number", "camera_number")
    ROBOT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CAMERA_NUMBER_FIELD_NUMBER: _ClassVar[int]
    robot_number: int
    camera_number: int
    def __init__(self, robot_number: _Optional[int] = ..., camera_number: _Optional[int] = ...) -> None: ...

class VisionRequestStereoParametersResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _types_pb2.StereoParameters
    def __init__(self, value: _Optional[_Union[_types_pb2.StereoParameters, _Mapping]] = ...) -> None: ...

class VisionRequestVisionToolPropertiesRequest(_message.Message):
    __slots__ = ("tool",)
    TOOL_FIELD_NUMBER: _ClassVar[int]
    tool: str
    def __init__(self, tool: _Optional[str] = ...) -> None: ...

class VisionRequestVisionToolPropertiesResponse(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class VisionRequestVisionToolPropertyRequest(_message.Message):
    __slots__ = ("tool", "property_name")
    TOOL_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    tool: str
    property_name: str
    def __init__(self, tool: _Optional[str] = ..., property_name: _Optional[str] = ...) -> None: ...

class VisionRequestVisionToolPropertyResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class VisionRequestVisionToolPropertyInfoRequest(_message.Message):
    __slots__ = ("tool", "property_name")
    TOOL_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    tool: str
    property_name: str
    def __init__(self, tool: _Optional[str] = ..., property_name: _Optional[str] = ...) -> None: ...

class VisionRequestVisionToolPropertyInfoResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class VisionRequestVisionToolPropertyValueRequest(_message.Message):
    __slots__ = ("tool", "property_name")
    TOOL_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    tool: str
    property_name: str
    def __init__(self, tool: _Optional[str] = ..., property_name: _Optional[str] = ...) -> None: ...

class VisionRequestVisionToolPropertyValueResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class VisionRequestVisionToolTypeRequest(_message.Message):
    __slots__ = ("tool",)
    TOOL_FIELD_NUMBER: _ClassVar[int]
    tool: str
    def __init__(self, tool: _Optional[str] = ...) -> None: ...

class VisionRequestVisionToolTypeResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class VisionRequestVisionToolTypesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionRequestVisionToolTypesResponse(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class VisionRequestVisionToolsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionRequestVisionToolsResponse(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class VisionRequestVisionVersionRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionRequestVisionVersionResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class VisionSaveImageRequest(_message.Message):
    __slots__ = ("camera", "acquire_prefix", "acquire_path")
    CAMERA_FIELD_NUMBER: _ClassVar[int]
    ACQUIRE_PREFIX_FIELD_NUMBER: _ClassVar[int]
    ACQUIRE_PATH_FIELD_NUMBER: _ClassVar[int]
    camera: _types_pb2.Camera
    acquire_prefix: str
    acquire_path: str
    def __init__(self, camera: _Optional[_Union[_types_pb2.Camera, _Mapping]] = ..., acquire_prefix: _Optional[str] = ..., acquire_path: _Optional[str] = ...) -> None: ...

class VisionSaveImageResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class VisionSetupRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionSetupResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionStartLedRequest(_message.Message):
    __slots__ = ("camera", "brightness", "delay", "use_server")
    CAMERA_FIELD_NUMBER: _ClassVar[int]
    BRIGHTNESS_FIELD_NUMBER: _ClassVar[int]
    DELAY_FIELD_NUMBER: _ClassVar[int]
    USE_SERVER_FIELD_NUMBER: _ClassVar[int]
    camera: _types_pb2.Camera
    brightness: int
    delay: int
    use_server: _types_pb2.CommandServer
    def __init__(self, camera: _Optional[_Union[_types_pb2.Camera, _Mapping]] = ..., brightness: _Optional[int] = ..., delay: _Optional[int] = ..., use_server: _Optional[_Union[_types_pb2.CommandServer, str]] = ...) -> None: ...

class VisionStartLedResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VisionStopLedRequest(_message.Message):
    __slots__ = ("camera", "use_server")
    CAMERA_FIELD_NUMBER: _ClassVar[int]
    USE_SERVER_FIELD_NUMBER: _ClassVar[int]
    camera: _types_pb2.Camera
    use_server: _types_pb2.CommandServer
    def __init__(self, camera: _Optional[_Union[_types_pb2.Camera, _Mapping]] = ..., use_server: _Optional[_Union[_types_pb2.CommandServer, str]] = ...) -> None: ...

class VisionStopLedResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
