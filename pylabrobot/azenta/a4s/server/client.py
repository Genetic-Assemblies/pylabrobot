"""An a4S served elsewhere, driven as one in this process is.

`RemoteA4S` is an `A4S`: every public coroutine is a call to the server, and returns what the
served sealer's returned. A long call (a seal, a shuttle move, a wait) reads the progress the
server streams until it says the call is done. Its port and timeout are the server's, taken up by
setup.
"""

from typing import AsyncIterator, Awaitable, Dict, Mapping, Optional, Sequence, Set, TypeVar, Union

from connectrpc.errors import ConnectError
from pyqwest import Client

from pylabrobot.azenta.a4s.a4s import A4S, A4SStatus
from pylabrobot.azenta.a4s.server.errors import from_connect_error
from pylabrobot.azenta.a4s.server.serve import a4s_server_app, status_from_proto
from pylabrobot.azenta.a4s.server.v1 import a4s_pb2 as pb
from pylabrobot.azenta.a4s.server.v1.a4s_connect import A4SServiceClient
from pylabrobot.resources.server.asgi_transport import ASGITransport
from pylabrobot.resources.server.client import _Headers

# The address an a4S server held in this process is spoken to at; never dialled.
_IN_PROCESS = "http://a4s.in-process"

R = TypeVar("R")


class A4SServer:
  """An a4S server: where sealers are served, and how their calls get there.

  `connect` reaches one served elsewhere; `local` serves sealers in this process, without a socket,
  as tests do.
  """

  def __init__(
    self, address: str, http: Optional[Client] = None, headers: Optional[Mapping[str, str]] = None
  ):
    interceptors = [_Headers(headers)] if headers else []
    self.address = address
    self.client = A4SServiceClient(address, http_client=http, interceptors=interceptors)
    # Each sealer the server holds, as last described.
    self.described: Dict[str, pb.Sealer] = {}

  @classmethod
  def connect(cls, url: str, headers: Optional[Mapping[str, str]] = None) -> "A4SServer":
    """An a4S server at `url`, "http://127.0.0.1:8094" say.

    Args:
      headers: sent with every call: the credentials the server asks for.
    """
    return cls(url, Client(), headers=headers)

  @classmethod
  def local(cls, sealers: Mapping[str, A4S]) -> "A4SServer":
    """Sealers served in this process, spoken to over Connect without a socket."""
    return cls(_IN_PROCESS, Client(transport=ASGITransport(a4s_server_app(sealers))))

  async def close(self) -> None:
    await self.client.close()

  async def call(self, response: Awaitable[R]) -> R:
    """A call's response, raising what the served sealer raised as it raised it."""
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
      raise ConnectionError(f"the a4S server stopped before {what} was done")
    return last

  async def stream_status(self, progress: AsyncIterator[pb.Progress], what: str) -> A4SStatus:
    """The status a long call returned."""
    done = await self.stream(progress, what)
    if not done.HasField("status"):
      raise ConnectionError(f"the a4S server did not say the status {what} returned")
    return status_from_proto(done.status)

  async def describe(self) -> Sequence[pb.Sealer]:
    """The sealers the server holds."""
    response = await self.call(self.client.describe(pb.DescribeRequest()))
    self.described = {sealer.name: sealer for sealer in response.sealers}
    return list(response.sealers)


