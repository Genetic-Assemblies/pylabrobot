"""What a served call raised, as a Connect error, and back: the client raises the same class, with
the same message, as the arm would have raised in this process."""

import asyncio
from typing import Dict, List, Optional, Tuple, Type

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from protobuf.wkt import Any as AnyMessage

from pylabrobot.brooks.precise_flex.driver.errors import (
  OperationInterrupted,
  OutOfRangeOfMotionError,
  PreciseFlexError,
)
from pylabrobot.brooks.precise_flex.kinematics import IKError
from pylabrobot.brooks.precise_flex.server import wire
from pylabrobot.brooks.precise_flex.server.v1 import errors_pb2 as epb
from pylabrobot.resources.server.errors import ServerError

ERROR_TYPE = "pylabrobot.brooks.precise_flex.server.v1.Error"

# Each kind and the class it is, the subclasses ahead of what they derive from.
_KINDS: List[Tuple[Type[BaseException], int, Code]] = [
  (PreciseFlexError, epb.ERROR_KIND_PRECISE_FLEX, Code.ABORTED),
  (OutOfRangeOfMotionError, epb.ERROR_KIND_OUT_OF_RANGE_OF_MOTION, Code.FAILED_PRECONDITION),
  (IKError, epb.ERROR_KIND_IK, Code.INVALID_ARGUMENT),
  (OperationInterrupted, epb.ERROR_KIND_OPERATION_INTERRUPTED, Code.ABORTED),
  (ServerError, epb.ERROR_KIND_RESOURCE_SERVER, Code.FAILED_PRECONDITION),
  (NotImplementedError, epb.ERROR_KIND_NOT_IMPLEMENTED, Code.UNIMPLEMENTED),
  (asyncio.TimeoutError, epb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (TimeoutError, epb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (ConnectionError, epb.ERROR_KIND_CONNECTION, Code.UNAVAILABLE),
  (KeyError, epb.ERROR_KIND_KEY, Code.INVALID_ARGUMENT),
  (IndexError, epb.ERROR_KIND_INDEX, Code.INVALID_ARGUMENT),
  (AssertionError, epb.ERROR_KIND_ASSERTION, Code.INTERNAL),
  (AttributeError, epb.ERROR_KIND_ATTRIBUTE, Code.INVALID_ARGUMENT),
  (TypeError, epb.ERROR_KIND_TYPE, Code.INVALID_ARGUMENT),
  (ValueError, epb.ERROR_KIND_VALUE, Code.INVALID_ARGUMENT),
  (RuntimeError, epb.ERROR_KIND_RUNTIME, Code.FAILED_PRECONDITION),
]
_CLASSES: Dict[int, Type[BaseException]] = {epb.ERROR_KIND_RESOURCE_SERVER: RuntimeError}
for _cls, _kind, _ in _KINDS:
  _CLASSES.setdefault(_kind, _cls)


def _message(error: BaseException) -> str:
  """What the error was made with, so making it again gives the same `str()`."""
  if len(error.args) == 1 and isinstance(error.args[0], str):
    return error.args[0]
  return str(error)


def to_connect_error(error: BaseException) -> ConnectError:
  """An error a call raised, as a Connect error carrying an `Error` detail."""
  if isinstance(error, ConnectError):
    return error
  detail = epb.Error(message=_message(error), type_name=type(error).__name__)
  code = Code.UNKNOWN
  for cls, kind, kind_code in _KINDS:
    if isinstance(error, cls):
      detail.kind, code = kind, kind_code  # type: ignore[assignment]
      break
  if isinstance(error, PreciseFlexError):
    detail.replycode, detail.message = error.replycode, error.message
  if isinstance(error, OutOfRangeOfMotionError):
    detail.axis_positions.CopyFrom(
      wire.joint_state_to({axis: value for axis, (value, _) in error.axes.items()})
    )
    detail.axis_limits.CopyFrom(
      wire.joint_limits_to({axis: limits for axis, (_, limits) in error.axes.items()})
    )
  any_detail = AnyMessage(
    type_url=f"type.googleapis.com/{ERROR_TYPE}", value=detail.SerializeToString()
  )
  return ConnectError(code, str(error), [any_detail])


def from_connect_error(error: ConnectError) -> Optional[BaseException]:
  """The error a call raised, from the Connect error it came as; None when it carries none."""
  for item in error.details:
    if item.type_name != ERROR_TYPE:
      continue
    detail = epb.Error.FromString(item.message_bytes)
    if detail.kind == epb.ERROR_KIND_PRECISE_FLEX:
      return PreciseFlexError(int(detail.replycode), detail.message)
    if detail.kind == epb.ERROR_KIND_OUT_OF_RANGE_OF_MOTION:
      positions = wire.joint_state_from(detail.axis_positions)
      limits = wire.joint_limits_from(detail.axis_limits)
      axes = {axis: (positions[axis], limits[axis]) for axis in positions if axis in limits}
      return OutOfRangeOfMotionError(detail.message, axes)
    cls = _CLASSES.get(detail.kind, Exception)
    return cls(detail.message) if detail.message else cls()
  return None
