"""A PreciseFlex served elsewhere, driven as one in this process is.

The device, its driver and its features are the same classes, every public coroutine a call to
the PreciseFlex server (`generated_remote.py`); the deprecated aliases are inherited as they are,
and call those. What their attributes hold - the configuration, the settings, and the resources
the arm's parts are - is kept from the server's description of the device, taken up again whenever
the server says it changed. Resources are handles on the resource server both ends use. Settings
are the server's: a client reads them and cannot set them.

`PreciseFlexServer` also speaks `PositionsService`: `list_positions`, `teach`, `forget`, `carry`
and `get_holding`.
"""

from __future__ import annotations

import asyncio
from typing import (
  Any,
  AsyncIterator,
  Awaitable,
  Callable,
  Dict,
  List,
  Mapping,
  Optional,
  Tuple,
  TypeVar,
  Union,
)

from connectrpc.client import ResponseMetadata
from connectrpc.errors import ConnectError
from pyqwest import Client

from pylabrobot.brooks.precise_flex.device import PreciseFlexDevice
from pylabrobot.brooks.precise_flex.driver.features.gripper import PreciseFlexGripper
from pylabrobot.brooks.precise_flex.kinematics import JointState
from pylabrobot.brooks.precise_flex.resource_model.pf400_manipulator import BASE_PLATE_SIZE
from pylabrobot.brooks.precise_flex.server import wire
from pylabrobot.brooks.precise_flex.server.description import ARM_SETTINGS, GRIPPER_SETTINGS
from pylabrobot.brooks.precise_flex.server.errors import from_connect_error
from pylabrobot.brooks.precise_flex.server.generated_remote import (
  PreciseFlexClients,
  _RemoteArmCalls,
  _RemoteDriverCalls,
  _RemoteGripperCalls,
  _RemotePreciseFlexCalls,
  _RemoteRailCalls,
  _RemoteVisionCalls,
)
from pylabrobot.brooks.precise_flex.server.serve import REVISION_HEADER, precise_flex_server_app
from pylabrobot.brooks.precise_flex.server.v1 import description_pb2 as dpb
from pylabrobot.brooks.precise_flex.server.v1 import positions_pb2 as ppb
from pylabrobot.brooks.precise_flex.server.v1 import types_pb2 as tpb
from pylabrobot.brooks.precise_flex.server.v1.positions_connect import PositionsServiceClient
from pylabrobot.resources.resource import Resource
from pylabrobot.resources.server.asgi_transport import ASGITransport
from pylabrobot.resources.server.client import ResourceServer, _Headers

# The address a PreciseFlex server held in this process is spoken to at; never dialled.
_IN_PROCESS = "http://precise-flex.in-process"

SETTING_MESSAGE = (
  "{} is set where the PreciseFlex is served, in the PreciseFlex server's settings file, not on "
  "a client"
)

R = TypeVar("R")