class RemoteA4S(A4S):
  """The sealer of a name an a4S server serves: an `A4S` whose every public coroutine is a call.

  Its port and timeout are the server's, known once setup has run; it has no serial port here.
  """

  def __init__(self, name: str, a4s_server: Union[str, A4SServer]):
    """
    Args:
      name: what the server calls the sealer.
      a4s_server: the server, or its URL.
    """
    # Not A4S.__init__: that opens a serial port, and the server has it.
    self.name = name
    self.server = A4SServer.connect(a4s_server) if isinstance(a4s_server, str) else a4s_server
    self.port = ""
    self.timeout = 0
    self._calls = self.server.client

  def __repr__(self) -> str:
    return f"RemoteA4S(name={self.name!r}, a4s_server={self.server.address!r})"

  async def _take_up(self) -> None:
    """Take up its port and timeout from the server's description.

    Raises:
      ValueError: If the server serves no sealer of its name.
    """
    await self.server.describe()
    described = self.server.described.get(self.name)
    if described is None:
      raise ValueError(f"the server serves no sealer named '{self.name}'")
    self.port, self.timeout = described.port, described.timeout

  async def setup(self):
    await self.server.stream(self._calls.setup(pb.SetupRequest(name=self.name)), "setup")
    await self._take_up()

  async def stop(self):
    await self.server.stream(self._calls.stop(pb.StopRequest(name=self.name)), "stop")

  async def send_command(self, command: str):
    request = pb.SendCommandRequest(name=self.name, command=command)
    await self.server.call(self._calls.send_command(request))

  async def read_message(self) -> str:
    request = pb.ReadMessageRequest(name=self.name)
    return (await self.server.call(self._calls.read_message(request))).message

  async def request_status(self) -> A4SStatus:
    request = pb.RequestStatusRequest(name=self.name)
    return status_from_proto(await self.server.call(self._calls.request_status(request)))

  async def wait_for_status(self, statuses: Set[A4SStatus.SystemStatus]) -> A4SStatus:
    request = pb.WaitForStatusRequest(
      name=self.name,
      statuses=[status.value for status in statuses],  # type: ignore[misc]
    )
    return await self.server.stream_status(
      self._calls.wait_for_status(request), "the wait for status"
    )

  async def wait_for_shuttle_open_sensor(
    self, shuttle_open: bool, timeout: float = 30.0
  ) -> A4SStatus:
    request = pb.WaitForShuttleOpenSensorRequest(
      name=self.name, shuttle_open=shuttle_open, timeout=timeout
    )
    return await self.server.stream_status(
      self._calls.wait_for_shuttle_open_sensor(request), "the wait for the shuttle"
    )

  async def system_reset(self) -> A4SStatus:
    request = pb.SystemResetRequest(name=self.name)
    return await self.server.stream_status(self._calls.system_reset(request), "the reset")

  async def set_heater(self, on: bool) -> A4SStatus:
    request = pb.SetHeaterRequest(name=self.name, on=on)
    return await self.server.stream_status(self._calls.set_heater(request), "set_heater")

  async def set_time(self, seconds: float):
    request = pb.SetTimeRequest(name=self.name, seconds=seconds)
    await self.server.call(self._calls.set_time(request))

  async def request_remaining_time(self) -> int:
    request = pb.RequestRemainingTimeRequest(name=self.name)
    return (await self.server.call(self._calls.request_remaining_time(request))).remaining_time

  async def seal(self, temperature: int, duration: float) -> A4SStatus:
    request = pb.SealRequest(name=self.name, temperature=temperature, duration=duration)
    return await self.server.stream_status(self._calls.seal(request), "the seal")

  async def open(self) -> A4SStatus:
    request = pb.OpenShuttleRequest(name=self.name)
    return await self.server.stream_status(self._calls.open_shuttle(request), "opening")

  async def close(self) -> A4SStatus:
    request = pb.CloseShuttleRequest(name=self.name)
    return await self.server.stream_status(self._calls.close_shuttle(request), "closing")

  async def set_temperature(self, temperature: float):
    request = pb.SetTemperatureRequest(name=self.name, temperature=temperature)
    await self.server.stream(self._calls.set_temperature(request), "set_temperature")

  async def request_current_temperature(self) -> float:
    request = pb.RequestCurrentTemperatureRequest(name=self.name)
    response = await self.server.call(self._calls.request_current_temperature(request))
    return response.temperature

  async def deactivate(self):
    request = pb.DeactivateRequest(name=self.name)
    await self.server.stream(self._calls.deactivate(request), "deactivate")
