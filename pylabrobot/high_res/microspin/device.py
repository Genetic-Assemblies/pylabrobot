"""The MicroSpin as resources on a resource server: its body, its rotor, and the two buckets.

`MicroSpin` drives the device through a `MicroSpinDriver` and keeps the model in step with it: after
each move it reads `status` and records how the rotor is turned and whether the door is open. The
buckets are plate holders, so a plate put in one by a robot, or by hand, is a plate on the server
like any other.

The body's size is the spec sheet's. Where the rotor and buckets sit inside it has not been
measured: the rotor is centered in the body and each bucket stands `BUCKET_RADIUS` from its axis,
the device's own `CENTRIFUGE_BUCKET_RADIUS_M`. Their locations have the right shape, not taught
positions; a robot reaches a bucket at a position taught for it.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

from pylabrobot.resources.coordinate import Coordinate
from pylabrobot.resources.server import PlateHolder, Resource, ResourceServer, build
from pylabrobot.resources.server.v1 import server_pb2 as spb
from pylabrobot.resources.server.v1 import types_pb2 as pb

from .driver import Bucket, CommandStatus, MicroSpinDriver, MicroSpinStatus
from .errors import ErrorEntry, MicroSpinTimeoutError
from .simulator import MicroSpinSimulator

if TYPE_CHECKING:
  from .server.client import MicroSpinServer

logger = logging.getLogger(__name__)

# The spec sheet's dimensions: 15 in wide, 16 in deep, 15 in tall, in mm.
BODY_SIZE = Coordinate(381.0, 406.4, 381.0)
# How far each bucket's center stands from the rotor's axis, in mm.
BUCKET_RADIUS = 120.0
# A bucket's footprint: one SBS plate. Its height is the plate holder's, none of its own.
BUCKET_SIZE = Coordinate(127.76, 85.48, 0.0)
ROTOR_SIZE = Coordinate(
  2 * (BUCKET_RADIUS + BUCKET_SIZE.y), 2 * (BUCKET_RADIUS + BUCKET_SIZE.y), 10.0
)
# The spindle position, in counts, with each bucket at the door, as a device reported it.
SPINDLE_AT_DOOR: Dict[int, int] = {1: 8186, 2: 4087}
# A door position above this, in counts, is open: a device read about 19240 open, -451 closed.
DOOR_OPEN_ABOVE = 9000
# How far from a bucket's door angle the rotor may be, in degrees, and that bucket count as at the
# door.
AT_DOOR_TOLERANCE = 10.0

_CATEGORY = "centrifuge"


def rotor_angle(spindle_position: int, counts_per_turn: int) -> float:
  """The rotor's angle about z, in degrees from 0 to 360, with 0 putting bucket 1 at the door."""
  turned = (spindle_position - SPINDLE_AT_DOOR[1]) % counts_per_turn
  return turned / counts_per_turn * 360.0


def _bucket_definition(name: str, bucket: Bucket) -> pb.ResourceDefinition:
  """A bucket, on the rotor: bucket 1 toward the door at angle 0, bucket 2 across from it."""
  center = Coordinate(ROTOR_SIZE.x / 2, ROTOR_SIZE.y / 2, ROTOR_SIZE.z)
  offset = -BUCKET_RADIUS if bucket == 1 else BUCKET_RADIUS
  location = Coordinate(
    center.x - BUCKET_SIZE.x / 2, center.y + offset - BUCKET_SIZE.y / 2, center.z
  )
  return build.plate_holder(
    name, BUCKET_SIZE, location=location, category="centrifuge_bucket", pedestal_size_z=0.0
  )


def body_definition(name: str) -> pb.ResourceDefinition:
  """The body, with the rotor in it and the buckets on the rotor."""
  rotor = build.resource(
    f"{name}_rotor",
    ROTOR_SIZE,
    location=Coordinate(
      (BODY_SIZE.x - ROTOR_SIZE.x) / 2, (BODY_SIZE.y - ROTOR_SIZE.y) / 2, BODY_SIZE.z / 3
    ),
    category="centrifuge_rotor",
    children=[
      _bucket_definition(f"{name}_bucket_1", 1),
      _bucket_definition(f"{name}_bucket_2", 2),
    ],
  )
  return build.resource(
    name,
    BODY_SIZE,
    category=_CATEGORY,
    model="HighRes Biosolutions MicroSpin",
    metadata={"door": "closed"},
    children=[rotor],
  )