class PreciseFlexServer:
  """A PreciseFlex server: where a device is served, and how its calls get there.

  `connect` reaches one served elsewhere; `local` serves a device in this process, without a
  socket, as tests do.
  """

  def __init__(
    self, address: str, http: Optional[Client] = None, headers: Optional[Mapping[str, str]] = None
  ):
    interceptors: List[_Headers] = [_Headers(headers)] if headers else []
    self.clients = PreciseFlexClients(address, http, interceptors)
    self.positions = PositionsServiceClient(address, http_client=http, interceptors=interceptors)
    self.revision: Optional[str] = None
    self.device: Optional[RemotePreciseFlexDevice] = None
    self._describing: Optional[asyncio.Lock] = None

  @classmethod
  def connect(cls, url: str, headers: Optional[Mapping[str, str]] = None) -> PreciseFlexServer:
    """A PreciseFlex server at `url`, "http://127.0.0.1:8090" say.

    Args:
      headers: sent with every call: the credentials the server asks for.
    """
    return cls(url, Client(), headers=headers)

  @classmethod
  def local(
    cls,
    device: PreciseFlexDevice,
    settings: Optional[dpb.Settings] = None,
    resource_server: Optional[ResourceServer] = None,
    positions_path: Optional[str] = None,
  ) -> PreciseFlexServer:
    """A device served in this process, spoken to over Connect without a socket.

    Args: as `precise_flex_server_app` takes them.
    """
    app = precise_flex_server_app(device, settings, resource_server, positions_path)
    return cls(_IN_PROCESS, Client(transport=ASGITransport(app)))

  async def close(self) -> None:
    await self.clients.close()
    await self.positions.close()

  def _raised(self, error: ConnectError) -> BaseException:
    """What the served device raised, from the Connect error it came as."""
    return from_connect_error(error) or error

  async def call(self, response: Awaitable[R]) -> R:
    """A call's response, raising what the served device raised as it raised it; the device's
    description taken up again when the server says it changed."""
    with ResponseMetadata() as meta:
      try:
        result = await response
      except ConnectError as error:
        raised = self._raised(error)
        await self._take_up(meta.headers.get(REVISION_HEADER))
        raise raised from None
    await self._take_up(meta.headers.get(REVISION_HEADER))
    return result

  async def stream(
    self, progress: AsyncIterator[tpb.Progress], what: str, each: Callable[[tpb.Progress], None]
  ) -> None:
    """Read a long call's progress until the server says it is done.

    Raises:
      ConnectionError: If the stream ends before the call is done.
    """
    done = False
    with ResponseMetadata() as meta:
      try:
        async for step in progress:
          each(step)
          done = done or step.done
      except ConnectError as error:
        raise self._raised(error) from None
      finally:
        revision = meta.trailers.get(REVISION_HEADER) or meta.headers.get(REVISION_HEADER)
    await self._take_up(revision)
    if not done:
      raise ConnectionError(f"the PreciseFlex server stopped before {what} was done")

  async def _take_up(self, revision: Optional[str]) -> None:
    """Ask for the device's description again when the server says it changed."""
    if revision is None or revision == self.revision or self.device is None:
      return
    await self.refresh()

  async def refresh(self) -> None:
    """Take up the device's description as the server has it now."""
    from pylabrobot.brooks.precise_flex.server.description import apply

    if self._describing is None:
      self._describing = asyncio.Lock()
    async with self._describing:
      with ResponseMetadata() as meta:
        try:
          description = await self.clients.precise_flex.describe(dpb.DescribeRequest())
        except ConnectError as error:
          raise self._raised(error) from None
      if self.device is not None:
        await apply(self.device, description)
      self.revision = meta.headers.get(REVISION_HEADER)

  # -- PositionsService --

  async def list_positions(self) -> Dict[str, JointState]:
    """The positions the server has been taught, each its joint state, by name."""
    response = await self.call(self.positions.list(ppb.ListRequest()))
    return {p.name: wire.joint_state_from(p.joint_state) for p in response.positions}

  async def teach(self, name: str, joint_state: Optional[JointState] = None) -> JointState:
    """Keep a joint state as a position, by name: the one given, or where the arm is now.

    Returns:
      What the position keeps.
    """
    request = ppb.TeachRequest(name=name)
    if joint_state is not None:
      request.joint_state.CopyFrom(wire.joint_state_to(joint_state))
    response = await self.call(self.positions.teach(request))
    return wire.joint_state_from(response.position.joint_state)

  async def forget(self, name: str) -> None:
    await self.call(self.positions.forget(ppb.ForgetRequest(name=name)))

  async def carry(
    self,
    from_position: str,
    to_position: str,
    width: float,
    height: float,
    plate_height: float,
    progress: Optional[Callable[[tpb.Progress], None]] = None,
  ) -> None:
    """Pick a plate up at one position and leave it at another (`v1/positions.proto`).

    Args:
      width: across the plate where the jaws close, in mm.
      height: from the plate's bottom to where the jaws close, in mm.
      plate_height: the plate's height, in mm: how far above a position to approach and leave it.
      progress: called with each `Progress` the server sends.
    """
    request = ppb.CarryRequest(
      from_position=from_position,
      to_position=to_position,
      grip=ppb.Grip(width=width, height=height, plate_height=plate_height),
    )
    await self.stream(self.positions.carry(request), "the carry", progress or (lambda _: None))

  async def get_holding(self) -> Optional[bool]:
    """Whether the gripper holds a plate; None when the server does not know."""
    response = await self.call(self.positions.get_holding(ppb.GetHoldingRequest()))
    return response.holding if response.HasField("holding") else None


