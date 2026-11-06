"""What the MicroSpin answers when a command fails, as exceptions."""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Type

# One entry of the device's error stack, as it prints it:
# `Error 12: (12:18:42) 14: Unable to confirm door lock pin is in place`.
_ENTRY = re.compile(
  r"^Error (?P<index>\d+): \((?P<time>[0-9:]+)\) (?P<command_id>-?\d+): (?P<message>.*)$"
)


@dataclass(frozen=True)
class ErrorEntry:
  """One entry of the device's error stack.

  Attributes:
    index: where it is in the stack, counting from 1 at the oldest since power-on.
    time: the device's clock when it was added, `HH:MM:SS`.
    command_id: the id of the command it was raised for; below 1, one of the device's own processes.
    message: what the device says.
  """

  index: int
  time: str
  command_id: int
  message: str


def parse_error_entry(line: str) -> Optional[ErrorEntry]:
  """The error-stack entry a line holds, or None for a line that is not one."""
  match = _ENTRY.match(line.strip())
  if match is None:
    return None
  return ErrorEntry(
    index=int(match.group("index")),
    time=match.group("time"),
    command_id=int(match.group("command_id")),
    message=match.group("message").strip(),
  )


class MicroSpinError(Exception):
  """The device ended a command with `ERROR!`.

  Before `ERROR!` the device prints any warnings and then its whole error stack since power-on,
  oldest first. The entries raised for this command carry its id; when there are none, as when one
  of the device's own processes gave up on it, the newest entry is the nearest to an explanation.

  Attributes:
    command: the command sent.
    command_id: the id the device acknowledged it with.
    lines: every line the device printed for it, warnings and stack.
    entries: the error stack, oldest first.
    own_entries: the entries raised for this command.
    message: the newest of `own_entries`, else the newest entry, else the last line printed.
  """

  def __init__(self, command: str, command_id: int, lines: List[str]) -> None:
    self.command = command
    self.command_id = command_id
    self.lines = list(lines)
    self.entries = [entry for entry in map(parse_error_entry, lines) if entry is not None]
    self.own_entries = [entry for entry in self.entries if entry.command_id == command_id]
    explaining = self.own_entries or self.entries
    if explaining:
      self.message = explaining[-1].message
    elif lines:
      self.message = lines[-1]
    else:
      self.message = "no error detail"
    super().__init__(f"'{command}' (id {command_id}) failed: {self.message}")


class DoorLockPinError(MicroSpinError):
  """ "Unable to confirm door lock pin is in place".

  Seen ending `home`, `open` and `spin`, after the device printed `WARNING: Retry of door lock pin`
  lines.
  """


class AmplifierDisabledError(MicroSpinError):
  """ "Amplifier 1 hardware is disabled". Seen ending `open`."""


class NotHomedError(MicroSpinError):
  """The device is not homed: "Machine must be homed" ending `open`, "Device must be homed before
  spinning" ending `spin`. The device answers this way after power-on until `home`."""


class QueueTimeoutError(MicroSpinError):
  """The device's own time limit for the command ran out: "A command (54 - home), slot 0 in the
  queue, timed out."."""


# Each error the device has been seen to raise, by what its message says, lower-cased.
_ERRORS_BY_MESSAGE: Tuple[Tuple[str, Type[MicroSpinError]], ...] = (
  ("door lock pin", DoorLockPinError),
  ("amplifier", AmplifierDisabledError),
  ("must be homed", NotHomedError),
  ("in the queue, timed out", QueueTimeoutError),
)


def error_for(command: str, command_id: int, lines: List[str]) -> MicroSpinError:
  """The exception for a command the device ended with `ERROR!`, by what its error says."""
  error = MicroSpinError(command, command_id, lines)
  message = error.message.lower()
  for fragment, cls in _ERRORS_BY_MESSAGE:
    if fragment in message:
      return cls(command, command_id, lines)
  return error


class MicroSpinAbortedError(Exception):
  """The device ended a command with `ABORTED!`, as it does for a motion command an `abort`
  stopped."""

  def __init__(self, command: str) -> None:
    self.command = command
    super().__init__(f"'{command}' was aborted")


class MicroSpinTimeoutError(TimeoutError):
  """A command's last line did not arrive within its timeout.

  The device may still be running it, or may have given up on it without sending its last line.
  `MicroSpinDriver.request_command_status(command_id)` asks the device which.

  Attributes:
    command: the command sent.
    command_id: the id the device acknowledged it with, or None if it was not acknowledged.
    timeout: how long was waited, in seconds.
  """

  def __init__(self, command: str, command_id: Optional[int], timeout: Optional[float]) -> None:
    self.command = command
    self.command_id = command_id
    self.timeout = timeout
    acked = "" if command_id is None else f" (id {command_id})"
    super().__init__(f"'{command}'{acked} did not finish within {timeout} s")


class MicroSpinProtocolError(Exception):
  """The device answered with a line this driver cannot read."""

  def __init__(self, command: str, line: str, detail: str) -> None:
    self.command = command
    self.line = line
    super().__init__(f"answer to '{command}': {detail}; got {line!r}")
