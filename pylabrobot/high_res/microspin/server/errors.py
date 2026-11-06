"""What a served call raised, as an `Error` message, and back: the client raises the same class,
with the same message, as the device would have raised in this process."""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Tuple, Type

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from protobuf.wkt import Any as AnyMessage

from pylabrobot.resources.server.errors import ServerError

from ..errors import (
  AmplifierDisabledError,
  DoorLockPinError,
  MicroSpinAbortedError,
  MicroSpinError,
  MicroSpinProtocolError,
  MicroSpinTimeoutError,
  NotHomedError,
  QueueTimeoutError,
)
from .v1 import microspin_pb2 as mpb

ERROR_TYPE = "pylabrobot.high_res.microspin.server.v1.Error"

# Each class and its kind and code, the subclasses ahead of what they derive from.
_KINDS: List[Tuple[Type[BaseException], mpb.ErrorKind, Code]] = [
  (DoorLockPinError, mpb.ERROR_KIND_DOOR_LOCK_PIN, Code.ABORTED),
  (AmplifierDisabledError, mpb.ERROR_KIND_AMPLIFIER_DISABLED, Code.ABORTED),
  (NotHomedError, mpb.ERROR_KIND_NOT_HOMED, Code.FAILED_PRECONDITION),
  (QueueTimeoutError, mpb.ERROR_KIND_QUEUE_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (MicroSpinError, mpb.ERROR_KIND_MICROSPIN, Code.ABORTED),
  (MicroSpinAbortedError, mpb.ERROR_KIND_ABORTED, Code.ABORTED),
  (MicroSpinTimeoutError, mpb.ERROR_KIND_MICROSPIN_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (MicroSpinProtocolError, mpb.ERROR_KIND_PROTOCOL, Code.INTERNAL),
  (ServerError, mpb.ERROR_KIND_RESOURCE_SERVER, Code.FAILED_PRECONDITION),
  (asyncio.TimeoutError, mpb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (TimeoutError, mpb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (ConnectionError, mpb.ERROR_KIND_CONNECTION, Code.UNAVAILABLE),
  (ValueError, mpb.ERROR_KIND_VALUE, Code.INVALID_ARGUMENT),
  (RuntimeError, mpb.ERROR_KIND_RUNTIME, Code.FAILED_PRECONDITION),
]

# The device's error classes made again from their command, id and lines, by kind.
_DEVICE_ERRORS: Dict[mpb.ErrorKind, Type[MicroSpinError]] = {
  mpb.ERROR_KIND_DOOR_LOCK_PIN: DoorLockPinError,
  mpb.ERROR_KIND_AMPLIFIER_DISABLED: AmplifierDisabledError,
  mpb.ERROR_KIND_NOT_HOMED: NotHomedError,
  mpb.ERROR_KIND_QUEUE_TIMEOUT: QueueTimeoutError,
  mpb.ERROR_KIND_MICROSPIN: MicroSpinError,
}

# The rest, made from their message alone.
_PLAIN: Dict[mpb.ErrorKind, Type[BaseException]] = {
  mpb.ERROR_KIND_TIMEOUT: TimeoutError,
  mpb.ERROR_KIND_CONNECTION: ConnectionError,
  mpb.ERROR_KIND_VALUE: ValueError,
  mpb.ERROR_KIND_RUNTIME: RuntimeError,
}


def _kind_and_code(error: BaseException) -> Tuple[mpb.ErrorKind, Code]:
  for cls, kind, code in _KINDS:
    if isinstance(error, cls):
      return kind, code
  return mpb.ERROR_KIND_UNSPECIFIED, Code.UNKNOWN


def to_error(error: BaseException) -> mpb.Error:
  """An exception as an `Error`."""
  kind, _ = _kind_and_code(error)
  message = mpb.Error(kind=kind, message=str(error))
  if isinstance(error, MicroSpinError):
    message.command = error.command
    message.command_id = error.command_id
    message.lines.extend(error.lines)
  elif isinstance(error, MicroSpinAbortedError):
    message.command = error.command
  elif isinstance(error, MicroSpinTimeoutError):
    message.command = error.command
    if error.command_id is not None:
      message.command_id = error.command_id
    if error.timeout is not None:
      message.timeout = error.timeout
  elif isinstance(error, MicroSpinProtocolError):
    message.command = error.command
  elif isinstance(error, ServerError):
    message.problem = error.problem
    message.resource_name = error.resource_name
  return message


def from_error(message: mpb.Error) -> BaseException:
  """The exception an `Error` stands for."""
  kind = message.kind
  device = _DEVICE_ERRORS.get(kind)
  if device is not None:
    return device(message.command, message.command_id, list(message.lines))
  if kind == mpb.ERROR_KIND_ABORTED:
    return MicroSpinAbortedError(message.command)
  if kind == mpb.ERROR_KIND_MICROSPIN_TIMEOUT:
    return MicroSpinTimeoutError(
      message.command,
      message.command_id if message.HasField("command_id") else None,
      message.timeout if message.HasField("timeout") else None,
    )
  if kind == mpb.ERROR_KIND_PROTOCOL:
    protocol = MicroSpinProtocolError(message.command, "", "")
    protocol.args = (message.message,)
    return protocol
  if kind == mpb.ERROR_KIND_RESOURCE_SERVER:
    return ServerError(message.problem, message.message, message.resource_name)
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
      return from_error(mpb.Error.FromString(item.message_bytes))
  return None
