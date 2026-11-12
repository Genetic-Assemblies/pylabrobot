"""What a served call raised, as a Connect error, and back: the client raises the same class, with
the same message and the device's error lines, as the store would have raised in this process."""

import asyncio
from typing import Dict, List, Optional, Tuple, Type

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from protobuf.wkt import Any as AnyMessage

from pylabrobot.high_res.sample_storage.driver.errors import (
  HighResSampleStorageAbortedError,
  HighResSampleStorageError,
  HighResSampleStorageFault,
  HighResSampleStorageProtocolError,
  NoFreeSiteError,
  PlateNotFoundError,
)
from pylabrobot.high_res.sample_storage.server.v1 import sample_storage_pb2 as pb
from pylabrobot.resources.errors import ResourceNotFoundError

ERROR_TYPE = "pylabrobot.high_res.sample_storage.server.v1.Error"

# The classes a store raises that the client raises again as themselves, by name.
_KNOWN: Dict[str, Type[BaseException]] = {
  cls.__name__: cls
  for cls in (
    HighResSampleStorageError,
    HighResSampleStorageAbortedError,
    HighResSampleStorageProtocolError,
    HighResSampleStorageFault,
    PlateNotFoundError,
    NoFreeSiteError,
    ResourceNotFoundError,
  )
}

# Each kind and the class it is, the subclasses ahead of what they derive from.
_KINDS: List[Tuple[Type[BaseException], int, Code]] = [
  (NotImplementedError, pb.ERROR_KIND_NOT_IMPLEMENTED, Code.UNIMPLEMENTED),
  (asyncio.TimeoutError, pb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (TimeoutError, pb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (ConnectionError, pb.ERROR_KIND_CONNECTION, Code.UNAVAILABLE),
  (KeyError, pb.ERROR_KIND_KEY, Code.INVALID_ARGUMENT),
  (TypeError, pb.ERROR_KIND_TYPE, Code.INVALID_ARGUMENT),
  (ValueError, pb.ERROR_KIND_VALUE, Code.INVALID_ARGUMENT),
  (AttributeError, pb.ERROR_KIND_ATTRIBUTE, Code.FAILED_PRECONDITION),
  (RuntimeError, pb.ERROR_KIND_RUNTIME, Code.FAILED_PRECONDITION),
]
_CLASSES: Dict[int, Type[BaseException]] = {pb.ERROR_KIND_UNSPECIFIED: Exception}
for _cls, _kind, _ in _KINDS:
  _CLASSES.setdefault(_kind, _cls)


def _message(error: BaseException) -> str:
  """What the error was made with, so making it again gives the same `str()`."""
  if len(error.args) == 1 and isinstance(error.args[0], str):
    return error.args[0]
  return str(error)


def to_connect_error(error: BaseException) -> ConnectError:
  """An error a call raised, as a Connect error carrying an `Error` detail."""
  detail = pb.Error(message=_message(error), type_name=type(error).__name__)
  code = Code.UNKNOWN
  for cls, kind, kind_code in _KINDS:
    if isinstance(error, cls):
      detail.kind, code = kind, kind_code  # type: ignore[assignment]
      break
  if isinstance(error, (HighResSampleStorageError, HighResSampleStorageProtocolError)):
    code = Code.ABORTED
  detail.command = getattr(error, "command", "") or ""
  detail.error_lines.extend(getattr(error, "error_lines", []) or [])
  detail.response = getattr(error, "response", "") or ""
  detail.detail = getattr(error, "detail", "") or ""
  any_detail = AnyMessage(
    type_url=f"type.googleapis.com/{ERROR_TYPE}", value=detail.SerializeToString()
  )
  return ConnectError(code, str(error), [any_detail])


def from_connect_error(error: ConnectError) -> Optional[BaseException]:
  """The error a call raised, from the Connect error it came as; None when it carries none."""
  for item in error.details:
    if item.type_name != ERROR_TYPE:
      continue
    detail = pb.Error.FromString(item.message_bytes)
    known = _KNOWN.get(detail.type_name)
    if known is None:
      cls = _CLASSES.get(detail.kind, Exception)
      return cls(detail.message) if detail.message else cls()
    # Made without its own constructor, which builds the message from what it is given: the
    # message is the one the server's had, and its attributes are set as that one's were.
    raised = known.__new__(known)
    BaseException.__init__(raised, detail.message)
    if issubclass(known, (HighResSampleStorageError, HighResSampleStorageAbortedError)):
      raised.command = detail.command  # type: ignore[attr-defined]
    if issubclass(known, HighResSampleStorageError):
      raised.error_lines = list(detail.error_lines)  # type: ignore[attr-defined]
    if issubclass(known, HighResSampleStorageProtocolError):
      raised.command = detail.command  # type: ignore[attr-defined]
      raised.response = detail.response  # type: ignore[attr-defined]
      raised.detail = detail.detail  # type: ignore[attr-defined]
    return raised
  return None