def _setting(name: str, feature: str) -> property:
  """An attribute a feature takes from the server's settings: read, never set."""

  def get(self: Any) -> Any:
    described: Optional[dpb.Description] = self._served_driver.described
    if described is None:
      return None
    held = getattr(described.settings, feature)
    if name == "parking_position":
      return wire.joint_state_from(held.parking_position) if held.HasField(name) else None
    return getattr(held, name)

  def refuse(self: Any, value: Any) -> None:
    raise AttributeError(SETTING_MESSAGE.format(name))

  return property(get, refuse, doc=f"`{name}`, as the server's settings have it.")


class RemotePreciseFlexArm(_RemoteArmCalls):
  """A PreciseFlex arm served elsewhere. Its settings and resources are the server's."""

  def __init__(self, driver: RemotePreciseFlexDriver):
    # Not the arm's own: what it holds is the server's.
    self._driver = driver
    self._served_driver = driver
    self.configuration = None
    self.resource = None
    self.link_1 = None
    self.link_2 = None

  @property
  def _precise_flex_server(self) -> PreciseFlexServer:  # type: ignore[override]
    return self._served_driver._precise_flex_server

  def update_joint_state(self, joints: JointState) -> None:
    raise RuntimeError("a served arm's model is the server's, kept as the arm moves")


for _name in ("parking_position", *ARM_SETTINGS):
  setattr(RemotePreciseFlexArm, _name, _setting(_name, "arm"))


class RemotePreciseFlexGripper(_RemoteGripperCalls):
  """A PreciseFlex gripper served elsewhere. Its calibration and settings are the server's."""

  def __init__(self, driver: RemotePreciseFlexDriver):
    self._driver = driver
    self._served_driver = driver
    self.configuration = None
    self.resource = None
    self._anchor_width_mm = PreciseFlexGripper.jaw_width_range[0]

  @property
  def _precise_flex_server(self) -> PreciseFlexServer:  # type: ignore[override]
    return self._served_driver._precise_flex_server

  @property  # type: ignore[override]
  def closed_gripper_position(self) -> float:
    described = self._served_driver.described
    return 0.0 if described is None else described.gripper.closed_gripper_position

  @closed_gripper_position.setter
  def closed_gripper_position(self, value: float) -> None:
    raise AttributeError("closed_gripper_position is the served gripper's calibration")

  @property  # type: ignore[override]
  def jaw_width_range(self) -> Tuple[float, float]:
    described = self._served_driver.described
    if described is None:
      return PreciseFlexGripper.jaw_width_range
    return (described.gripper.jaw_width_range.low, described.gripper.jaw_width_range.high)

  @jaw_width_range.setter
  def jaw_width_range(self, value: Tuple[float, float]) -> None:
    raise AttributeError("jaw_width_range is the served gripper's, from its configuration")

  @property
  def _is_dual_gripper(self) -> bool:  # type: ignore[override]
    described = self._served_driver.described
    return described is not None and described.gripper.is_dual_gripper

  def update_width(self, width: float) -> None:
    raise RuntimeError("a served gripper's model is the server's, kept as the jaws move")


for _name in GRIPPER_SETTINGS:
  setattr(RemotePreciseFlexGripper, _name, _setting(_name, "gripper"))


class RemotePreciseFlexRail(_RemoteRailCalls):
  """A PreciseFlex rail served elsewhere."""

  def __init__(self, driver: RemotePreciseFlexDriver):
    self._driver = driver
    self._served_driver = driver
    self.configuration = None

  @property
  def _precise_flex_server(self) -> PreciseFlexServer:  # type: ignore[override]
    return self._served_driver._precise_flex_server


