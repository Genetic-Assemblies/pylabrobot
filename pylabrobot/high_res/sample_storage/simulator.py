"""A simulated HighRes sample store: what answers on its port 1000, without the device.

`SampleStorageSimulator` stands in for the store's socket (`store.io = SampleStorageSimulator()`),
so the driver runs unchanged and speaks its text protocol to it. It keeps which stacker slots and
nests hold a plate, the doors, whether it is homed and the environment's setpoints, and answers as
the device does: a pick from an empty slot is "No plate detected", one from an empty top slot
leaves the spatula out, as the real store does.

It is not the device: the replies are modelled on captures from a SteriStore (firmware 3.0.0.119)
and the manual, and nothing here has been checked against a TundraStore.
"""

from typing import Dict, List, Optional, Sequence, Set, Tuple

# Each stacker the simulated store has: its number and how many slots it has, and the slots' pitch.
DEFAULT_STACKERS: Tuple[Tuple[int, int, float], ...] = ((1, 24, 22.867), (2, 24, 22.867))


class SampleStorageSimulator:
  """The socket of a simulated HighRes sample store.

  Attributes:
    slots: the stacker slots that hold a plate, as (stacker, slot), slots from 1.
    nests: whether each nest, by number from 1, holds a plate.
    written: every command written to it, in order.
  """

  def __init__(
    self,
    stackers: Sequence[Tuple[int, int, float]] = DEFAULT_STACKERS,
    nests: int = 1,
    product_name: str = "TundraStore",
    environment: Optional[Dict[str, Tuple[float, Optional[float], Optional[float]]]] = None,
  ):
    """
    Args:
      stackers: each stacker's number, slot count and slot height.
      nests: how many nests it has.
      product_name: what it says it is.
      environment: each channel's current value, setpoint and limit; a TundraStore's by default.
    """
    self.stackers = list(stackers)
    self.slots: Set[Tuple[int, int]] = set()
    self.nests: Dict[int, bool] = {n: False for n in range(1, nests + 1)}
    self.product_name = product_name
    self.environment: Dict[str, Tuple[float, Optional[float], Optional[float]]] = (
      dict(environment)
      if environment is not None
      else {"TEMP": (4.0, 4.0, 4.0), "RH": (30.0, 30.0, 100.0)}
    )
    self.enabled: Set[str] = {"temp", "rh"}
    self.homed = False
    self.spatula_out = False
    self.spatula_holding = False
    self.doors_open = False
    self.aborted = False
    self.written: List[str] = []
    self._queue: List[str] = []
    self._id = 0

  # -- what a test or an operator does by hand --

  def load(self, stacker: int, slot: int) -> None:
    """Put a plate in a slot by hand."""
    self._slot_count(stacker, slot)
    self.slots.add((stacker, slot))

  # -- the socket --

  async def setup(self) -> None:
    pass

  async def stop(self) -> None:
    pass

  async def write(self, data: bytes, timeout: Optional[float] = None) -> None:
    command = data.decode("ascii").rstrip("\r\n")
    self.written.append(command)
    self._id += 1
    try:
      lines, status = self._answer(command), "OK!"
    except _Failed as failed:
      lines, status = failed.lines, failed.status
    self._queue = [f"ACK! {command} {self._id}", *lines, f"{status} {command} {self._id}"]

  async def readuntil(self, separator: bytes = b"\n", timeout: Optional[float] = None) -> bytes:
    if not self._queue:
      raise TimeoutError("the simulated store has nothing more to say")
    return self._queue.pop(0).encode("ascii") + b"\r\n"

  # -- the device --

  def _slot_count(self, stacker: int, slot: int) -> int:
    for number, count, _ in self.stackers:
      if number == stacker:
        if not 1 <= slot <= count:
          raise _Failed([f"Error 1: Invalid slot {slot} for stacker {stacker}"])
        return count
    raise _Failed([f"Error 1: Invalid stacker {stacker}"])

  def _nest(self, nest: int) -> None:
    if nest not in self.nests:
      raise _Failed([f"Error 1: Invalid nest {nest}"])

  def _require_ready(self) -> None:
    if self.aborted:
      raise _Failed([], status="ABORTED!")
    if not self.homed or self.spatula_out:
      raise _Failed(["Error 1: Machine must be homed"])

  def _answer(self, command: str) -> List[str]:
    word, *args = command.split()
    if word == "version":
      return [
        f"Product Name: {self.product_name}",
        "Serial Number: SIMULATED",
        "Firmware Version:     3.0.0.119",
        "Firmware Build: SIMULATED",
      ]
    if word == "homedstatus":
      return ["homed" if self.homed else "not homed"]
    if word == "status":
      y = 120.0 if self.spatula_out else 0.0
      return ["Carousel: 0.0", f"Y axis: {y}", "Z axis: 0.0"]
    if word == "doorstatus":
      state = "OPEN" if self.doors_open else "CLOSED"
      return ["User Door: CLOSED", f"RI: {state}", f"SEAL: {state}", f"RO1: {state}"]
    if word == "platestatus":
      return ["PLATE" if self.spatula_holding else "NO_PLATE"]
    if word == "neststatus":
      return [f"{n}: {'PLATE_AVAILABLE' if held else 'CLEAR'}" for n, held in self.nests.items()]
    if word == "environmentstatus":
      return [
        f"{name}:{current}/{'' if setpoint is None else setpoint}/{'' if limit is None else limit}"
        for name, (current, setpoint, limit) in self.environment.items()
      ]
    if word == "environmentset":
      channel, value = args[0].upper(), float(args[1])
      if channel not in self.environment:
        raise _Failed([f"Error 1: Unknown environment parameter {channel}"])
      _, _, limit = self.environment[channel]
      self.environment[channel] = (value, value, limit)
      return []
    if word == "environment":
      action, channel = args
      (self.enabled.add if action == "enable" else self.enabled.discard)(channel)
      return []
    if word == "getstackerdimensions":
      return [f"{n}: 0.000 {height:.3f} {count}" for n, count, height in self.stackers]
    if word == "settings":
      return [f"MACHINE_TYPE = {self.product_name}"]
    if word == "home":
      self.doors_open = False
      self.homed, self.spatula_out, self.aborted = True, False, False
      return []
    if word in ("enable", "clearabort"):
      self.aborted = False
      return []
    if word == "spatulaout":
      self.spatula_out = False
      return []
    if word == "openalldoors":
      self.doors_open = True
      return []
    if word == "closealldoors":
      self.doors_open = False
      return []
    if word == "barcode":
      return self._barcode(args)
    if word == "pick":
      return self._pick(*map(int, args))
    if word == "place":
      return self._place(*map(int, args))
    if word == "nesttransfer":
      return self._nest_transfer(*map(int, args))
    raise _Failed([f"Error 1: Unknown command {word}"])

  def _barcode(self, args: List[str]) -> List[str]:
    self._require_ready()
    if args[0] == "all":
      wanted = [(n, s) for n, count, _ in self.stackers for s in range(1, count + 1)]
    else:
      stacker = int(args[0])
      count = self._slot_count(stacker, int(args[1]) if len(args) > 1 else 1)
      wanted = (
        [(stacker, int(args[1]))] if len(args) > 1 else [(stacker, s) for s in range(1, count + 1)]
      )
    # A simulated plate has no label to read.
    return [f"{stacker} {slot}: EMPTY" for stacker, slot in wanted]

  def _pick(self, stacker: int, slot: int, nest: int) -> List[str]:
    self._require_ready()
    count = self._slot_count(stacker, slot)
    self._nest(nest)
    if self.nests[nest]:
      raise _Failed([f"Error 1: Nest {nest} is occupied"])
    if (stacker, slot) not in self.slots:
      if slot == count:
        # The real store cannot retract safely from an empty top slot.
        self.spatula_out = True
        raise _Failed(
          [
            f"Error 1: No plate detected at stacker {stacker} slot {slot}",
            "Error 2: Spatula is not in safe travel position",
          ]
        )
      raise _Failed([f"Error 1: No plate detected at stacker {stacker} slot {slot}"])
    self.slots.discard((stacker, slot))
    self.nests[nest] = True
    self.doors_open = False
    return []

  def _place(self, stacker: int, slot: int, nest: int) -> List[str]:
    self._require_ready()
    self._slot_count(stacker, slot)
    self._nest(nest)
    if not self.nests[nest]:
      raise _Failed([f"Error 1: No plate detected on nest {nest}"])
    if (stacker, slot) in self.slots:
      raise _Failed([f"Error 1: Stacker {stacker} slot {slot} is occupied"])
    self.nests[nest] = False
    self.slots.add((stacker, slot))
    self.doors_open = False
    return []

  def _nest_transfer(self, source: int, destination: int) -> List[str]:
    self._require_ready()
    self._nest(source)
    self._nest(destination)
    if not self.nests[source]:
      raise _Failed([f"Error 1: No plate detected on nest {source}"])
    if self.nests[destination]:
      raise _Failed([f"Error 1: Nest {destination} is occupied"])
    self.nests[source], self.nests[destination] = False, True
    return []


class _Failed(Exception):
  """A command the simulated device does not complete: its error lines and completion status."""

  def __init__(self, lines: List[str], status: str = "ERROR!"):
    super().__init__(*lines)
    self.lines = lines
    self.status = status
