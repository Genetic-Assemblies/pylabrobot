"""A thermocycler served elsewhere, driven as one in this process is.

`RemoteThermocyclerBackend` is a `ThermocyclerBackend`: every method of the interface is a call to
the server, made on the backend of the thermocycler of its name, so
`Thermocycler(backend=RemoteThermocyclerBackend(name, url), ...)` runs as it does on that backend
here. A backend's own keyword arguments (`block_id=0` say), as `Thermocycler` passes them on, go to
the served backend as they are; they must be things JSON can say. A long call (setup, a lid move, a
temperature, a run) reads the progress the server streams until it says the call is done.
"""

from typing import (
  Any,
  AsyncIterator,
  Awaitable,
  Dict,
  List,
  Mapping,
  Optional,
  Sequence,
  TypeVar,
  Union,
)

from connectrpc.errors import ConnectError
from pyqwest import Client

from pylabrobot.legacy.thermocycling.backend import ThermocyclerBackend
from pylabrobot.legacy.thermocycling.server.errors import from_connect_error
from pylabrobot.legacy.thermocycling.server.serve import (
  kwargs_to_json,
  protocol_to_proto,
  thermocycler_server_app,
)
from pylabrobot.legacy.thermocycling.server.v1 import thermocycler_pb2 as pb
from pylabrobot.legacy.thermocycling.server.v1.thermocycler_connect import (
  ThermocyclerServiceClient,
)
from pylabrobot.legacy.thermocycling.standard import BlockStatus, LidStatus, Protocol
from pylabrobot.resources.server.asgi_transport import ASGITransport
from pylabrobot.resources.server.client import _Headers

# The address a thermocycler server held in this process is spoken to at; never dialled.
_IN_PROCESS = "http://thermocycler.in-process"

_LID_STATUSES = {
  pb.LID_STATUS_IDLE: LidStatus.IDLE,
  pb.LID_STATUS_HOLDING_AT_TARGET: LidStatus.HOLDING_AT_TARGET,
}
_BLOCK_STATUSES = {
  pb.BLOCK_STATUS_IDLE: BlockStatus.IDLE,
  pb.BLOCK_STATUS_HOLDING_AT_TARGET: BlockStatus.HOLDING_AT_TARGET,
}

R = TypeVar("R")


class ThermocyclerServer:
  """A thermocycler server: where thermocyclers are served, and how their calls get there.

  `connect` reaches one served elsewhere; `local` serves backends in this process, without a
  socket, as tests do.
  """

  def __init__(
    self, address: str, http: Optional[Client] = None, headers: Optional[Mapping[str, str]] = None
  ):
    interceptors = [_Headers(headers)] if headers else []
    self.address = address
    self.client = ThermocyclerServiceClient(address, http_client=http, interceptors=interceptors)

  @classmethod
  def connect(cls, url: str, headers: Optional[Mapping[str, str]] = None) -> "ThermocyclerServer":
    """A thermocycler server at `url`, "http://127.0.0.1:8096" say.

    Args:
      headers: sent with every call: the credentials the server asks for.
    """
    return cls(url, Client(), headers=headers)

  @classmethod
  def local(cls, thermocyclers: Mapping[str, ThermocyclerBackend]) -> "ThermocyclerServer":
    """Thermocyclers' backends served in this process, spoken to over Connect without a socket."""
    app = thermocycler_server_app(thermocyclers)
    return cls(_IN_PROCESS, Client(transport=ASGITransport(app)))

  async def close(self) -> None:
    await self.client.close()

  async def call(self, response: Awaitable[R]) -> R:
    """A call's response, raising what the served backend raised as it raised it."""
    try:
      return await response
    except ConnectError as error:
      raise (from_connect_error(error) or error) from None

  async def stream(self, progress: AsyncIterator[pb.Progress], what: str) -> None:
    """Read a long call's progress until the server says it is done.

    Raises:
      ConnectionError: If the stream ends before the call is done.
    """
    done = False
    try:
      async for each in progress:
        done = done or each.done
    except ConnectError as error:
      raise (from_connect_error(error) or error) from None
    if not done:
      raise ConnectionError(f"the thermocycler server stopped before {what} was done")

  async def describe(self) -> Sequence[pb.Thermocycler]:
    """The thermocyclers the server holds, each with its backend's class."""
    return list((await self.call(self.client.describe(pb.DescribeRequest()))).thermocyclers)


