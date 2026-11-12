"""What the LightCycler driver raises."""

from typing import List, Optional, Sequence


class LightCyclerError(Exception):
  """Something the instrument, or a run on it, did not do."""


class CommandFailedError(LightCyclerError):
  """The instrument answered a command with a status other than 0.

  Attributes:
    command: the command's message name, `CreateExperiment` say.
    fields: every field of the answer; the first is the status.
  """

  def __init__(self, command: str, fields: Sequence[str]) -> None:
    self.command = command
    self.fields: List[str] = list(fields)
    super().__init__(f"{command} failed: the instrument answered {self.fields}")


class LightCyclerProtocolError(LightCyclerError):
  """The instrument answered with something this driver cannot read."""


class ExperimentFailedError(LightCyclerError):
  """An experiment did not finish.

  Attributes:
    experiment_id: the experiment's id.
    reason: why, as the error that stopped it said.
  """

  def __init__(self, experiment_id: str, reason: str) -> None:
    self.experiment_id = experiment_id
    self.reason = reason
    super().__init__(f"experiment {experiment_id} failed: {reason}")


class LightCyclerTimeoutError(TimeoutError):
  """The instrument did not answer a command in time.

  Attributes:
    command: the command's message name.
    timeout: how long was waited, in seconds.
  """

  def __init__(self, command: str, timeout: Optional[float]) -> None:
    self.command = command
    self.timeout = timeout
    super().__init__(f"{command} was not answered within {timeout} s")
