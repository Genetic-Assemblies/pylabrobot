"""A simulated Liconic: `ExperimentalLiconicBackend` with what its PLC answers made up.

`LiconicSimulator` is the backend with its serial port answering as the PLC does, from what it
keeps: its data memory (`WR DM`/`RD DM`), which cassette positions hold a plate, the transfer
station and the shovel, the climate and the shaker. Everything above `_send_command` is the real
backend's (its setup handshake and `_send_command` too), so it addresses a site through its racks
as it does on the device.

A handling step that cannot be done leaves the ready flag down and the error flag up with a
handling error code in DM200, as the PLC does; the backend reads it once it gives up waiting for
ready, after `error_wait` seconds here rather than its minute. The replies are modelled on the
backend's parsing, not on a device; nothing here has been checked against one.
"""

import asyncio
from typing import Dict, List, Optional, Set, Tuple, Union

from pylabrobot.legacy.barcode_scanners import BarcodeScanner
from pylabrobot.legacy.barcode_scanners.backend import BarcodeScannerBackend
from pylabrobot.legacy.storage.backend import IncubatorBackend
from pylabrobot.legacy.storage.liconic.constants import HandlingError, LiconicType
from pylabrobot.legacy.storage.liconic.liconic_backend import ExperimentalLiconicBackend
from pylabrobot.resources import PlateCarrier
from pylabrobot.resources.barcode import Barcode


class SimulatedBarcodeScannerBackend(BarcodeScannerBackend):
  """Reads the label of the plate the simulated Liconic's shovel is at: `SIM-<cassette>-<pos>`."""

  def __init__(self) -> None:
    super().__init__()
    self.at: Tuple[int, int] = (0, 0)

  async def setup(self) -> None:
    pass

  async def stop(self) -> None:
    pass

  async def scan_barcode(self) -> Barcode:
    cassette, position = self.at
    return Barcode(
      data=f"SIM-{cassette}-{position}", symbology="Code 128", position_on_resource="front"
    )


