"""Serving a PreciseFlex: one Connect application for every service of one device.

Every service but `PositionsService` is one of the device's classes, each RPC a call of its method
of that name (`generated_handlers.py`). A call that moves the arm, or changes how it moves, waits
for the one before it, and for a carry; one that only asks (`request_...`, `sense_...`) and `halt`
do not wait.

With a resource server, the device's resources are kept there after setup: the device, its base
plate and what it carries, made from the device's own model, or taken up when the server already
holds a device of its name. After every call the carriage, the links and the gripper are recorded
where the arm's model has them.
"""

import asyncio
import hashlib
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext

from pylabrobot.brooks.precise_flex.device import PreciseFlexDevice
from pylabrobot.brooks.precise_flex.driver.features.arm import PreciseFlexArm
from pylabrobot.brooks.precise_flex.driver.features.gripper import PreciseFlexGripper
from pylabrobot.brooks.precise_flex.driver.features.rail import PreciseFlexRail
from pylabrobot.brooks.precise_flex.driver.features.vision import PreciseFlexVision
from pylabrobot.brooks.precise_flex.driver.master import PreciseFlexDriver
from pylabrobot.brooks.precise_flex.server.description import describe, put_in_place
from pylabrobot.brooks.precise_flex.server.errors import to_connect_error
from pylabrobot.brooks.precise_flex.server.generated_handlers import ASGIApp, applications
from pylabrobot.brooks.precise_flex.server.positions import Positions, positions_application
from pylabrobot.brooks.precise_flex.server.v1 import description_pb2 as dpb
from pylabrobot.resources.server.client import ResourceServer
from pylabrobot.resources.server.definitions import definition_from_resource
from pylabrobot.resources.server.memory import asgi_app as resource_server_app
from pylabrobot.resources.server.v1 import server_pb2 as spb
from pylabrobot.resources.server.v1 import types_pb2 as rpb

logger = logging.getLogger(__name__)

# The response header that says which description of the device is current.
REVISION_HEADER = "precise-flex-description-revision"

R = TypeVar("R")
Ctx = RequestContext[Any, Any]

# Calls that do not wait their turn: they only ask, or stop a move under way.
_ASKS = ("request_", "sense_", "read_")
_DO_NOT_WAIT = {("arm", "halt"), ("driver", "nop")}


def _holding_after(
  feature: str, method: str, kwargs: Dict[str, Any], before: Optional[bool]
) -> Optional[bool]:
  """Whether the gripper holds a plate after a call, as far as the call says."""
  if method == "setup" and feature in ("device", "driver"):
    # Homing opens the jaws, so whatever they held is let go.
    return None if kwargs.get("skip_home") else False
  if (feature, method) in (("driver", "home"), ("driver", "home_all")):
    return False
  if feature == "arm" and method.startswith("pick_up_at_"):
    return True
  if feature == "arm" and method.startswith("drop_at_"):
    return False
  if feature == "gripper" and method.startswith("move_to_jaw_position"):
    return None
  if method in ("stop", "disconnect") and feature in ("device", "driver"):
    return None
  return before


