"""A simulated Cytomat: `CytomatBackend` with what its serial port answers made up.

`CytomatSimulator` is the backend with `send_command` answering as the device's firmware does,
from what it keeps: which storage locations hold a plate, the transfer station, the handler, the
gate, the shakers and the climate. Everything above `send_command` is the real backend's, so it
numbers locations through its racks as it does on the device.

A move that cannot be done fails as the device's do: a command it refuses outright ("Transfer
station occupied") with that error, and one it starts and cannot finish through the error register,
which the backend reads when it waits for the move. The replies are modelled on the backend's
parsing, not on a device; nothing here has been checked against one.
"""

import asyncio
from typing import Dict, List, Optional, Set, Union

from pylabrobot.legacy.storage.backend import IncubatorBackend
from pylabrobot.legacy.storage.cytomat.constants import (
  ActionRegister,
  ActionType,
  CytomatType,
  ErrorRegister,
  OverviewRegister,
  SensorRegister,
)
from pylabrobot.legacy.storage.cytomat.cytomat import CytomatBackend
from pylabrobot.legacy.storage.cytomat.errors import error_map
from pylabrobot.resources import PlateCarrier


def _base_twelve(value: int) -> str:
  digits = ""
  while True:
    value, digit = divmod(value, 12)
    digits = "0123456789AB"[digit] + digits
    if value == 0:
      return digits


