"""What a served backend call raised, as a Connect error, and back: the client raises the same
class, with the same message, as the backend would have raised in this process."""

import asyncio
from typing import Dict, Iterable, List, Optional, Tuple, Type

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from protobuf.wkt import Any as AnyMessage

from pylabrobot.legacy.storage.server.v1 import incubator_pb2 as pb

ERROR_TYPE = "pylabrobot.legacy.storage.server.v1.Error"

# Each kind and the class it is, the subclasses ahead of what they derive from.
_KINDS: List[Tuple[Type[BaseException], int, Code]] = [
  (NotImplementedError, pb.ERROR_KIND_NOT_IMPLEMENTED, Code.UNIMPLEMENTED),
  (asyncio.TimeoutError, pb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (TimeoutError, pb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (ConnectionError, pb.ERROR_KIND_CONNECTION, Code.UNAVAILABLE),
  (KeyError, pb.ERROR_KIND_KEY, Code.INVALID_ARGUMENT),
  (TypeError, pb.ERROR_KIND_TYPE, Code.INVALID_ARGUMENT),
  (ValueError, pb.ERROR_KIND_VALUE, Code.INVALID_ARGUMENT),
  (AssertionError, pb.ERROR_KIND_ASSERTION, Code.FAILED_PRECONDITION),
  (AttributeError, pb.ERROR_KIND_ATTRIBUTE, Code.FAILED_PRECONDITION),
  (RuntimeError, pb.ERROR_KIND_RUNTIME, Code.FAILED_PRECONDITION),
]
_CLASSES: Dict[int, Type[BaseException]] = {pb.ERROR_KIND_UNSPECIFIED: Exception}
for _cls, _kind, _ in _KINDS:
  _CLASSES.setdefault(_kind, _cls)


def exception_classes(namespace: Dict[str, object]) -> List[Type[BaseException]]:
  """The exception classes a module defines: `exception_classes(vars(errors))`."""
  return [
    value
    for value in namespace.values()
    if isinstance(value, type)
    and issubclass(value, BaseException)
    and value.__module__ == namespace.get("__name__")
  ]


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
  any_detail = AnyMessage(
    type_url=f"type.googleapis.com/{ERROR_TYPE}", value=detail.SerializeToString()
  )
  return ConnectError(code, str(error), [any_detail])


class ErrorClasses:
  """The classes a client raises again as themselves: a device's own errors, by name."""

  def __init__(self, classes: Iterable[Type[BaseException]]):
    self.known: Dict[str, Type[BaseException]] = {cls.__name__: cls for cls in classes}

  def from_connect_error(self, error: ConnectError) -> Optional[BaseException]:
    """The error a call raised, from the Connect error it came as; None when it carries none."""
    for item in error.details:
      if item.type_name != ERROR_TYPE:
        continue
      detail = pb.Error.FromString(item.message_bytes)
      cls = self.known.get(detail.type_name) or _CLASSES.get(detail.kind, Exception)
      return cls(detail.message) if detail.message else cls()
    return None
