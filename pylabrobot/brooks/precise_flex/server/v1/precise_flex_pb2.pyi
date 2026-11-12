from pylabrobot.brooks.precise_flex.server.v1 import description_pb2 as _description_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class PreciseFlexSetupRequest(_message.Message):
    __slots__ = ("skip_home", "skip_vision_setup")
    SKIP_HOME_FIELD_NUMBER: _ClassVar[int]
    SKIP_VISION_SETUP_FIELD_NUMBER: _ClassVar[int]
    skip_home: bool
    skip_vision_setup: bool
    def __init__(self, skip_home: _Optional[bool] = ..., skip_vision_setup: _Optional[bool] = ...) -> None: ...

class PreciseFlexSetupResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PreciseFlexStopRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PreciseFlexStopResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