class RemotePreciseFlexVision(_RemoteVisionCalls):
  """A PreciseFlex vision feature served elsewhere."""

  def __init__(self, driver: RemotePreciseFlexDriver):
    from pylabrobot.brooks.precise_flex.driver.features.vision import VisionConfiguration

    self.driver = driver
    self._served_driver = driver
    self.configuration = VisionConfiguration()

  @property
  def _precise_flex_server(self) -> PreciseFlexServer:  # type: ignore[override]
    return self._served_driver._precise_flex_server


class RemotePreciseFlexDriver(_RemoteDriverCalls):
  """A PreciseFlex driver served elsewhere. What it holds is the server's driver's, as last
  described."""

  def __init__(self, precise_flex_server: PreciseFlexServer):
    # Not the driver's own: there is no link here to open.
    self._precise_flex_server = precise_flex_server
    self.described: Optional[dpb.Description] = None
    self.io = None  # type: ignore[assignment]
    self.declared_configuration_json = None
    self.declared: Dict[str, Any] = {}
    self.base_plate: Optional[Any] = None  # type: ignore[assignment]
    self._configuration = None
    self._connected = False
    self.arm: RemotePreciseFlexArm = RemotePreciseFlexArm(self)  # type: ignore[assignment]
    self.gripper: RemotePreciseFlexGripper = RemotePreciseFlexGripper(self)  # type: ignore[assignment]
    self.rail = None
    self.vision = None

  @property
  def vision_server_connected(self) -> bool:
    return self.described is not None and self.described.vision_server_connected

  def _controller_reference(self) -> Dict[str, object]:
    return {"name": "precise_flex", "type": type(self).__name__, "served": True}


class RemotePreciseFlexDevice(_RemotePreciseFlexCalls):
  """A PreciseFlex served elsewhere: the arm, its base plate and what it carries are the server's
  device's. Its name and size are the server's, once it has described the device.

  Attributes:
    body: the device on the resource server, when there is one.
    base_plate: its base plate there.
  """

  def __init__(
    self,
    precise_flex_server: PreciseFlexServer,
    resource_server: Optional[ResourceServer],
    name: str,
    model: str,
  ):
    # Not the device's own: the server's device holds what it is, and its tree is on the resource
    # server.
    Resource.__init__(
      self,
      name=name,
      size_x=BASE_PLATE_SIZE[0],
      size_y=BASE_PLATE_SIZE[1],
      size_z=BASE_PLATE_SIZE[2],
      category="device",
      model=model,
    )
    self._precise_flex_server = precise_flex_server
    self.resource_server = resource_server
    self.body: Optional[Any] = None
    self.base_plate = None  # type: ignore[assignment]
    self.driver: RemotePreciseFlexDriver = RemotePreciseFlexDriver(precise_flex_server)  # type: ignore[assignment]
    precise_flex_server.device = self


def remote_device(
  precise_flex_server: Union[str, PreciseFlexServer],
  resource_server: Union[str, ResourceServer, None],
  name: str,
  model: str,
) -> RemotePreciseFlexDevice:
  """A device a PreciseFlex server serves.

  Args:
    precise_flex_server: the server, or its URL.
    resource_server: the resource server the PreciseFlex server keeps the device's resources in,
      or its URL; without one, the device's resources are not reachable here.
    name: what to call it until the server has described it.
    model: the device the caller asked for.
  """
  if isinstance(precise_flex_server, str):
    precise_flex_server = PreciseFlexServer.connect(precise_flex_server)
  if isinstance(resource_server, str):
    resource_server = ResourceServer.connect(resource_server)
  return RemotePreciseFlexDevice(precise_flex_server, resource_server, name, model)


__all__ = [
  "PreciseFlexServer",
  "RemotePreciseFlexArm",
  "RemotePreciseFlexDevice",
  "RemotePreciseFlexDriver",
  "RemotePreciseFlexGripper",
  "RemotePreciseFlexRail",
  "RemotePreciseFlexVision",
  "remote_device",
]
