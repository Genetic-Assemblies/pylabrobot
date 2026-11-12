"""What a served call raised, as an `Error` message, and back: the client raises the same class,
with the same message, as the LightCycler would have raised in this process."""

import asyncio
from typing import Dict, List, Optional, Tuple, Type

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from protobuf.wkt import Any as AnyMessage

from ..errors import (
  CommandFailedError,
  ExperimentFailedError,
  LightCyclerError,
  LightCyclerProtocolError,
  LightCyclerTimeoutError,
)
from .v1 import lightcycler_pb2 as pb

ERROR_TYPE = "pylabrobot.roche.lightcycler.server.v1.Error"

# Each class and its kind and code, the subclasses ahead of what they derive from.
_KINDS: List[Tuple[Type[BaseException], "pb.ErrorKind", Code]] = [
  (CommandFailedError, pb.ERROR_KIND_COMMAND_FAILED, Code.ABORTED),
  (LightCyclerProtocolError, pb.ERROR_KIND_PROTOCOL, Code.INTERNAL),
  (ExperimentFailedError, pb.ERROR_KIND_EXPERIMENT_FAILED, Code.ABORTED),
  (LightCyclerError, pb.ERROR_KIND_LIGHTCYCLER, Code.ABORTED),
  (LightCyclerTimeoutError, pb.ERROR_KIND_LIGHTCYCLER_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (asyncio.TimeoutError, pb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (TimeoutError, pb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (ConnectionError, pb.ERROR_KIND_CONNECTION, Code.UNAVAILABLE),
  (KeyError, pb.ERROR_KIND_KEY, Code.NOT_FOUND),
  (ValueError, pb.ERROR_KIND_VALUE, Code.INVALID_ARGUMENT),
  (RuntimeError, pb.ERROR_KIND_RUNTIME, Code.FAILED_PRECONDITION),
]

# The classes made again from their message alone, by kind.
_PLAIN: Dict["pb.ErrorKind", Type[BaseException]] = {
  pb.ERROR_KIND_LIGHTCYCLER: LightCyclerError,
  pb.ERROR_KIND_TIMEOUT: TimeoutError,
  pb.ERROR_KIND_CONNECTION: ConnectionError,
  pb.ERROR_KIND_KEY: KeyError,
  pb.ERROR_KIND_VALUE: ValueError,
  pb.ERROR_KIND_RUNTIME: RuntimeError,
}


def _kind_and_code(error: BaseException) -> Tuple["pb.ErrorKind", Code]:
  for cls, kind, code in _KINDS:
    if isinstance(error, cls):
      return kind, code
  return pb.ERROR_KIND_UNSPECIFIED, Code.UNKNOWN


def _message(error: BaseException) -> str:
  """What the error was made with, so making it again gives the same `str()`."""
  if len(error.args) == 1 and isinstance(error.args[0], str):
    return error.args[0]
  return str(error)


def to_error(error: BaseException) -> pb.Error:
  """An exception as an `Error`."""
  kind, _ = _kind_and_code(error)
  message = pb.Error(kind=kind, message=_message(error))
  if isinstance(error, CommandFailedError):
    message.command = error.command
    message.fields.extend(error.fields)
  elif isinstance(error, ExperimentFailedError):
    message.experiment_id = error.experiment_id
    message.reason = error.reason
  elif isinstance(error, LightCyclerTimeoutError):
    message.command = error.command
    if error.timeout is not None:
      message.timeout = error.timeout
  return message


def from_error(message: pb.Error) -> BaseException:
  """The exception an `Error` stands for."""
  kind = message.kind
  if kind == pb.ERROR_KIND_COMMAND_FAILED:
    return CommandFailedError(message.command, list(message.fields))
  if kind == pb.ERROR_KIND_EXPERIMENT_FAILED:
    return ExperimentFailedError(message.experiment_id, message.reason)
  if kind == pb.ERROR_KIND_LIGHTCYCLER_TIMEOUT:
    return LightCyclerTimeoutError(
      message.command, message.timeout if message.HasField("timeout") else None
    )
  if kind == pb.ERROR_KIND_PROTOCOL:
    return LightCyclerProtocolError(message.message)
  return _PLAIN.get(kind, Exception)(message.message)


def to_connect_error(error: BaseException) -> ConnectError:
  """An exception as a Connect error carrying its `Error`."""
  _, code = _kind_and_code(error)
  detail = AnyMessage(
    type_url=f"type.googleapis.com/{ERROR_TYPE}", value=to_error(error).SerializeToString()
  )
  return ConnectError(code, str(error), [detail])


def from_connect_error(error: ConnectError) -> Optional[BaseException]:
  """The exception a Connect error carries; None when it carries none."""
  for item in error.details:
    if item.type_name == ERROR_TYPE:
      return from_error(pb.Error.FromString(item.message_bytes))
  return None
