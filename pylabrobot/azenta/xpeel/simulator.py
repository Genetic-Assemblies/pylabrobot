"""A simulated XPeel: the serial port of one, answering as the peeler would, under the real `XPeel`.

`SimulatedXPeel` is an `XPeel` whose port is an `XPeelPortSimulator`, so every one of its methods
runs as it does against hardware. The simulated peeler answers each command with the lines the
driver reads: `*ack` at once for a command that acts, then `*ready:EE,WW,00` when it is done; it
peels, moves and restarts in time, on a clock that may run faster than the real one, and counts
its tape down.

What is not the XPeel's own: the timings, which are plausible, not measured; the `*version` line;
that `*sealstat` answers with no reading of its own; and that `*tapeleft` answers with its counts,
in tens, as the first two fields of its ready line, which is what the driver reads.
"""

import asyncio
import logging
import time
from typing import List, Tuple

from pylabrobot.azenta.xpeel.xpeel import XPeel


class XPeelPortSimulator:
  """The serial port of a simulated XPeel: what is written to it are commands, what is read from it
  the peeler's answers, each when the peeler would send it.

  Attributes:
    written: every command written, decoded and stripped, in order.
    fault: an error code the next peel fails with, and every one after it until a restart; 0 is
      none.
    plate: whether a plate is on its stage.
    sealed: whether the plate on its stage is sealed.
    supply: seals left on its supply roll.
    takeup: seals there is room for on its take-up spool.
    peels: each peel it finished: its parameter set and adhere time code.
  """

  PEEL_SECONDS = 12.0
  FAST_PEEL_SECONDS = 8.0
  MOVE_SECONDS = 2.0
  RESTART_SECONDS = 15.0
  RESET_SECONDS = 3.0
  CHECK_SECONDS = 1.0
  # The longest a read waits for a line, in real seconds, before it reads nothing, as a serial
  # port's timeout makes it.
  READ_SECONDS = 0.5

  def __init__(self, speed: float = 1.0, supply: int = 300, takeup: int = 300):
    """
    Args:
      speed: how many times faster than a real one it runs.
      supply: seals left on its supply roll.
      takeup: seals there is room for on its take-up spool.
    """
    if speed <= 0:
      raise ValueError(f"speed must be more than 0, not {speed}")
    self.speed = speed
    self.written: List[str] = []
    self.fault = 0
    self.plate = True
    self.sealed = True
    self.supply = supply
    self.takeup = takeup
    self.plate_check = False
    self.peels: List[Tuple[int, int]] = []
    # The lines it will send, each with the real time it sends it.
    self._lines: List[Tuple[float, bytes]] = []
    self._changed = asyncio.Event()

  # -- the port --

  async def setup(self) -> None:
    pass

  async def stop(self) -> None:
    pass

  async def write(self, data: bytes) -> None:
    command = data.decode("ascii").strip()
    self.written.append(command)
    self._command(command)
    self._changed.set()

  async def readline(self) -> bytes:
    deadline = time.monotonic() + self.READ_SECONDS
    while True:
      now = time.monotonic()
      if self._lines and self._lines[0][0] <= now:
        return self._lines.pop(0)[1]
      wait = deadline - now
      if self._lines:
        wait = min(wait, self._lines[0][0] - now)
      if wait <= 0:
        return b""
      self._changed.clear()
      try:
        await asyncio.wait_for(self._changed.wait(), wait)
      except asyncio.TimeoutError:
        pass

  async def reset_input_buffer(self) -> None:
    now = time.monotonic()
    self._lines = [line for line in self._lines if line[0] > now]

  # -- the peeler --

  def _send(self, line: str, after: float = 0.0) -> None:
    """Send a line `after` simulated seconds after the last one it has yet to send."""
    at = max([time.monotonic()] + [sent for sent, _ in self._lines]) + after / self.speed
    self._lines.append((at, f"{line}\r\n".encode("ascii")))

  def _warning(self) -> int:
    if self.supply < 30:
      return 20
    if self.takeup < 30:
      return 21
    return 0

  def _ready(self, code: int = 0, after: float = 0.0) -> None:
    self._send(f"*ready:{code:02d},{self._warning():02d},00", after)

  def _command(self, command: str) -> None:
    name, _, argument = command.partition(":")
    if name == "*stat":
      self._ready(self.fault)
    elif name == "*version":
      self._send("*version:XPeel simulator")
    elif name == "*reset":
      self._send("*ack")
      self.fault = 0
      self._ready(after=self.RESET_SECONDS)
    elif name == "*restart":
      self._send("*ack")
      if self.supply > 0:
        self.fault = 0
      self._ready(self.fault, after=self.RESTART_SECONDS)
    elif name == "*sealcheck":
      self._send("*ack")
      code = 6 if not self.plate else 4 if self.sealed else 0
      self._send(f"*ready:{code:02d},00,00", self.CHECK_SECONDS)
    elif name == "*tapeleft":
      self._send("*ack")
      self._send(f"*ready:{self.supply // 10:02d},{self.takeup // 10:02d},00", self.CHECK_SECONDS)
    elif name == "*platecheck" and argument in ("y", "n"):
      self._send("*ack")
      self.plate_check = argument == "y"
      self._ready()
    elif name == "*sealstat":
      self._send("*ack")
      self._ready(after=self.CHECK_SECONDS)
    elif name in ("*sealhigher", "*seallower") and argument.isdigit():
      self._send("*ack")
      self._ready()
    elif name in ("*moveout", "*movein", "*movedown", "*moveup", "*movespool"):
      self._send("*ack")
      self._ready(after=self.MOVE_SECONDS)
    elif name == "*xpeel" and len(argument) == 2 and argument.isdigit():
      self._peel(int(argument[0]), int(argument[1]))
    else:
      self._ready(5)

  def _peel(self, parameter_set: int, adhere_time: int) -> None:
    if not (1 <= parameter_set <= 9 and 1 <= adhere_time <= 4):
      self._ready(5)
      return
    self._send("*ack")
    if self.supply <= 0 or self.takeup <= 0:
      self.fault = 7
    if self.plate_check and not self.plate:
      self._ready(6, after=self.MOVE_SECONDS)
      return
    if self.fault:
      self._ready(self.fault, after=self.MOVE_SECONDS)
      return
    fast = parameter_set in (1, 3, 5, 7)
    self.supply -= 1
    self.takeup -= 1
    self.sealed = False
    self.peels.append((parameter_set, adhere_time))
    self._ready(after=(self.FAST_PEEL_SECONDS if fast else self.PEEL_SECONDS) + adhere_time * 2.5)


class SimulatedXPeel(XPeel):
  """An `XPeel` on a simulated peeler's port: the driver's own methods, without hardware.

  Attributes:
    simulator: the simulated peeler, which is its port.
  """

  def __init__(
    self, port: str = "simulated", timeout: float = XPeel.RESPONSE_TIMEOUT, speed: float = 1.0
  ):
    """
    Args:
      port: what to call its port.
      timeout: as `XPeel`'s: how long it waits for an answer, in real seconds.
      speed: how many times faster than a real one the simulated peeler runs.
    """
    # Not XPeel.__init__: that opens a serial port.
    self.logger = logging.getLogger("pylabrobot.azenta.xpeel.xpeel")
    self.port = port
    self.response_timeout = timeout
    self.simulator = XPeelPortSimulator(speed)
    self.io = self.simulator  # type: ignore[assignment]