class Served:
  """One device, served: each call made on the device, and the description of it kept current.

  Attributes:
    motion: held by every call that moves the arm or changes how it moves, so one runs at a time.
    holding: whether the gripper holds a plate, as far as the server knows; None when it does not.
  """

  def __init__(
    self,
    device: PreciseFlexDevice,
    settings: Optional[dpb.Settings] = None,
    resource_server: Union[str, ResourceServer, None] = None,
    positions_path: Optional[str] = None,
  ):
    self.device = device
    self.settings = settings
    self.resource_server = (
      ResourceServer.connect(resource_server)
      if isinstance(resource_server, str)
      else resource_server
    )
    self.positions = Positions(positions_path)
    self.resources: Optional[dpb.Resources] = None
    self.holding: Optional[bool] = None
    # Whether a setup has finished since the server started, and no stop since.
    self.set_up = False
    self.motion = asyncio.Lock()
    # Calls that keep running when their client has gone, held so they are not collected.
    self.running: Set["asyncio.Task[Any]"] = set()
    self._digest: Optional[bytes] = None
    self.revision = 0

  # -- what a call is made on --

  def driver(self) -> PreciseFlexDriver:
    return self.device.driver

  def arm(self) -> PreciseFlexArm:
    return self.device.arm

  def gripper(self) -> PreciseFlexGripper:
    return self.device.gripper

  def rail(self) -> PreciseFlexRail:
    if self.device.rail is None:
      raise ConnectError(Code.FAILED_PRECONDITION, "the arm has no rail; has setup run?")
    return self.device.rail

  def vision(self) -> PreciseFlexVision:
    if self.device.vision is None:
      raise ConnectError(Code.FAILED_PRECONDITION, "the arm has no vision; has setup run?")
    return self.device.vision

  def require_set_up(self) -> None:
    """
    Raises:
      RuntimeError: If the device has not been set up.
    """
    if not self.set_up:
      raise RuntimeError("the arm is not set up: call setup first")

  # -- its resources --

  async def publish(self) -> None:
    """Keep the device's resources on the resource server: made from its model, or taken up when
    the server holds a device of its name. Does nothing without a resource server, or before the
    arm is modelled."""
    server, device = self.resource_server, self.device
    if server is None or device.arm.resource is None or self.resources is not None:
      return
    found = await server.find_resources(
      spb.ResourceFilter(names=[device.name], categories=["device"])
    )
    body = found[0] if found else await server.create(definition_from_resource(device), device.name)
    parts: List[Tuple[str, Any]] = [
      ("base_plate", device.base_plate),
      ("arm", device.arm.resource),
      ("link_1", device.arm.link_1),
      ("link_2", device.arm.link_2),
      ("gripper", device.gripper.resource),
    ]
    resources = dpb.Resources(device=rpb.ResourceRef(id=body.id))
    for field, part in parts:
      if part is not None:
        handle = await body.get_resource(part.name)
        getattr(resources, field).CopyFrom(rpb.ResourceRef(id=handle.id))
    self.resources = resources
    await self.record()

  async def record(self) -> None:
    """Record the carriage, the links and the gripper where the arm's model has them."""
    if self.resource_server is None or self.resources is None:
      return
    device = self.device
    positions = []
    for field, part in (
      ("arm", device.arm.resource),
      ("link_1", device.arm.link_1),
      ("link_2", device.arm.link_2),
      ("gripper", device.gripper.resource),
    ):
      if part is None or not self.resources.HasField(field) or part.location is None:
        continue
      rotation = part.rotation
      position = spb.DevicePosition(
        resource=getattr(self.resources, field),
        location=rpb.PartialVec3(x=part.location.x, y=part.location.y, z=part.location.z),
        rotation=rpb.RotationChange(
          to=rpb.PartialRotation(x=rotation.x, y=rotation.y, z=rotation.z)
        ),
      )
      if part is device.gripper.resource:
        position.jaw_width = device.gripper.resource.jaw_width
      positions.append(position)
    if positions:
      await self.resource_server.commands.record_device_positions(
        spb.RecordDevicePositionsRequest(positions=positions)
      )

  async def _record_quietly(self) -> None:
    try:
      await self.record()
    except Exception as error:  # noqa: BLE001 - the call's own result is what the client gets
      logger.warning("could not record the arm on the resource server: %s", error)

  # -- making a call --

  def description(self) -> dpb.Description:
    return describe(self.device, self.resources, self.holding)

  def stamp(self, ctx: Ctx, trailer: bool = False) -> None:
    """Say which description is current, moving the revision on when it changed.

    Args:
      trailer: say it in a trailer too, as a long call does when it ends, its headers long sent.
    """
    digest = hashlib.sha256(self.description().SerializeToString(deterministic=True)).digest()
    if digest != self._digest:
      self._digest = digest
      self.revision += 1
    ctx.response_headers[REVISION_HEADER] = str(self.revision)
    if trailer:
      ctx.response_trailers[REVISION_HEADER] = str(self.revision)

  async def _call(
    self, feature: str, method: str, call: Callable[[], Awaitable[R]], kwargs: Dict[str, Any]
  ) -> R:
    if feature in ("device", "driver") and method == "setup":
      self.set_up = False
    result = await call()
    self.holding = _holding_after(feature, method, kwargs, self.holding)
    if feature in ("device", "driver"):
      if method == "setup":
        self.set_up = True
        put_in_place(self.device, self.settings)
        await self.publish()
      elif method in ("stop", "disconnect"):
        self.set_up = False
    return result

  async def run(
    self,
    ctx: Ctx,
    feature: str,
    method: str,
    call: Callable[[], Awaitable[R]],
    kwargs: Dict[str, Any],
  ) -> R:
    """Make a call, raising what it raised as a Connect error, and say which description is
    current. After a setup, the settings are put in place again and the resources kept."""
    try:
      if method.startswith(_ASKS) or (feature, method) in _DO_NOT_WAIT:
        return await self._call(feature, method, call, kwargs)
      async with self.motion:
        return await self._call(feature, method, call, kwargs)
    except ConnectError:
      raise
    except Exception as error:
      raise to_connect_error(error) from error
    finally:
      await self._record_quietly()
      self.stamp(ctx)

  async def describe(self, ctx: Ctx) -> dpb.Description:
    self.stamp(ctx)
    return self.description()