class CytomatSimulator(CytomatBackend):
  """A Cytomat with no device behind it.

  Attributes:
    locations: the storage locations that hold a plate, as the firmware names them ("003").
    transfer_station: whether a plate is on the transfer station.
    handler: whether the handler holds a plate, and where: "wait" or "exposed"; None when empty.
    written: every command sent, as the backend assembles it.
  """

  def __init__(
    self,
    model: Union[CytomatType, str] = CytomatType.C6000,
    strict_transfer_station: bool = True,
    move_time: float = 0.0,
  ):
    """
    Args:
      model: the Cytomat it is.
      strict_transfer_station: whether a move refuses a transfer station that does not hold what
        it needs. A robot takes plates off it and puts them on without the Cytomat being told; a
        simulator that is not strict takes it that the robot did.
      move_time: how long a move takes, in seconds.
    """
    IncubatorBackend.__init__(self)
    self.model = CytomatType(model) if isinstance(model, str) else model
    self._racks: List[PlateCarrier] = []
    self.strict_transfer_station = strict_transfer_station
    self.move_time = move_time
    self.locations: Set[str] = set()
    self.transfer_station = False
    self.handler: Optional[str] = None
    self.gate_open = False
    self.shovel_extended = False
    self.error_register = ErrorRegister.NO_ERROR
    self.shakers: Dict[int, int] = {1: 0, 2: 0}
    self.shaking = False
    # Each climate query, its nominal and actual value.
    self.climate: Dict[str, List[float]] = {
      "it": [37.0, 37.0],
      "ic": [5.0, 5.0],
      "ih": [90.0, 90.0],
      "io": [21.0, 21.0],
    }
    self.written: List[str] = []

  def location(self, rack: int, site: int) -> str:
    """The firmware's name for a site, from its rack's index and its key, as the backend makes it."""
    return self._site_to_firmware_string(self._racks[rack].sites[site])

  def load(self, rack: int, site: int) -> None:
    """Put a plate in a site by hand."""
    self.locations.add(self.location(rack, site))

  async def setup(self):
    await self.initialize()
    await self.wait_for_task_completion()

  async def stop(self):
    pass

  def _known(self, location: str) -> bool:
    """Whether a storage location names a site of its racks."""
    if self.model == CytomatType.C2C_425:
      rack, _, site = location.partition(" ")
      return (
        rack.isdigit()
        and int(rack) < len(self._racks)
        and int(site) in self._racks[int(rack)].sites
      )
    capacity = sum(rack.capacity for rack in self._racks)
    return location.isdigit() and 1 <= int(location) <= capacity

  def _overview(self) -> str:
    bits = {
      OverviewRegister.TRANSFER_STATION_OCCUPIED: self.transfer_station,
      OverviewRegister.DEVICE_DOOR_OPEN: False,
      OverviewRegister.AUTOMATIC_GATE_OPEN: self.gate_open,
      OverviewRegister.HANDLER_OCCUPIED: self.handler is not None,
      OverviewRegister.ERROR_REGISTER_SET: self.error_register != ErrorRegister.NO_ERROR,
      OverviewRegister.WARNING_REGISTER_SET: False,
      OverviewRegister.READY_BIT_SET: True,
      OverviewRegister.BUSY_BIT_SET: False,
    }
    binary = "".join("1" if bits[member] else "0" for member in sorted(bits, key=lambda m: m.value))
    return f"{int(binary, 2):02X}"

  def _sensors(self) -> str:
    states = {
      SensorRegister.INIT_SENSOR_HEIGHT_MOTOR: True,
      SensorRegister.INIT_SENSOR_CAROUSEL: True,
      SensorRegister.SHOVEL_RETRACTED: not self.shovel_extended,
      SensorRegister.SHOVEL_EXTENDED: self.shovel_extended,
      SensorRegister.SHOVEL_OCCUPIED: self.handler is not None,
      SensorRegister.GATE_OPENED: self.gate_open,
      SensorRegister.GATE_CLOSED: not self.gate_open,
      SensorRegister.TRANSFER_STATION_OCCUPIED: self.transfer_station,
      SensorRegister.TRANSFER_STATION_POSITION_1: True,
    }
    binary = "".join("1" if states.get(m, False) else "0" for m in SensorRegister)
    return _base_twelve(int(binary, 2))

  def _fail(self, error: ErrorRegister) -> str:
    """A move it starts and cannot finish: the error register says why."""
    self.error_register = error
    return self._overview()

  def _move(self, command: str, params: str) -> str:
    station_needed = {"ts": True, "tw": True, "st": False, "wt": False}
    if command in station_needed and self.transfer_station != station_needed[command]:
      if self.strict_transfer_station:
        raise error_map[0x31 if station_needed[command] else 0x32]
      self.transfer_station = station_needed[command]  # the robot saw to it
    takes_from_storage = command in ("st", "sw", "sh")
    puts_in_storage = command in ("ts", "ws", "hs")
    if (takes_from_storage or puts_in_storage) and not self._known(params):
      raise error_map[0x5]
    if takes_from_storage and params not in self.locations:
      return self._fail(ErrorRegister.NO_MTP_LOADED_ON_HANDLER_SHOVEL)
    if puts_in_storage and params in self.locations:
      return self._fail(ErrorRegister.NO_MTP_UNLOADED_FROM_HANDLER_SHOVEL)
    if command in ("ws", "wt", "wh") and self.handler != "wait":
      raise error_map[0x22]
    if command in ("hw", "hs") and self.handler != "exposed":
      raise error_map[0x22]
    if command in ("sw", "tw", "sh") and self.handler is not None:
      raise error_map[0x21]
    if takes_from_storage:
      self.locations.discard(params)
    if puts_in_storage:
      self.locations.add(params)
    if command in ("ts", "tw"):
      self.transfer_station = False
    if command in ("st", "wt"):
      self.transfer_station = True
    self.handler = {"sw": "wait", "tw": "wait", "hw": "wait", "sh": "exposed", "wh": "exposed"}.get(
      command
    )
    return self._overview()

  async def send_command(self, command_type: str, command: str, params: str) -> str:
    self.written.append(self._assemble_command(command_type, command, params).strip())
    if command_type == "mv" and command != "sn":
      if self.move_time:
        await asyncio.sleep(self.move_time)
      return self._move(command, params)
    if command_type == "ch":
      if command == "bs":
        return self._overview()
      if command == "bw":
        return "00"
      if command == "be":
        return self.error_register.value
      if command == "ba":
        target = int(ActionType.WAIT_POSITION.value, 16)
        action = int(ActionRegister.QUERY_SHOVEL_RETRACTED.value, 16)
        return f"{(target << 5) | action:02X}"
      if command == "sw":
        return f"1{int(self.transfer_station)}0"
      if command == "ts":
        return self._sensors()
      if command in self.climate:
        nominal, actual = self.climate[command]
        return f"+{nominal:05.1f} +{actual:05.1f}"
    if command_type == "rs" and command == "be":
      self.error_register = ErrorRegister.NO_ERROR
      return "00"
    if command_type == "ll":
      if command == "in":
        self.handler, self.shovel_extended = None, False
        return self._overview()
      if command == "gp":
        self.gate_open = params == "002"
        return self._overview()
      if command == "sp":
        self.shovel_extended = params == "002"
        return self._overview()
      if command == "vi":
        return "03"
      if command == "va":
        self.shaking = True
        return "03"
      if command == "vd":
        self.shaking = False
        return "00"
    if command_type == "se" and command.startswith("pb 2"):
      self.shakers[int(command[-1]) + 1] = int(params)
      return params
    if command_type == "mv" and command == "sn":
      return self._overview()
    raise error_map[0x2]