class RemoteThermocyclerBackend(ThermocyclerBackend):
  """The backend of the thermocycler of a name a thermocycler server serves: every method of the
  `ThermocyclerBackend` interface is a call to it."""

  def __init__(self, name: str, thermocycler_server: Union[str, ThermocyclerServer]):
    """
    Args:
      name: what the server calls the thermocycler.
      thermocycler_server: the server, or its URL.
    """
    super().__init__()
    self.name = name
    if isinstance(thermocycler_server, str):
      thermocycler_server = ThermocyclerServer.connect(thermocycler_server)
    self.server = thermocycler_server
    self._calls = thermocycler_server.client

  def __repr__(self) -> str:
    return (
      f"RemoteThermocyclerBackend(name={self.name!r}, thermocycler_server={self.server.address!r})"
    )

  def serialize(self) -> dict:
    return {
      **super().serialize(),
      "name": self.name,
      "thermocycler_server": self.server.address,
    }

  def _get(self, backend_kwargs: Dict[str, Any]) -> pb.GetRequest:
    return pb.GetRequest(name=self.name, backend_kwargs=kwargs_to_json(backend_kwargs))

  async def setup(self, **backend_kwargs):
    request = pb.SetupRequest(name=self.name, backend_kwargs=kwargs_to_json(backend_kwargs))
    await self.server.stream(self._calls.setup(request), "setup")

  async def stop(self):
    await self.server.call(self._calls.stop(pb.StopRequest(name=self.name)))

  async def open_lid(self, **backend_kwargs):
    request = pb.OpenLidRequest(name=self.name, backend_kwargs=kwargs_to_json(backend_kwargs))
    await self.server.stream(self._calls.open_lid(request), "opening the lid")

  async def close_lid(self, **backend_kwargs):
    request = pb.CloseLidRequest(name=self.name, backend_kwargs=kwargs_to_json(backend_kwargs))
    await self.server.stream(self._calls.close_lid(request), "closing the lid")

  async def set_block_temperature(self, temperature: List[float], **backend_kwargs):
    request = pb.SetBlockTemperatureRequest(
      name=self.name, temperature=temperature, backend_kwargs=kwargs_to_json(backend_kwargs)
    )
    await self.server.stream(self._calls.set_block_temperature(request), "set_block_temperature")

  async def set_lid_temperature(self, temperature: List[float], **backend_kwargs):
    request = pb.SetLidTemperatureRequest(
      name=self.name, temperature=temperature, backend_kwargs=kwargs_to_json(backend_kwargs)
    )
    await self.server.stream(self._calls.set_lid_temperature(request), "set_lid_temperature")

  async def deactivate_block(self, **backend_kwargs):
    request = pb.DeactivateBlockRequest(
      name=self.name, backend_kwargs=kwargs_to_json(backend_kwargs)
    )
    await self.server.call(self._calls.deactivate_block(request))

  async def deactivate_lid(self, **backend_kwargs):
    request = pb.DeactivateLidRequest(name=self.name, backend_kwargs=kwargs_to_json(backend_kwargs))
    await self.server.call(self._calls.deactivate_lid(request))

  async def run_protocol(self, protocol: Protocol, block_max_volume: float, **backend_kwargs):
    request = pb.RunProtocolRequest(
      name=self.name,
      protocol=protocol_to_proto(protocol),
      block_max_volume=block_max_volume,
      backend_kwargs=kwargs_to_json(backend_kwargs),
    )
    await self.server.stream(self._calls.run_protocol(request), "the protocol")

  async def get_block_current_temperature(self, **backend_kwargs) -> List[float]:
    request = self._get(backend_kwargs)
    response = await self.server.call(self._calls.get_block_current_temperature(request))
    return list(response.temperature)

  async def get_block_target_temperature(self, **backend_kwargs) -> List[float]:
    request = self._get(backend_kwargs)
    response = await self.server.call(self._calls.get_block_target_temperature(request))
    return list(response.temperature)

  async def get_lid_current_temperature(self, **backend_kwargs) -> List[float]:
    request = self._get(backend_kwargs)
    response = await self.server.call(self._calls.get_lid_current_temperature(request))
    return list(response.temperature)

  async def get_lid_target_temperature(self, **backend_kwargs) -> List[float]:
    request = self._get(backend_kwargs)
    response = await self.server.call(self._calls.get_lid_target_temperature(request))
    return list(response.temperature)

  async def get_lid_open(self, **backend_kwargs) -> bool:
    response = await self.server.call(self._calls.get_lid_open(self._get(backend_kwargs)))
    return response.open

  async def get_lid_status(self, **backend_kwargs) -> LidStatus:
    response = await self.server.call(self._calls.get_lid_status(self._get(backend_kwargs)))
    return _LID_STATUSES[response.status]

  async def get_block_status(self, **backend_kwargs) -> BlockStatus:
    response = await self.server.call(self._calls.get_block_status(self._get(backend_kwargs)))
    return _BLOCK_STATUSES[response.status]

  async def get_hold_time(self, **backend_kwargs) -> float:
    response = await self.server.call(self._calls.get_hold_time(self._get(backend_kwargs)))
    return response.seconds

  async def get_current_cycle_index(self, **backend_kwargs) -> int:
    request = self._get(backend_kwargs)
    return (await self.server.call(self._calls.get_current_cycle_index(request))).value

  async def get_total_cycle_count(self, **backend_kwargs) -> int:
    request = self._get(backend_kwargs)
    return (await self.server.call(self._calls.get_total_cycle_count(request))).value

  async def get_current_step_index(self, **backend_kwargs) -> int:
    request = self._get(backend_kwargs)
    return (await self.server.call(self._calls.get_current_step_index(request))).value

  async def get_total_step_count(self, **backend_kwargs) -> int:
    request = self._get(backend_kwargs)
    return (await self.server.call(self._calls.get_total_step_count(request))).value