class LiconicSimulator(ExperimentalLiconicBackend):
  """A Liconic with no device behind it.

  Attributes:
    positions: the cassette positions that hold a plate, as (cassette, position), both from 1.
    transfer_station: whether a plate is on the transfer station.
    shovel: whether the shovel holds a plate.
    written: every command sent.
  """

  def __init__(
    self,
    model: Union[LiconicType, str] = LiconicType.STX44_IC,
    barcode_scanner: bool = True,
    strict_transfer_station: bool = True,
    move_time: float = 0.0,
    error_wait: float = 0.2,
  ):
    """
    Args:
      model: the Liconic it is.
      barcode_scanner: whether it has a (simulated) barcode reader.
      strict_transfer_station: whether a move refuses a transfer station that does not hold what
        it needs. A robot takes plates off it and puts them on without the Liconic being told; a
        simulator that is not strict takes it that the robot did.
      move_time: how long a handling step takes, in seconds.
      error_wait: how long the backend waits for ready before it reads a handling error.
    """
    IncubatorBackend.__init__(self)
    self.model = LiconicType(model) if isinstance(model, str) else model
    self._racks: List[PlateCarrier] = []
    self.scanner_backend = SimulatedBarcodeScannerBackend()
    self.barcode_scanner = BarcodeScanner(self.scanner_backend) if barcode_scanner else None
    self.co2_installed: Optional[bool] = None
    self.n2_installed: Optional[bool] = None
    self.strict_transfer_station = strict_transfer_station
    self.move_time = move_time
    self.error_wait = error_wait
    self.memory: Dict[int, int] = {890: 370, 893: 900, 894: 500, 895: 0, 39: 100}
    self.positions: Set[Tuple[int, int]] = set()
    self.transfer_station = False
    self.shovel = False
    self.door_open = False
    self.shaking = False
    self.swap_station_turned = False
    self.ready = True
    self.error: Optional[HandlingError] = None
    self.written: List[str] = []
    self.io = _SimulatedPort(self)  # type: ignore[assignment]

  def load(self, rack: int, site: int) -> None:
    """Put a plate in a site by hand: a rack's index and the site's key, both from 0."""
    self.positions.add((rack + 1, site + 1))

  async def _wait_ready(self, timeout: int = 60):
    await super()._wait_ready(timeout=self.error_wait if not self.ready else timeout)  # type: ignore[arg-type]

  def _fail(self, error: HandlingError) -> str:
    self.ready, self.error = False, error
    return "OK"

  def _at(self) -> Tuple[int, int]:
    return self.memory.get(0, 0), self.memory.get(5, 0)

  def _handle(self, step: int) -> str:
    """A handling step: ST 1904 to 1910."""
    at = self._at()
    if step == 1905:  # from a cassette position to the transfer station
      if self.transfer_station and self.strict_transfer_station:
        return self._fail(HandlingError.PLATE_TRANSFER_DETECTION_ERROR)
      if at not in self.positions:
        return self._fail(HandlingError.EXPORT_PLATE_LIFT_STACKER_IMPORT_ERROR)
      self.positions.discard(at)
      self.transfer_station = True
    elif step == 1904:  # from the transfer station to a cassette position
      if not self.transfer_station and self.strict_transfer_station:
        return self._fail(HandlingError.NO_PLATE_ON_SHOVEL_DETECTION)
      if at in self.positions:
        return self._fail(HandlingError.IMPORT_PLATE_LIFT_STACKER_PLACE_ERROR)
      self.transfer_station = False
      self.positions.add(at)
    elif step == 1908:  # from a cassette position onto the shovel
      if self.shovel:
        return self._fail(HandlingError.PLATE_GET_PLATE_ON_SHOVEL_DETECTION)
      if at not in self.positions:
        return self._fail(HandlingError.PLATE_GET_NO_PLATE_ON_SHOVEL_DETECTION)
      self.positions.discard(at)
      self.shovel = True
    elif step == 1909:  # from the shovel to a cassette position
      if not self.shovel:
        return self._fail(HandlingError.PLATE_PLACE_NO_PLATE_ON_SHOVEL_DETECTION)
      if at in self.positions:
        return self._fail(HandlingError.PLATE_PLACE_GENERAL_HANDLING_ERROR)
      self.shovel = False
      self.positions.add(at)
    elif step == 1910:  # the shovel to the barcode reader
      self.scanner_backend.at = at
    return "OK"

  async def answer(self, command: str) -> str:
    """What the PLC answers a command."""
    self.written.append(command)
    if command == "CR":
      return "CC"
    word, *args = command.split()
    if word == "WR" and args[0].startswith("DM"):
      self.memory[int(args[0][2:])] = int(args[1])
      return "OK"
    if word == "RD":
      if args[0].startswith("DM"):
        address = int(args[0][2:])
        if address == 200:
          return self.error.value if self.error is not None else "00000"
        # The actual values (982 to 985) are their setpoints (890, 893 to 895): it is at them.
        address = {982: 890, 983: 893, 984: 894, 985: 895}.get(address, address)
        return f"{self.memory.get(address, 0):05d}"
      flags = {
        "1915": self.ready,
        "1814": self.error is not None,
        "1914": self.transfer_station,
        "1912": self.swap_station_turned,
        "1812": self.shovel,
        "1813": self.transfer_station,
        "1807": False,
      }
      if args[0] in flags:
        return "1" if flags[args[0]] else "0"
    if word in ("ST", "RS") and args:
      flag = int(args[0])
      if word == "ST" and 1904 <= flag <= 1910 and flag not in (1906, 1907):
        if self.move_time:
          await asyncio.sleep(self.move_time)
        if not self.ready:
          return "OK"
        return self._handle(flag)
      if flag in (1900, 1801):
        self.ready, self.error = True, None
      elif flag == 1901:
        self.door_open = True
      elif flag == 1902:
        self.door_open = False
      elif flag == 1913:
        self.shaking = word == "ST"
      elif flag == 1912:
        self.swap_station_turned = word == "ST"
      return "OK"
    return "E1"


class _SimulatedPort:
  """The serial port of a simulated Liconic: what is written to it is answered by the PLC."""

  def __init__(self, plc: LiconicSimulator):
    self.plc = plc
    self.port = "simulation"
    self._reply = b""

  async def setup(self) -> None:
    pass

  async def stop(self) -> None:
    pass

  async def send_break(self, duration: float) -> None:
    pass

  async def reset_input_buffer(self) -> None:
    self._reply = b""

  async def reset_output_buffer(self) -> None:
    pass

  async def write(self, data: bytes) -> None:
    reply = await self.plc.answer(data.decode("ascii").strip())
    self._reply = reply.encode("ascii") + b"\r\n"

  async def read(self, num_bytes: int = 1) -> bytes:
    reply, self._reply = self._reply[:num_bytes], self._reply[num_bytes:]
    return reply

  async def readline(self) -> bytes:
    reply, self._reply = self._reply, b""
    return reply
