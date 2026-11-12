"""A Liconic served elsewhere, driven as one in this process is.

`RemoteLiconicBackend` is an `ExperimentalLiconicBackend`: every public coroutine is a call to the
server, so `Incubator(backend=RemoteLiconicBackend("http://host:8093"), racks=..., ...)` drives the
served Liconic as it drives one on this computer's serial port. The racks the `Incubator` is given
are sent to the server when it is set up; the plates stay this process's, and each call that takes
one says where it is. A barcode the server reads onto a plate is put on this process's plate.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, Union

from pyqwest import Client

from pylabrobot.legacy.storage.backend import IncubatorBackend
from pylabrobot.legacy.storage.liconic import errors as liconic_errors
from pylabrobot.legacy.storage.liconic.constants import LiconicType
from pylabrobot.legacy.storage.liconic.liconic_backend import ExperimentalLiconicBackend
from pylabrobot.legacy.storage.liconic.server.serve import liconic_server_app
from pylabrobot.legacy.storage.liconic.server.v1 import liconic_pb2 as pb
from pylabrobot.legacy.storage.liconic.server.v1.liconic_connect import LiconicServiceClient
from pylabrobot.legacy.storage.server.errors import ErrorClasses, exception_classes
from pylabrobot.legacy.storage.server.remote import (
  BackendServer,
  plate_message,
  racks_request,
  site_ref,
)
from pylabrobot.legacy.storage.server.served import to_barcode
from pylabrobot.legacy.storage.server.v1 import incubator_pb2 as ipb
from pylabrobot.resources import Plate, PlateCarrier, PlateHolder, ResourceNotFoundError
from pylabrobot.resources.barcode import Barcode
from pylabrobot.resources.server.asgi_transport import ASGITransport
from pylabrobot.resources.server.client import _Headers

# The address a Liconic server held in this process is spoken to at; never dialled.
_IN_PROCESS = "http://liconic.in-process"

_ERRORS = ErrorClasses([*exception_classes(vars(liconic_errors)), ResourceNotFoundError])


class LiconicServer(BackendServer[LiconicServiceClient]):
  """A Liconic server: where a Liconic is served, and how its calls get there.

  `connect` reaches one served elsewhere; `local` serves a backend in this process, without a
  socket, as tests do.
  """

  def __init__(
    self, address: str, http: Optional[Client] = None, headers: Optional[Mapping[str, str]] = None
  ):
    interceptors = [_Headers(headers)] if headers else []
    client = LiconicServiceClient(address, http_client=http, interceptors=interceptors)
    super().__init__(address, client, _ERRORS)

  @classmethod
  def connect(cls, url: str, headers: Optional[Mapping[str, str]] = None) -> LiconicServer:
    """A Liconic server at `url`, "http://127.0.0.1:8093" say.

    Args:
      headers: sent with every call: the credentials the server asks for.
    """
    return cls(url, Client(), headers=headers)

  @classmethod
  def local(cls, backend: ExperimentalLiconicBackend) -> LiconicServer:
    """A backend served in this process, spoken to over Connect without a socket."""
    return cls(_IN_PROCESS, Client(transport=ASGITransport(liconic_server_app(backend))))


def _server(server: Union[str, LiconicServer]) -> LiconicServer:
  return LiconicServer.connect(server) if isinstance(server, str) else server


class RemoteLiconicBackend(ExperimentalLiconicBackend):
  """The Liconic a Liconic server serves: every public coroutine is a call to it.

  Attributes:
    model: the server's, known once setup has run.
  """

  def __init__(
    self,
    liconic_server: Union[str, LiconicServer],
    model: Union[LiconicType, str, None] = None,
  ):
    """
    Args:
      liconic_server: the server, or its URL.
      model: the Liconic it must be; setup refuses a server serving another. Its barcode reader,
        if it has one, is the server's.
    """
    IncubatorBackend.__init__(self)
    self.server = _server(liconic_server)
    self._expected = LiconicType(model) if isinstance(model, str) else model
    self.model = self._expected  # type: ignore[assignment]
    self._racks: List[PlateCarrier] = []
    self.barcode_scanner = None
    self.co2_installed: Optional[bool] = None
    self.n2_installed: Optional[bool] = None

  def serialize(self) -> dict:
    return {
      "type": type(self).__name__,
      "liconic_server": self.server.address,
      "model": None if self.model is None else self.model.value,
    }

  @classmethod
  def deserialize(cls, data: dict):
    return cls(liconic_server=data["liconic_server"], model=data.get("model"))

  async def _long(self, response: Any, what: str) -> pb.Progress:
    return await self.server.stream(response, what)

  async def _barcode(self, response: Any, what: str) -> Barcode:
    last = await self.server.stream(response, what)
    if not last.HasField("barcode"):
      raise ConnectionError(f"the Liconic server did not say what {what} read")
    return to_barcode(last.barcode)

  async def _move(self, plate: Plate, response: Any, what: str) -> None:
    """A move that may read the plate's barcode: what it read is put on the plate, even when the
    move then fails, as it is in this process."""

    def read(progress: pb.Progress) -> None:
      if progress.HasField("barcode"):
        plate.barcode = to_barcode(progress.barcode)

    await self.server.stream(response, what, read)

  async def _value(self, response: Any) -> float:
    value: float = (await self.server.call(response)).value
    return value

  # -- lifecycle --

  async def setup(self):
    await self.server.stream(self.server.client.setup(ipb.Empty()), "the setup")
    description = await self.server.call(self.server.client.describe(ipb.Empty()))
    model = LiconicType(description.model)
    if self._expected is not None and model != self._expected:
      raise ValueError(f"the server serves a {model.value}, not a {self._expected.value}")
    self.model = model

  async def stop(self):
    await self.server.call(self.server.client.stop(ipb.Empty()))

  async def set_racks(self, racks: List[PlateCarrier]):
    await IncubatorBackend.set_racks(self, racks)
    await self.server.call(self.server.client.set_racks(racks_request(racks)))

  async def initialize(self):
    await self._long(self.server.client.initialize(ipb.Empty()), "the initialization")

  async def open_door(self):
    await self._long(self.server.client.open_door(ipb.Empty()), "opening the door")

  async def close_door(self):
    await self._long(self.server.client.close_door(ipb.Empty()), "closing the door")

  # -- plates --

  async def fetch_plate_to_loading_tray(
    self, plate: Plate, read_barcode: bool = False, **backend_kwargs
  ):
    request = pb.FetchPlateToLoadingTrayRequest(
      plate=plate_message(plate, self._racks), read_barcode=read_barcode
    )
    await self._move(plate, self.server.client.fetch_plate_to_loading_tray(request), "the fetch")

  async def take_in_plate(
    self, plate: Plate, site: PlateHolder, read_barcode: bool = False, **backend_kwargs
  ):
    request = pb.TakeInPlateRequest(
      plate=plate_message(plate, self._racks), site=site_ref(site), read_barcode=read_barcode
    )
    await self._move(plate, self.server.client.take_in_plate(request), "the take-in")

  async def move_position_to_position(
    self, plate: Plate, dest_site: PlateHolder, read_barcode: bool = False
  ):
    # The server holds no plates, so whether the site is taken is this process's to say.
    if dest_site.resource is not None:
      raise RuntimeError(f"Position {dest_site} already has a plate assigned!")
    request = pb.MovePositionToPositionRequest(
      plate=plate_message(plate, self._racks),
      dest_site=site_ref(dest_site),
      read_barcode=read_barcode,
    )
    await self._move(plate, self.server.client.move_position_to_position(request), "the move")

  async def read_barcode_inline(self, cassette: int, plt_position: int) -> Barcode:
    request = pb.ReadBarcodeInlineRequest(cassette=cassette, plt_position=plt_position)
    return await self._barcode(self.server.client.read_barcode_inline(request), "the read")

  async def scan_barcode(self, site: PlateHolder) -> Barcode:
    request = ipb.SiteRequest(site=site_ref(site))
    return await self._barcode(self.server.client.scan_barcode(request), "the scan")

  # -- climate --

  async def set_temperature(self, temperature: float):
    request = pb.Temperature(temperature=temperature)
    await self._long(self.server.client.set_temperature(request), "setting the temperature")

  async def get_temperature(self) -> float:
    return await self._value(self.server.client.get_temperature(ipb.Empty()))

  async def get_target_temperature(self) -> float:
    return await self._value(self.server.client.get_target_temperature(ipb.Empty()))

  async def set_humidity(self, humidity: float):
    request = pb.Humidity(humidity=humidity)
    await self._long(self.server.client.set_humidity(request), "setting the humidity")

  async def get_humidity(self) -> float:
    return await self._value(self.server.client.get_humidity(ipb.Empty()))

  async def get_target_humidity(self) -> float:
    return await self._value(self.server.client.get_target_humidity(ipb.Empty()))

  async def set_co2_level(self, co2_level: float):
    request = pb.Co2Level(co2_level=co2_level)
    await self._long(self.server.client.set_co2_level(request), "setting the CO2 level")

  async def get_co2_level(self) -> float:
    return await self._value(self.server.client.get_co2_level(ipb.Empty()))

  async def get_target_co2_level(self) -> float:
    return await self._value(self.server.client.get_target_co2_level(ipb.Empty()))

  async def set_n2_level(self, n2_level: float):
    request = pb.N2Level(n2_level=n2_level)
    await self._long(self.server.client.set_n2_level(request), "setting the N2 level")

  async def get_n2_level(self) -> float:
    return await self._value(self.server.client.get_n2_level(ipb.Empty()))

  async def get_target_n2_level(self) -> float:
    return await self._value(self.server.client.get_target_n2_level(ipb.Empty()))

  # -- shaking, the swap station and sensors --

  async def shaker_status(self) -> int:
    return (await self.server.call(self.server.client.shaker_status(ipb.Empty()))).status

  async def get_shaker_speed(self) -> float:
    last = await self._long(self.server.client.get_shaker_speed(ipb.Empty()), "the read")
    return last.value

  async def start_shaking(self, frequency):
    request = pb.Frequency(frequency=frequency)
    await self._long(self.server.client.start_shaking(request), "starting to shake")

  async def stop_shaking(self):
    await self._long(self.server.client.stop_shaking(ipb.Empty()), "stopping shaking")

  async def turn_swap_station(self, home: bool):
    request = pb.TurnSwapStationRequest(home=home)
    await self.server.call(self.server.client.turn_swap_station(request))

  async def check_shovel_sensor(self) -> bool:
    return (await self.server.call(self.server.client.check_shovel_sensor(ipb.Empty()))).value

  async def check_transfer_sensor(self) -> bool:
    return (await self.server.call(self.server.client.check_transfer_sensor(ipb.Empty()))).value

  async def check_second_transfer_sensor(self) -> bool:
    response = await self.server.call(self.server.client.check_second_transfer_sensor(ipb.Empty()))
    return response.value
