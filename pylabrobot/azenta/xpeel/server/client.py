"""An XPeel served elsewhere, driven as one in this process is.

`RemoteXPeel` is an `XPeel`: every public coroutine is a call to the server, and returns what the
served peeler's returned. A long call (a peel, a move, a check) reads the progress the server
streams until it says the call is done. Its port and response timeout are the server's, taken up by
setup.
"""

from typing import (
  AsyncIterator,
  Awaitable,
  Dict,
  List,
  Literal,
  Mapping,
  Optional,
  Sequence,
  Tuple,
  TypeVar,
  Union,
)

from connectrpc.errors import ConnectError
from pyqwest import Client

from pylabrobot.azenta.xpeel.server.errors import from_connect_error
from pylabrobot.azenta.xpeel.server.serve import SEAL_CHECKS, xpeel_server_app
from pylabrobot.azenta.xpeel.server.v1 import xpeel_pb2 as pb
from pylabrobot.azenta.xpeel.server.v1.xpeel_connect import XPeelServiceClient
from pylabrobot.azenta.xpeel.xpeel import XPeel
from pylabrobot.resources.server.asgi_transport import ASGITransport
from pylabrobot.resources.server.client import _Headers

# The address an XPeel server held in this process is spoken to at; never dialled.
_IN_PROCESS = "http://xpeel.in-process"

# What `XPeel.seal_check` returns, by how the proto numbers it.
_SEAL_CHECKS = {number: result for result, number in SEAL_CHECKS.items()}

R = TypeVar("R")


class XPeelServer:
  """An XPeel server: where peelers are served, and how their calls get there.

  `connect` reaches one served elsewhere; `local` serves peelers in this process, without a socket,
  as tests do.
  """

  def __init__(
    self, address: str, http: Optional[Client] = None, headers: Optional[Mapping[str, str]] = None
  ):
    interceptors = [_Headers(headers)] if headers else []
    self.address = address
    self.client = XPeelServiceClient(address, http_client=http, interceptors=interceptors)
    # Each peeler the server holds, as last described.
    self.described: Dict[str, pb.Peeler] = {}

  @classmethod
  def connect(cls, url: str, headers: Optional[Mapping[str, str]] = None) -> "XPeelServer":
    """An XPeel server at `url`, "http://127.0.0.1:8095" say.

    Args:
      headers: sent with every call: the credentials the server asks for.
    """
    return cls(url, Client(), headers=headers)

  @classmethod
  def local(cls, peelers: Mapping[str, XPeel]) -> "XPeelServer":
    """Peelers served in this process, spoken to over Connect without a socket."""
    return cls(_IN_PROCESS, Client(transport=ASGITransport(xpeel_server_app(peelers))))

  async def close(self) -> None:
    await self.client.close()

  async def call(self, response: Awaitable[R]) -> R:
    """A call's response, raising what the served peeler raised as it raised it."""
    try:
      return await response
    except ConnectError as error:
      raise (from_connect_error(error) or error) from None

  async def stream(self, progress: AsyncIterator[pb.Progress], what: str) -> pb.Progress:
    """Read a long call's progress until the server says it is done; the last, which says so.

    Raises:
      ConnectionError: If the stream ends before the call is done.
    """
    last: Optional[pb.Progress] = None
    try:
      async for each in progress:
        if each.done:
          last = each
    except ConnectError as error:
      raise (from_connect_error(error) or error) from None
    if last is None:
      raise ConnectionError(f"the XPeel server stopped before {what} was done")
    return last

  async def lines(self, progress: AsyncIterator[pb.Progress], what: str) -> List[str]:
    """The lines a long call returned."""
    return list((await self.stream(progress, what)).lines.lines)

  async def describe(self) -> Sequence[pb.Peeler]:
    """The peelers the server holds."""
    response = await self.call(self.client.describe(pb.DescribeRequest()))
    self.described = {peeler.name: peeler for peeler in response.peelers}
    return list(response.peelers)