class MicroSpin:
  """A HighRes Biosolutions MicroSpin: the driver, and the device's resources on a server.

  Given `microspin_server`, a MicroSpin server or its URL, it is the device that server serves
  instead, driven over the network with the same methods; see `ServedMicroSpin`.

  Attributes:
    name: what its body is called on the server; its rotor and buckets are named after it.
    resource_server: where its resources are.
    body: its body, once `setup` or `create_resources` has run.
    rotor: its rotor.
    buckets: its buckets, by number.
  """

  def __new__(cls, *args: Any, microspin_server: Any = None, **kwargs: Any) -> "MicroSpin":
    if microspin_server is not None and cls is MicroSpin:
      from .server.client import ServedMicroSpin

      return super().__new__(ServedMicroSpin)
    return super().__new__(cls)

  def __init__(
    self,
    name: str = "microspin",
    host: Optional[str] = None,
    port: int = MicroSpinDriver.DEFAULT_PORT,
    simulation: bool = False,
    resource_server: Optional[Union[str, ResourceServer]] = None,
    driver: Optional[MicroSpinDriver] = None,
    microspin_server: Union[str, "MicroSpinServer", None] = None,
  ) -> None:
    """
    Args:
      name: what to call its body on the server.
      host: the device's address; not needed for a simulated device or a given driver.
      port: its remote-control port.
      simulation: drive a `MicroSpinSimulator` in place of a device.
      resource_server: the server to keep its resources on, or its URL; one held in this process
        when not given.
      driver: the driver to use, in place of one made from the arguments above.
      microspin_server: the MicroSpin server to drive the device through, or its URL; see
        `ServedMicroSpin`.
    """
    if driver is None:
      if simulation:
        driver = MicroSpinSimulator()
      elif host is None:
        raise ValueError("a MicroSpin needs a host, simulation=True, or a driver")
      else:
        driver = MicroSpinDriver(host=host, port=port)
    if isinstance(resource_server, str):
      resource_server = ResourceServer.connect(resource_server)
    self.name = name
    self._driver = driver
    self.resource_server = resource_server or ResourceServer.local()
    self.body: Optional[Resource] = None
    self.rotor: Optional[Resource] = None
    self.buckets: Dict[int, PlateHolder] = {}

  @property
  def driver(self) -> MicroSpinDriver:
    """What talks to the device."""
    return self._driver

  # -- the device's resources -------------------------------------------------------------------

  async def _take_up(self, body: Resource) -> None:
    """Hold the parts of a body already on the server."""
    rotor = await body.get_resource(f"{self.name}_rotor")
    buckets: Dict[int, PlateHolder] = {}
    for bucket in (1, 2):
      found = await rotor.get_resource(f"{self.name}_bucket_{bucket}")
      if not isinstance(found, PlateHolder):
        raise ValueError(f"'{found.name}' on the server is not a plate holder")
      buckets[bucket] = found
    self.body, self.rotor, self.buckets = body, rotor, buckets

  async def create_resources(self) -> None:
    """Make the body, rotor and buckets on the server, or find them there under this name.

    `setup` calls this. Call it before setup to hang the body somewhere or put plates in it.
    Repeatable: a body that exists is taken up, not made again.
    """
    if self.body is not None:
      return
    found = await self.resource_server.find_resources(
      spb.ResourceFilter(names=[self.name], categories=[_CATEGORY])
    )
    if found:
      await self._take_up(found[0])
    else:
      await self._take_up(await self.resource_server.create(body_definition(self.name), self.name))

  def _require_resources(self) -> Resource:
    if self.rotor is None or self.body is None:
      raise RuntimeError("the MicroSpin has no resources yet; call setup() or create_resources()")
    return self.rotor

  async def _record(self, status: MicroSpinStatus) -> None:
    """Record how the rotor is turned and whether the door is open, as `status` reports."""
    rotor = self._require_resources()
    assert self.body is not None
    angle = rotor_angle(status.spindle_position, self.driver.SPINDLE_COUNTS_PER_TURN)
    pivot = Coordinate(ROTOR_SIZE.x / 2, ROTOR_SIZE.y / 2, 0)
    turned = pb.RotationChange(to=pb.PartialRotation(z=angle), pivot=build.vec3(pivot))
    await self.resource_server.commands.record_device_positions(
      spb.RecordDevicePositionsRequest(
        positions=[spb.DevicePosition(resource=pb.ResourceRef(id=rotor.id), rotation=turned)]
      )
    )
    door = "open" if status.door_position > DOOR_OPEN_ABOVE else "closed"
    await self.body.set_metadata({"door": door})

  async def _record_where_it_stopped(self) -> None:
    """Read `status` and record it, unless the abort latch leaves `status` unsafe to send."""
    if self.driver.abort_latched:
      return
    await self._record(await self.driver.request_status())

  async def _after_failed_move(self, error: BaseException) -> None:
    """Record where a move that raised `error` left the device, without hiding `error`.

    A move that timed out is still going on the device, and `status` would wait behind it, so
    nothing is recorded; the next move records.
    """
    if isinstance(error, MicroSpinTimeoutError):
      return
    try:
      await self._record_where_it_stopped()
    except Exception as recording:
      logger.warning("[microspin] could not record where the device stopped: %s", recording)

  # -- lifecycle ---------------------------------------------------------------------------------

  async def setup(self) -> None:
    """Connect to the device, make or find its resources, and record where it is if homed."""
    await self.driver.setup()
    await self.create_resources()
    if await self.driver.request_homed():
      await self._record(await self.driver.request_status())

  async def stop(self) -> None:
    """Close the connections to the device. Its resources stay on the server."""
    await self.driver.stop()

  # -- what the device reports ---------------------------------------------------------------------

  async def request_version(self) -> Dict[str, str]:
    """See `MicroSpinDriver.request_version`."""
    return await self.driver.request_version()

  async def request_homed(self) -> bool:
    """See `MicroSpinDriver.request_homed`."""
    return await self.driver.request_homed()

  async def request_status(self, timeout: Optional[float] = None) -> MicroSpinStatus:
    """See `MicroSpinDriver.request_status`."""
    return await self.driver.request_status(timeout=timeout)

  async def request_errors(self, count: int = 10) -> List[ErrorEntry]:
    """See `MicroSpinDriver.request_errors`."""
    return await self.driver.request_errors(count)

  async def request_command_status(self, command_id: int) -> CommandStatus:
    """See `MicroSpinDriver.request_command_status`."""
    return await self.driver.request_command_status(command_id)

  async def request_spindle_velocity(self) -> float:
    """See `MicroSpinDriver.request_spindle_velocity`."""
    return await self.driver.request_spindle_velocity()

  async def wait_for_spindle_stopped(
    self, timeout: Optional[float] = None, poll_interval: Optional[float] = None
  ) -> None:
    """See `MicroSpinDriver.wait_for_spindle_stopped`."""
    await self.driver.wait_for_spindle_stopped(timeout=timeout, poll_interval=poll_interval)

  # -- what the model says -------------------------------------------------------------------------

  async def get_door(self) -> Literal["open", "closed"]:
    """Whether the door is open, as last recorded."""
    self._require_resources()
    assert self.body is not None
    return "open" if (await self.body.get_metadata()).get("door") == "open" else "closed"

  async def get_bucket_at_door(self) -> Optional[PlateHolder]:
    """The bucket at the open door, as last recorded, or None when the door is closed or the rotor
    is between buckets."""
    rotor = self._require_resources()
    if await self.get_door() != "open":
      return None
    angle = (await rotor.get_rotation()).z % 360
    for bucket, door_angle in ((1, 0.0), (2, 180.0)):
      if min(abs(angle - door_angle), 360 - abs(angle - door_angle)) <= AT_DOOR_TOLERANCE:
        return self.buckets[bucket]
    return None

  async def _require_balanced(self) -> None:
    """Refuse a spin with a plate in one bucket and none in the other."""
    self._require_resources()
    held = [await self.buckets[bucket].get_resource_held() for bucket in (1, 2)]
    if (held[0] is None) != (held[1] is None):
      loaded = 1 if held[0] is not None else 2
      raise ValueError(
        f"bucket {loaded} holds a plate and bucket {3 - loaded} none; balance the rotor first"
      )

  # -- motion --------------------------------------------------------------------------------------

  async def home(self) -> None:
    """Home the door and spindle, and record where they are."""
    try:
      await self.driver.home()
    except BaseException as error:
      await self._after_failed_move(error)
      raise
    await self._record_where_it_stopped()

  async def present_bucket(self, bucket: Bucket) -> None:
    """Open the door with `bucket` at it, and record the rotor and door."""
    try:
      await self.driver.present_bucket(bucket)
    except BaseException as error:
      await self._after_failed_move(error)
      raise
    await self._record_where_it_stopped()

  async def spin(
    self,
    g: float,
    duration: float,
    acceleration: Optional[float] = None,
    deceleration: Optional[float] = None,
    timeout: Optional[float] = None,
  ) -> None:
    """Spin, as `MicroSpinDriver.spin`, after checking the rotor is balanced.

    Raises:
      ValueError: One bucket holds a plate and the other none; nothing is sent.
    """
    await self._require_balanced()
    try:
      await self.driver.spin(
        g, duration, acceleration=acceleration, deceleration=deceleration, timeout=timeout
      )
    except BaseException as error:
      await self._after_failed_move(error)
      raise
    await self._record_where_it_stopped()

  async def abort(self) -> None:
    """Stop whatever is moving; see `MicroSpinDriver.abort`."""
    await self.driver.abort()

  async def clear_abort(self) -> None:
    """Release the abort latch; see `MicroSpinDriver.clear_abort`."""
    await self.driver.clear_abort()

  async def reset(self, timeout: Optional[float] = None) -> MicroSpinStatus:
    """Abort, wait for the rotor to stop, release the latch, and record where it is."""
    status = await self.driver.reset(timeout=timeout)
    await self._record(status)
    return status