def precise_flex_server_app(
  device: PreciseFlexDevice,
  settings: Optional[dpb.Settings] = None,
  resource_server: Union[str, ResourceServer, None] = None,
  positions_path: Optional[str] = None,
) -> ASGIApp:
  """One ASGI application serving every PreciseFlex service for a device.

  Args:
    device: the device to serve.
    settings: the defaults the device's features use where a call names none, put in place now
      and after every setup. Those not given keep the defaults in the code.
    resource_server: the resource server to keep the device's resources in, or its URL. Without
      one, its parts are not on any.
    positions_path: the JSON file the taught positions are kept in. Without one they are kept only
      while the server runs.

  Raises:
    ValueError: If the positions file holds a position it cannot use.
  """
  put_in_place(device, settings)
  served = Served(device, settings, resource_server, positions_path)
  apps = applications(served)
  apps.update(positions_application(served))

  async def app(scope: Dict[str, Any], receive: Any, send: Any) -> None:
    path = scope.get("path", "") if scope.get("type") == "http" else ""
    for prefix, application in apps.items():
      if path.startswith(prefix):
        await application(scope, receive, send)
        return
    if scope.get("type") == "http":
      await send({"type": "http.response.start", "status": 404, "headers": []})
      await send({"type": "http.response.body", "body": b""})

  return app


async def serve(
  device: PreciseFlexDevice,
  host: str = "127.0.0.1",
  port: int = 8090,
  settings: Optional[dpb.Settings] = None,
  resource_server: Union[str, ResourceServer, None] = None,
  resource_port: Optional[int] = None,
  positions_path: Optional[str] = None,
) -> None:
  """Serve a device until cancelled. Needs uvicorn, the `resource-server` extra.

  Args:
    device: the device to serve.
    host: the address to listen on.
    port: the port the PreciseFlex server listens on.
    settings: as `precise_flex_server_app` takes them.
    resource_server: as `precise_flex_server_app` takes it.
    resource_port: a port to serve the resource server on as well, when it is held in this
      process; not served when not given.
    positions_path: as `precise_flex_server_app` takes it.

  Raises:
    ValueError: If given a `resource_port` for a resource server that is not held in this process.
  """
  import uvicorn

  if isinstance(resource_server, str):
    resource_server = ResourceServer.connect(resource_server)
  apps: List[Tuple[ASGIApp, int]] = [
    (precise_flex_server_app(device, settings, resource_server, positions_path), port)
  ]
  if resource_port is not None:
    if resource_server is None or resource_server.memory is None:
      raise ValueError("only a resource server held in this process can be served with the arm")
    apps.append((resource_server_app(resource_server.memory), resource_port))
  await asyncio.gather(
    *(uvicorn.Server(uvicorn.Config(app, host=host, port=p)).serve() for app, p in apps)
  )


__all__ = ["REVISION_HEADER", "Served", "precise_flex_server_app", "serve"]