class RemoteXPeel(XPeel):
  """The peeler of a name an XPeel server serves: an `XPeel` whose every public coroutine is a
  call.

  Its port and response timeout are the server's, known once setup has run; it has no serial port
  here.
  """

  def __init__(self, name: str, xpeel_server: Union[str, XPeelServer]):
    """
    Args:
      name: what the server calls the peeler.
      xpeel_server: the server, or its URL.
    """
    # Not XPeel.__init__: that opens a serial port, and the server has it.
    self.name = name
    self.server = (
      XPeelServer.connect(xpeel_server) if isinstance(xpeel_server, str) else xpeel_server
    )
    self.port = ""
    self.response_timeout = self.RESPONSE_TIMEOUT
    self._calls = self.server.client

  def __repr__(self) -> str:
    return f"RemoteXPeel(name={self.name!r}, xpeel_server={self.server.address!r})"

  async def _take_up(self) -> None:
    """Take up its port and response timeout from the server's description.

    Raises:
      ValueError: If the server serves no peeler of its name.
    """
    await self.server.describe()
    described = self.server.described.get(self.name)
    if described is None:
      raise ValueError(f"the server serves no peeler named '{self.name}'")
    self.port, self.response_timeout = described.port, described.response_timeout

  async def setup(self):
    await self.server.call(self._calls.setup(pb.SetupRequest(name=self.name)))
    await self._take_up()

  async def stop(self):
    await self.server.call(self._calls.stop(pb.StopRequest(name=self.name)))

  async def send_command(
    self, cmd, expect_ack=False, wait_for_ready=False, clear_buffer=True
  ) -> List[str]:
    request = pb.SendCommandRequest(
      name=self.name,
      cmd=cmd,
      expect_ack=expect_ack,
      wait_for_ready=wait_for_ready,
      clear_buffer=clear_buffer,
    )
    return await self.server.lines(self._calls.send_command(request), f"{cmd}")

  async def request_status(self) -> Tuple[int, int, int]:
    request = pb.RequestStatusRequest(name=self.name)
    response = await self.server.call(self._calls.request_status(request))
    return response.first, response.second, response.third

  async def request_version(self):
    request = pb.RequestVersionRequest(name=self.name)
    return list((await self.server.call(self._calls.request_version(request))).lines)

  async def reset(self):
    request = pb.ResetRequest(name=self.name)
    return await self.server.lines(self._calls.reset(request), "the reset")

  async def seal_check(self) -> Literal["seal_detected", "no_seal", "plate_not_detected"]:
    request = pb.SealCheckRequest(name=self.name)
    done = await self.server.stream(self._calls.seal_check(request), "the seal check")
    return _SEAL_CHECKS[done.seal_check]  # type: ignore[return-value]

  async def request_tape_remaining(self):
    request = pb.RequestTapeRemainingRequest(name=self.name)
    done = await self.server.stream(self._calls.request_tape_remaining(request), "the tape request")
    return done.tape_remaining.supply_remaining, done.tape_remaining.takeup_remaining

  async def enable_plate_check(self, enabled=True):
    request = pb.EnablePlateCheckRequest(name=self.name, enabled=enabled)
    return await self.server.lines(self._calls.enable_plate_check(request), "the plate check")

  async def request_seal_sensor_status(self):
    request = pb.RequestSealSensorStatusRequest(name=self.name)
    return await self.server.lines(
      self._calls.request_seal_sensor_status(request), "the seal sensor request"
    )

  async def set_seal_threshold_upper(self, value: int):
    request = pb.SetSealThresholdUpperRequest(name=self.name, value=value)
    return await self.server.lines(self._calls.set_seal_threshold_upper(request), "the threshold")

  async def set_seal_threshold_lower(self, value: int):
    request = pb.SetSealThresholdLowerRequest(name=self.name, value=value)
    return await self.server.lines(self._calls.set_seal_threshold_lower(request), "the threshold")

  async def move_conveyor_out(self):
    request = pb.MoveConveyorOutRequest(name=self.name)
    return await self.server.lines(self._calls.move_conveyor_out(request), "the move")

  async def move_conveyor_in(self):
    request = pb.MoveConveyorInRequest(name=self.name)
    return await self.server.lines(self._calls.move_conveyor_in(request), "the move")

  async def move_elevator_down(self):
    request = pb.MoveElevatorDownRequest(name=self.name)
    return await self.server.lines(self._calls.move_elevator_down(request), "the move")

  async def move_elevator_up(self):
    request = pb.MoveElevatorUpRequest(name=self.name)
    return await self.server.lines(self._calls.move_elevator_up(request), "the move")

  async def advance_tape(self):
    request = pb.AdvanceTapeRequest(name=self.name)
    return await self.server.lines(self._calls.advance_tape(request), "the tape advance")

  async def peel(
    self,
    begin_location: Literal[-2, 0, 2, 4] = 0,
    fast: bool = False,
    adhere_time: float = 2.5,
  ):
    request = pb.PeelRequest(
      name=self.name, begin_location=begin_location, fast=fast, adhere_time=adhere_time
    )
    return await self.server.lines(self._calls.peel(request), "the peel")

  async def restart(self):
    request = pb.RestartRequest(name=self.name)
    return await self.server.lines(self._calls.restart(request), "the restart")
