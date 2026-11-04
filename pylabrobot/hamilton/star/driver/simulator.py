"""A STAR that answers without being plugged in.

Each feature has a small subclass here that overrides the handful of methods which would
otherwise talk to a device, returning what one would have said. `STARSimulationDriver` swaps
those in, so everything above them - discovery, the initialization order, the configuration each
feature resolves - runs exactly as it does against hardware.

Nothing reaches the wire. `send_command` raises, which is how a command that has not been
simulated makes itself known: override the method that sends it, on the feature that owns it.
"""

import asyncio
import copy
import dataclasses
import datetime
import logging
import math
from typing import Any, Dict, List, Literal, Optional, Tuple, cast

from pylabrobot.hamilton.protocol.text.framing import (
  assemble_channel_command,
  parse_firmware_version_date,
)
from pylabrobot.hamilton.star import resource_model
from pylabrobot.hamilton.star.driver import model
from pylabrobot.hamilton.star.driver.configuration import DeviceConfiguration
from pylabrobot.hamilton.star.driver.errors import check_fw_string_error
from pylabrobot.hamilton.star.driver.features.autoload import (
  AUTOLOAD_TYPES,
  Autoload,
  AutoloadConfiguration,
)
from pylabrobot.hamilton.star.driver.features.core_grippers import CoreGrippers
from pylabrobot.hamilton.star.driver.features.cover import CoverPosition, FrontCover
from pylabrobot.hamilton.star.driver.features.head import (
  HEAD_REFERENCE_SHAFT,
  Head,
  HeadConfiguration,
)
from pylabrobot.hamilton.star.driver.features.head96 import Head96, Head96Configuration
from pylabrobot.hamilton.star.driver.features.head384 import Head384, Head384Configuration
from pylabrobot.hamilton.star.driver.features.iswap import (
  iSWAP,
  iSWAPConfiguration,
  iSWAPElbowPositions,
  iSWAPGripperPositions,
  iSWAPWristPositions,
  iSWAPYPositions,
  iSWAPZPositions,
)
from pylabrobot.hamilton.star.driver.features.pipettes import (
  PipetteConfiguration,
  Pipettes,
  PipettesConfiguration,
)
from pylabrobot.hamilton.star.driver.features.x_arm import XArm
from pylabrobot.hamilton.star.driver.master import STARDriver
from pylabrobot.io.io import IOBase
from pylabrobot.io.validation_utils import LOG_LEVEL_IO
from pylabrobot.resources.coordinate import Coordinate
from pylabrobot.resources.hamilton.tip_creators import TipDropMethod, TipPickupMethod
from pylabrobot.resources.server import handles
from pylabrobot.resources.server.errors import ServerError
from pylabrobot.resources.server.tree import to_coordinate
from pylabrobot.resources.server.v1 import server_pb2 as spb
from pylabrobot.resources.server.v1 import types_pb2 as pb

logger = logging.getLogger(__name__)


# What stands where a transport's identity would be in the log, so simulated and recorded runs read
# the same way.
SIMULATED_LINK = "[simulation]"

# Where its two undriven drives report themselves, in mm. Where they actually are is not modelled:
# each answers from its zero. X is not among them - it answers from the deck.
SIMULATED_AUTOLOAD_Y_POSITION = 0.0
SIMULATED_AUTOLOAD_Z_POSITION = 0.0

# The two diagnostic reads that exist to show what a real unit holds. A simulated one holds nothing,
# and says so rather than inventing a block for a caller to read meaning into.
SIMULATED_AUTOLOAD_ADJUSTMENT_VALUES = "[simulation] no adjustment values"
SIMULATED_AUTOLOAD_PARAMETER_VALUE = "[simulation]"

# Whether the front cover is shut. A simulated device is not being reached into.
SIMULATED_COVER_POSITION: CoverPosition = "closed"

# The three inputs on the cover connector: the cover input, and two whose meaning is not known.
SIMULATED_COVER_INPUTS = (True, False, False)

# What a channel's drive holds after a power cycle, as the device read.
SIMULATED_CHANNEL_DRIVE_PARAMETERS = {"zv": 12_000, "zr": 75, "yv": 6_000, "yr": 4}

# What its scanner reads. A simulated deck holds no carriers, so nothing.
SIMULATED_BARCODE: Optional[str] = None


class _UnusedTransport(IOBase):
  """Stands where the transport would be. Nothing should reach it."""

  async def setup(self, *args, **kwargs):
    pass

  async def stop(self):
    pass

  async def write(self, data: bytes, *args, **kwargs):
    raise RuntimeError(f"the simulator tried to write to a transport: {data!r}")

  async def read(self, *args, **kwargs) -> bytes:
    raise RuntimeError("the simulator tried to read from a transport")


class _Simulated:
  """Reaches the device behind a feature, which for a simulated one is the simulator."""

  _driver: STARDriver

  @property
  def device(self) -> "STARSimulationDriver":
    return cast("STARSimulationDriver", self._driver)

  async def recorded(self, module: str, command: str, **kwargs: Any) -> None:
    """Put a command on the link so it is recorded, without an answer.

    For a read the model can answer outright. The command is assembled and logged exactly as a
    move is, and the value is returned by the caller rather than written into a reply for the
    caller to take apart again: a reply invented here would only ever be read by the parser that
    invented it.

    Args:
      module: the module to address.
      command: the two-letter command code.
      kwargs: the command's own parameters, so the bytes logged are the bytes that would go.
    """
    await self._driver.send_command(module=module, command=command, **kwargs)

  async def answer(self, module: str, command: str, **kwargs: Any) -> Optional[Tuple[Any, str]]:
    """What this feature would answer the command with, taken from the model.

    The link asks each feature in turn, so a read assembles and logs its command exactly as a
    move does, rather than being intercepted before it becomes one. The answer is in the shape
    the caller's format implies - the parsed reply, or the raw one where no format was given -
    because that is what the real read is about to work on.

    Args:
      module: the module the command was addressed to.
      command: the two-letter command code.
      kwargs: the command's own parameters, for the reads that vary by one.

    Returns:
      The answer, and where in the model it came from. None when this feature does not answer
      that command, which is every command that only moves.
    """
    return None


# What liquid stands in: every kind of container but a trash.
_LIQUID_KINDS = (
  pb.RESOURCE_KIND_CONTAINER,
  pb.RESOURCE_KIND_WELL,
  pb.RESOURCE_KIND_TROUGH,
  pb.RESOURCE_KIND_TUBE,
  pb.RESOURCE_KIND_PETRI_DISH,
)


async def _get_container_under(
  deck: handles.Deck, x: float, y: float
) -> Optional[handles.Container]:
  """The smallest container on the deck whose footprint holds the point, or None.

  Every container is asked in one read, which is fine for a deck of hundreds and no more.
  """
  containers = [
    c for c in await deck.find_resources(kinds=_LIQUID_KINDS) if isinstance(c, handles.Container)
  ]
  answers = await model.resolve_geometry(deck.server, [model.query(c, deck) for c in containers])
  found: Optional[handles.Container] = None
  found_area = 0.0
  for container, answer in zip(containers, answers):
    corner, size = answer.locations[0], answer.size
    if not (corner.x <= x <= corner.x + size.x and corner.y <= y <= corner.y + size.y):
      continue
    if found is None or size.x * size.y < found_area:
      found, found_area = container, size.x * size.y
  return found


async def _height_of(container: handles.Container, volume: float) -> float:
  """How high `volume` stands above a container's cavity bottom, in mm.

  Raises:
    RuntimeError: The container has no height-volume data to say.
  """
  try:
    return await container.compute_height_from_volume(volume)
  except ServerError as error:
    if error.problem != pb.PROBLEM_NO_HEIGHT_VOLUME_DATA:
      raise
    raise RuntimeError(
      f"the simulator cannot say where {volume} uL stands in {container.name}: the container "
      "has no height-volume data. Generate a height_volume_data dictionary for it and consider "
      "contributing it back to PyLabRobot :)"
    ) from None


async def _held_volume(container: handles.Container) -> float:
  """What a container holds, counting what is booked and not yet resolved."""
  return (await container.state()).volume.pending_volume


def _is_tool(node: pb.ResourceNode) -> bool:
  return node.attributes.kind in (pb.RESOURCE_KIND_TIP, pb.RESOURCE_KIND_HEAD_TOOL)


def _below_stop_disc_of(tool: Optional[pb.ResourceNode]) -> float:
  """How far a tool's Z reference sits below the stop disc of the shaft carrying it, in mm.

  CO-RE grippers are measured at the grip line; tips are measured at their bottom.
  """
  if tool is None:
    return 0.0
  bottom = tool.attributes.location.z
  if resource_model.grips(tool.attributes):
    return -bottom - resource_model.grip_line_height(tool.attributes)
  return -bottom


class SimulatedPipettes(_Simulated, Pipettes):
  """The pipetting channels, answering for themselves."""

  def _declared_channel(self, channel: int) -> PipetteConfiguration:
    """What this device was told sits on a channel, or the channel this frame documents.

    Args:
      channel: which channel, 0-indexed from the back.

    Returns:
      The channel to answer from.
    """
    declared = self.device.simulated_pipettes
    if declared is not None and channel < len(declared.channels):
      return declared.channels[channel]
    return PipetteConfiguration()

  async def initialize(self, *args, **kwargs):
    """Whatever was mounted on the channels comes off. Goes through the command path, so it is
    coordinated like the real one."""
    await super().initialize(*args, **kwargs)
    self.device.tips_mounted = [False] * len(self.device.tips_mounted)

  @staticmethod
  def _get_travel_time(distance: float, speed: float, acceleration: Optional[float]) -> float:
    """How long a move of `distance` takes at `speed`, speeding up and slowing down at
    `acceleration`, in seconds. With no acceleration stated it is the cruise alone."""
    distance = abs(distance)
    if distance == 0.0:
      return 0.0
    if acceleration is None:
      return distance / speed
    if distance * acceleration < speed * speed:  # never reaches cruise
      return 2 * math.sqrt(distance / acceleration)
    return distance / speed + speed / acceleration

  async def _tools(self) -> List[Optional[pb.ResourceNode]]:
    """What each channel carries, per channel: what the model has on its shaft, or what it had
    when a tool command staged its change, until the command is resolved - the device carries
    that while the command runs."""
    if self.carried_while_staged is not None:
      return list(self.carried_while_staged)
    tools = await self.get_tools()
    return tools + [None] * (self.num_channels - len(tools))

  async def _carries_tips(self) -> List[bool]:
    """Whether each channel carries a tip: one on its shaft, or one it was started with."""
    mounted = self.device.tips_mounted
    return [
      tool is not None or (channel < len(mounted) and mounted[channel])
      for channel, tool in enumerate(await self._tools())
    ]

  async def _below_stop_discs(self) -> List[float]:
    """How far each channel's tool's Z reference sits below its stop disc, in mm."""
    return [_below_stop_disc_of(tool) for tool in await self._tools()]

  async def _below_stop_disc(self, channel: int) -> float:
    """How far the tool on one channel sits below its stop disc, in mm. See `_below_stop_discs`."""
    return (await self._below_stop_discs())[channel]

  async def _modelled_ys(self) -> List[float]:
    """Where the model has every channel along Y, in mm, or where initialization spreads one that
    nothing models yet."""
    defaults = self.default_initialize_y_positions()
    return [
      defaults[channel] if point is None else point.y
      for channel, point in enumerate(await self.get_reference_point_locations())
    ]

  async def _modelled_zs(self) -> List[float]:
    """Where the model has every channel's stop disc along Z, in mm, or the top of the drive's
    window for one nothing models yet, which is where Z safety leaves a device just switched on."""
    top = self.configuration.z_range[1]
    return [
      top if point is None else point.z for point in await self.get_reference_point_locations()
    ]

  async def _modelled_y(self, channel: int) -> float:
    """Where the model has one channel along Y, in mm. See `_modelled_ys`."""
    return (await self._modelled_ys())[channel]

  async def update_locations_by_reference_point(
    self, positions: Dict[int, Tuple[Optional[float], Optional[float]]]
  ) -> None:
    """Record where channels are, and charge the device for the time the drives would take.

    A simulated device answers at once, so a run is over before anything watching it has been given
    a turn. What a move would have taken is owed here and waited out before the next command, which
    paces a run without any command pretending to be slow in itself.
    """
    if self.device.simulate_motion_time:
      ys, zs = await self._modelled_ys(), await self._modelled_zs()
      for channel, (y, z) in positions.items():
        self.device.owe_motion_time(
          self._get_travel_time(0.0 if y is None else y - ys[channel], self.default_y_speed, None),
          self._get_travel_time(
            0.0 if z is None else z - zs[channel],
            self.default_z_speed,
            self.default_z_acceleration,
          ),
        )
    await super().update_locations_by_reference_point(positions)

  async def _container_under(self, channel: int) -> Optional[handles.Container]:
    """The smallest container on the deck whose footprint has the channel's tip over it, or None."""
    deck = self._driver.deck
    point = await self.get_reference_point_location(channel)
    if deck is None or point is None:
      return None
    return await _get_container_under(deck, point.x, point.y)

  async def _liquid_surface(
    self, channel: int
  ) -> Tuple[Optional[handles.Container], Optional[float]]:
    """The container a channel searches and where its liquid stands, in mm on the deck.

    The container is the one the batch search named, else the one under the tip. The surface is
    None for no container or an empty one.
    """
    container = self.device.liquid_searches.get(channel) or await self._container_under(channel)
    if container is None:
      return None, None
    volume = await _held_volume(container)
    if volume <= 0:
      return container, None
    deck = self._driver.deck
    assert deck is not None
    (bottom,) = await model.locations_in([container], deck, "c", "c", "cb")
    return container, round(bottom.z + await _height_of(container, volume), 2)

  async def _answer_liquid_search(
    self, channel: int, command: str, **kwargs: Any
  ) -> Optional[Tuple[Any, str]]:
    """What `ZL` or `ZE` answers: the surface in the container the channel searches, or nothing.

    The stop disc ends `zi` above where the tip met the surface, as `zj` 1 leaves it, and the
    height is latched for `C0 RL`. A search that meets no liquid above `zh` ends there, zeroes
    the latch, and answers as the device does, with trace 70.
    """
    c = self.configuration
    container, surface = await self._liquid_surface(channel)
    below = await self._below_stop_disc(channel)
    end = c.z_drive_increments_to_mm(int(kwargs["zh"]))
    if surface is None or surface + below < end:
      await self.update_location_by_reference_point(channel, z=end)
      self.device.last_lld_heights[channel] = 0.0
      check_fw_string_error(f"{self.channel_id(channel)}{command}id0000er70")
    assert container is not None and surface is not None
    detected = round(surface + below, 2)
    retreat = c.z_drive_increments_to_mm(int(kwargs.get("zi", 0)))
    up = str(kwargs.get("zj", 1)) == "1"
    await self.update_location_by_reference_point(
      channel, z=round(detected + (retreat if up else -retreat), 2)
    )
    self.device.last_lld_heights[channel] = surface
    source = f"the liquid in {container.name}"
    if command == "ZE":
      # Two values as the device answers, the second 0 unless foam was searched through.
      return {"if": [c.z_drive_mm_to_increments(detected), 0]}, source
    return None, source

  def _record_simulated_tadm(self, command: str, **kwargs: Any) -> None:
    """A curve for each involved channel a recording `C0 AS` or `DS` runs on, monitored.

    The firmware records when the command asks (`gk` 2) and the channel's monitoring is on. The
    curve is made up, but shaped as one is: still air, the pressure moving as the piston does
    (down drawing, up pushing), in proportion to the volume, then settling back.
    """
    if str(kwargs.get("gk", 0)) != "2":
      return
    operation, field = (0, "av") if command == "AS" else (1, "dv")
    used = 0
    for index, involved in enumerate(kwargs["tm"]):
      if not int(involved):
        continue
      volume = int(kwargs[field][used]) / 10
      used += 1
      if not self.device.tadm_monitoring.get(index):
        continue
      depth = round(40 + volume / 2) * (-1 if operation == 0 else 1)
      stroke = 20 + round(volume / 5)
      pressures = (
        [0] * 10
        + [round(depth * (i + 1) / 10) for i in range(10)]
        + [depth] * stroke
        + [round(depth * (9 - i) / 10) for i in range(10)]
      )
      self.device.tadm_fifo.setdefault(index, []).append((operation, pressures))

  def _answer_tadm(self, channel: int, command: str, **kwargs: Any) -> Optional[Tuple[Any, str]]:
    """What a channel's TADM commands answer, as the device's raw replies; None for others."""
    d, cid = self.device, self.channel_id(channel)
    if command == "AF":
      return None
    if command == "BG":
      d.tadm_monitoring[channel] = True
      return None
    if command == "BH":
      d.tadm_monitoring[channel] = False
      return None
    if command == "AN":
      d.tadm_fifo[channel] = []
      d.tadm_pointer[channel] = None
      return None
    if command == "QM":
      fifo = d.tadm_fifo.get(channel) or []
      d.tadm_pointer[channel] = fifo.pop(0) if fifo else None
      more = d.tadm_pointer[channel] is not None
      return f"{cid}QMid0000qm{int(more)}", f"channel {channel}'s TADM FIFO"
    if command == "QL":
      at = d.tadm_pointer.get(channel)
      if at is None:
        return (
          f"{cid}QLid0000ql0000 0 0 0000 0000nr0000gd",
          f"channel {channel}'s empty TADM pointer",
        )
      operation, pressures = at
      return (
        f"{cid}QLid0000ql{len(pressures):04} {operation} 0 0000 0000nr0000gd",
        f"channel {channel}'s TADM curve",
      )
    if command == "QN":
      at = d.tadm_pointer.get(channel)
      pressures = [] if at is None else at[1]
      start, count = int(kwargs["li"]), int(kwargs["ln"])
      values = " ".join(f"{v:+05d}" for v in pressures[start : start + count])
      return f"{cid}QNid0000qn{values}", f"channel {channel}'s TADM curve"
    return None

  async def _answer_ztouch(self, channel: int, **kwargs: Any) -> Tuple[Any, str]:
    """What `ZH` answers: the stop disc where the tip met the floor of the container under it.

    The floor is the container's cavity bottom, as the model has it. Nothing under the tip, or a
    floor below the search end, and the search runs to `za` and answers that, as the device does.
    """
    c = self.configuration
    end = c.z_drive_increments_to_mm(int(kwargs["za"]))
    container = await self._container_under(channel)
    deck = self._driver.deck
    stopped = end
    source = "the end of an untouched search"
    if container is not None and deck is not None:
      (floor,) = await model.locations_in([container], deck, "c", "c", "cb")
      touched = round(floor.z + await self._below_stop_disc(channel), 2)
      if touched > end:
        stopped, source = touched, f"the floor of {container.name}"
    await self.update_location_by_reference_point(channel, z=stopped)
    return {"rz": c.z_drive_mm_to_increments(stopped)}, source

  async def answer(self, module: str, command: str, **kwargs: Any) -> Optional[Tuple[Any, str]]:
    """What a read of the channels answers, taken from the model.

    The channels keep no positions of their own here: the model is where a channel is, and a read
    finds it there. What puts it there is the move, which records as it does on a device.
    """
    c = self.configuration
    if module == "C0":
      if command == "RY":
        return (
          {"ry": [round(y * 10) for y in await self._modelled_ys()]},
          "where the model has the channels along Y",
        )

      if command == "RT":
        return (
          {"rt": [int(carries) for carries in await self._carries_tips()]},
          "what the channels carry",
        )

      if command == "RZ":
        # The master reports the bottom of what a channel carries, or its stop disc when empty.
        zs, below = await self._modelled_zs(), await self._below_stop_discs()
        return (
          {"rz": [round((z - b) * 10) for z, b in zip(zs, below)]},
          "where the model has the bottom of what each channel carries",
        )
      if command == "RL":
        return (
          {
            "lh": [
              round(self.device.last_lld_heights.get(channel, 0.0) * 10)
              for channel in range(self.num_channels)
            ]
          },
          "what each channel last detected liquid at",
        )
      if command in ("TP", "TR"):
        # As a device showed: a pick-up takes the pistons to 0, a drop leaves them 10 uL up; the
        # old tip's air goes with it. A drop lets go of a tip the device holds that the model does
        # not, too.
        mounted = self.device.tips_mounted
        for index, involved in enumerate(kwargs["tm"]):
          if int(involved):
            standing = self.device.dispensing_drive_uL.get(index, 0.0)
            self.device.dispensing_drive_uL[index] = 0.0 if command == "TP" else standing + 10.0
            self.device.transport_air_uL.pop(index, None)
            if command == "TR" and index < len(mounted):
              mounted[index] = False
        return None
      if command in ("AS", "DS"):
        self._record_simulated_tadm(command, **kwargs)
      if command == "AS":
        # The command moves the channels itself: each involved one to its Y and, at the end, its
        # tip bottom to `te`. That is what the model has to show when the driver reads back.
        end = int(kwargs["te"]) / 10
        below = await self._below_stop_discs()
        moved: Dict[int, Tuple[Optional[float], Optional[float]]] = {}
        # The per-channel lists run over the channels involved, in order, not over the pattern.
        used = 0
        for index, (involved, y) in enumerate(zip(kwargs["tm"], kwargs["yp"])):
          if not involved:
            continue
          moved[index] = (int(y) / 10, round(end + below[index], 2))
          # The piston draws the blow-out air, the volume and the transport air, and stands there.
          drawn = sum(int(kwargs[field][used]) for field in ("ba", "av", "ta")) / 10
          self.device.dispensing_drive_uL[index] = round(
            self.device.dispensing_drive_uL.get(index, 0.0) + drawn, 1
          )
          held = self.device.transport_air_uL.get(index, 0.0)
          self.device.transport_air_uL[index] = round(held + int(kwargs["ta"][used]) / 10, 1)
          used += 1
        await self.update_locations_by_reference_point(moved)
        return None
      if command == "DS":
        end = int(kwargs["te"]) / 10
        below = await self._below_stop_discs()
        moved = {}
        used = 0
        for index, (involved, y) in enumerate(zip(kwargs["tm"], kwargs["yp"])):
          if not involved:
            continue
          moved[index] = (int(y) / 10, round(end + below[index], 2))
          # The piston pushes out the transport air the tip holds and the volume; the blow-out air
          # too in a blow-out mode; everything in an empty.
          standing = self.device.dispensing_drive_uL.get(index, 0.0)
          mode = str(kwargs["dm"][used])
          pushed = self.device.transport_air_uL.get(index, 0.0) + int(kwargs["dv"][used]) / 10
          if mode in ("1", "3"):
            pushed += int(kwargs["ba"][used]) / 10
          left = 0.0 if mode == "4" else max(standing - pushed, 0.0)
          # Then it draws this command's transport air, after an empty too; the stop-back leaves
          # the piston where the dispense did.
          air = int(kwargs["ta"][used]) / 10
          self.device.transport_air_uL[index] = air
          self.device.dispensing_drive_uL[index] = round(left + air, 1)
          used += 1
        await self.update_locations_by_reference_point(moved)
        return None

      return None

    channel = self.channel_from_module(module)
    if channel is None or channel >= self.num_channels:
      return None

    tadm = self._answer_tadm(channel, command, **kwargs)
    if tadm is not None:
      return tadm

    if command == "VY":
      width = self._declared_channel(channel).width
      if width is None:
        raise RuntimeError(
          f"the simulated channel {channel} has no width; set it on its configuration"
        )
      # The drive answers twice; the read takes the second.
      increments = c.y_drive_mm_to_increments(width)
      return {"yc": [increments, increments]}, f"channel {channel}'s declared width"

    if command == "RZ":
      return (
        {"rz": c.z_drive_mm_to_increments((await self._modelled_zs())[channel])},
        f"where the model has channel {channel}'s stop disc",
      )
    if command == "DC":
      # The piston draws the air and stands there.
      self.device.dispensing_drive_uL[channel] = round(
        self.device.dispensing_drive_uL.get(channel, 0.0)
        + c.dispensing_drive_increments_to_uL(int(kwargs["dh"])),
        1,
      )
      return None
    if command == "DS":
      # The piston moves by the distance, up to draw or down to push; a push sends the tip's
      # transport air out first.
      moved_uL = c.dispensing_drive_increments_to_uL(int(kwargs["ds"]))
      pushing = kwargs["dt"] == "1"
      self.device.dispensing_drive_uL[channel] = round(
        self.device.dispensing_drive_uL.get(channel, 0.0) + (-moved_uL if pushing else moved_uL),
        1,
      )
      if pushing:
        held = self.device.transport_air_uL.pop(channel, 0.0)
        if held > moved_uL:
          self.device.transport_air_uL[channel] = round(held - moved_uL, 1)
      return None
    if command == "RD":
      uL = self.device.dispensing_drive_uL.get(channel, 0.0)
      return (
        {"rd": c.dispensing_drive_uL_to_increments(uL)},
        f"where channel {channel}'s piston stands, from what it drew",
      )
    if command in ("ZL", "ZE"):
      return await self._answer_liquid_search(channel, command, **kwargs)
    if command == "ZH":
      return await self._answer_ztouch(channel, **kwargs)

    # A channel's drive keeps what `AA` writes, and what its own `ZA` moves with.
    stored = self.device.channel_drive_parameters.setdefault(
      channel, dict(SIMULATED_CHANNEL_DRIVE_PARAMETERS)
    )
    if command in ("AA", "ZA"):
      for parameter in stored:
        if parameter in kwargs:
          stored[parameter] = int(kwargs[parameter])
      return None

    if command == "RA" and kwargs.get("ra") in stored:
      parameter = kwargs["ra"]
      return {parameter: stored[parameter]}, f"what channel {channel}'s drive holds"

    return None

  async def probe_z_max(self) -> List[float]:
    # The firmware retract inside the probe is what puts the channels at their ceiling, and the
    # probe reads them back before it returns, so the model is written before the read rather
    # than after. `move_to_safe_z` runs this probe, so it needs no override of its own.
    top = self.configuration.z_range[1]
    await self.update_locations_by_reference_point(
      {channel: (None, top) for channel in range(self.num_channels)}
    )
    return await super().probe_z_max()

  async def _probe_batch_liquid_heights(
    self, batch: Any, containers: Any, *args: Any, **kwargs: Any
  ):
    """Say which container each channel searches, so its searches are answered from it."""
    self.device.liquid_searches = {
      channel: containers[job] for channel, job in zip(batch.channels, batch.indices)
    }
    try:
      return await super()._probe_batch_liquid_heights(batch, containers, *args, **kwargs)
    finally:
      self.device.liquid_searches = {}

  async def _unchecked_fw_move_lowest_point_to_z_positions(self, zs: Dict[int, float]):
    # A move is what puts a channel somewhere. Written after the move, not before: one the real
    # method refuses never happened. The move places the lowest point - the end of a carried tip,
    # or the stop disc - and the model holds the stop disc, so a tip puts it that much higher.
    resp = await super()._unchecked_fw_move_lowest_point_to_z_positions(zs)
    below = await self._below_stop_discs()
    await self.update_locations_by_reference_point(
      {channel: (None, z + below[channel]) for channel, z in zs.items()}
    )
    return resp

  async def _record_tip_command(
    self,
    x_positions: List[int],
    y_positions: List[int],
    tip_pattern: List[bool],
    z: int,
    overhang: float = 0.0,
    descend_to: Optional[int] = None,
  ) -> None:
    """Put the arm and the channels where a tip command leaves them, as the reads will find them.

    The arm ends over the last column the command visited, and each channel taking part at its Y.
    The Z drives are each their own, so an unnamed channel keeps its height: `rz +2450 +3343
    +3343 ...`. In Y they share a rail, so the device brings the others along: the same pick-up
    answers `ry +2418 +2328 +2238 ...`.

    The height a tip command ends at is its lowest point, and the model holds the stop disc, so a
    channel that came away with a tip ends that much higher. As the device answers a pick-up of a
    300 uL tip at `th2450`: the master reads the lowest points as `rz +2450 +3343 ...`, and the
    channel itself reads `rz +27674` increments - 296.9 mm, the traverse height plus the 51.9 mm
    the tip hangs below the disc.

    Args:
      x_positions, y_positions, tip_pattern: the command, in tenths of a millimetre.
      z: the height the command ends at, in tenths of a millimetre.
      overhang: how far what the channels now carry hangs below the stop disc, in mm. Nothing for
        a command that leaves them empty.
      descend_to: the lowest point of the stroke, in tenths of a millimetre. Recorded as a stop of
        its own so the descent is seen; only the end is recorded when it is None.
    """
    involved = [i for i, used in enumerate(tip_pattern) if used and i < self.num_channels]
    if not involved:
      return
    await self.arm.update_location_by_reference_point(x_positions[involved[-1]] / 10)

    # One rail, so the channels not named are moved as far as the spacing asks - the rule a Y
    # move already goes by.
    sent = {channel: y_positions[channel] / 10 for channel in involved}
    try:
      planned = await self._plan_y_positions(sent, make_space=True)
    except ValueError:
      # No room for the others, as a packed discard leaves none: the firmware arranges them.
      planned = sent
    # The stroke as the device makes it: across at the height it starts from, down onto the spots,
    # and back up. Recorded as one stop, the whole command is a single jump to wherever it ended.
    await self.update_locations_by_reference_point(
      {channel: (y, None) for channel, y in planned.items()}
    )
    if descend_to is not None:
      await self.device.pay_motion_time()
      below = await self._below_stop_discs()
      await self.update_locations_by_reference_point(
        {channel: (None, descend_to / 10 + below[channel]) for channel in involved}
      )
      await self.device.pay_motion_time()
    await self.update_locations_by_reference_point(
      {channel: (None, z / 10 + overhang) for channel in involved}
    )

  async def _unchecked_fw_pick_up_tips(
    self,
    x_positions: List[int],
    y_positions: List[int],
    tip_pattern: List[bool],
    tip_type_index: int,
    begin_tip_pick_up_process: int,
    end_tip_pick_up_process: int,
    minimum_traverse_height_start: int,
    pickup_method: TipPickupMethod,
    read_timeout: int = 120,
  ):
    resp = await super()._unchecked_fw_pick_up_tips(
      x_positions=x_positions,
      y_positions=y_positions,
      tip_pattern=tip_pattern,
      tip_type_index=tip_type_index,
      begin_tip_pick_up_process=begin_tip_pick_up_process,
      end_tip_pick_up_process=end_tip_pick_up_process,
      minimum_traverse_height_start=minimum_traverse_height_start,
      pickup_method=pickup_method,
    )
    # The channels come away carrying a tip of this type, which hangs below the stop disc by the
    # length the type was defined with.
    await self._record_tip_command(
      x_positions,
      y_positions,
      tip_pattern,
      minimum_traverse_height_start,
      overhang=self.device.defined_tip_lengths.get(tip_type_index, 0.0),
      descend_to=end_tip_pick_up_process,
    )
    return resp

  async def _unchecked_fw_drop_tips(
    self,
    x_positions: List[int],
    y_positions: List[int],
    tip_pattern: List[bool],
    begin_tip_deposit_process: int,
    end_tip_deposit_process: int,
    minimum_traverse_height_start: int,
    minimum_traverse_height_end: int,
    discarding_method: TipDropMethod,
  ):
    resp = await super()._unchecked_fw_drop_tips(
      x_positions=x_positions,
      y_positions=y_positions,
      tip_pattern=tip_pattern,
      begin_tip_deposit_process=begin_tip_deposit_process,
      end_tip_deposit_process=end_tip_deposit_process,
      minimum_traverse_height_start=minimum_traverse_height_start,
      minimum_traverse_height_end=minimum_traverse_height_end,
      discarding_method=discarding_method,
    )
    await self._record_tip_command(
      x_positions,
      y_positions,
      tip_pattern,
      minimum_traverse_height_end,
      descend_to=end_tip_deposit_process,
    )
    return resp

  async def move_stop_disc_to_z_position(self, channel: int, z: float, *args: Any, **kwargs: Any):
    resp = await super().move_stop_disc_to_z_position(channel, z, *args, **kwargs)
    await self.update_location_by_reference_point(channel, z=z)
    return resp

  async def request_firmware_version(self, channel: int) -> Tuple[str, datetime.date]:
    # What the channel was declared to run, where the declaration says: a recording taken with
    # `save_configuration` carries no channel firmware, because it is a field discovery fills from
    # this very read, so the simulator's own table stands in where it is not there.
    await self.recorded(self.channel_id(channel), "RF")
    declared = self._declared_channel(channel).firmware_version
    if declared is None:
      raise RuntimeError(
        f"the simulated channel {channel} has no firmware version; set it on its configuration"
      )
    return declared, parse_firmware_version_date(declared)

  async def request_pipette_configuration(self, channel: int) -> PipetteConfiguration:
    # Only what the read reports: the rest of a channel's configuration is filled by discovery
    # from other reads, as it is on a device.
    await self.recorded(self.channel_id(channel), "VW")
    declared = self._declared_channel(channel)
    return PipetteConfiguration(
      channel_type=declared.channel_type,
      head_type=declared.head_type,
      stop_disc_type=declared.stop_disc_type,
      pressure_adc=declared.pressure_adc,
    )


# Where the left arm has come to rest when a simulated device is switched on, in mm: far enough
# along the rail to sit within reach of any STAR deck. The right arm rests at the far end of its
# own travel instead, so the two do not overlap on a device that has both. Setup reads this once
# to seat each arm on the deck; every read after that answers from the deck.
SIMULATED_LEFT_X_ARM_POSITION = 362.9


class SimulatedXArm(_Simulated, XArm):
  """An X-arm, answering for itself."""

  async def answer(self, module: str, command: str, **kwargs: Any) -> Optional[Tuple[Any, str]]:
    arm_number = "1" if self.side == "left" else "2"
    if module == "X0" and command == "QW" and kwargs.get("mn") == arm_number:
      return {"qw": 1}, f"the {self.side} X-arm, which a simulated device keeps initialized"
    # Both arms are answered in one reply, so the first arm answers it for the device.
    if module != "C0" or command not in ("RU", "UA") or self is not self.device.arms[0]:
      return None
    declared = self.device.simulated_configuration
    arms = (declared.left_arm, declared.right_arm)

    def tenths(value: Optional[float]) -> int:
      return 0 if value is None else round(value * 10)

    if command == "RU":
      values = [tenths(v) for arm in arms for v in (arm.x_range if arm and arm.x_range else (0, 0))]
      return "ru" + " ".join(str(v) for v in values), "the declared arms' X ranges"
    wraps = [tenths(arm.wrap_size if arm else None) for arm in arms]
    workspaces = [
      tenths(v)
      for arm in arms
      for v in (arm.workspace_x_range if arm and arm.workspace_x_range else (0, 0))
    ]
    return "ua" + " ".join(str(v) for v in wraps + workspaces), "the declared arms' envelopes"

  async def request_firmware_version(self) -> Tuple[str, datetime.date]:
    declared = self.configuration.firmware_version
    if declared is None:
      raise RuntimeError(
        f"the simulated {self.side} X-arm has no firmware version; set it on its configuration"
      )
    return declared, parse_firmware_version_date(declared)

  async def request_position(self) -> float:
    # Where the arm is is what the model says: a simulated device has no drive to ask. Until setup
    # has put it on the deck there is nothing to read, and it answers where it powered up.
    modelled = await self.get_reference_point_x()
    if modelled is not None:
      return modelled
    if self.side == "left" or self.configuration.x_range is None:
      return SIMULATED_LEFT_X_ARM_POSITION
    return self.configuration.x_range[1]


class _SimulatedHead(_Simulated, Head):
  """What a head answers when there is no head: the same for either of them.

  Each head says which simulated configuration it answers from and where a retract leaves it; what
  its configuration bytes mean is its own, as on a device.
  """

  _firmware_key: str
  _label: str

  @property
  def _z_safety(self) -> float:
    """Where a retract leaves this head, in mm: the top of the window its configuration states.

    Returns:
      The Z its drive comes to rest at.
    """
    return self.configuration.z_range[1]

  @property
  def _declared(self) -> HeadConfiguration:
    """The head this device was told it has.

    Distinct from `configuration`, which discovery fills from these answers exactly as it would
    off an device.
    """
    raise NotImplementedError("a simulated head says which configuration it answers from")

  def _stored(self, table: Literal["py", "pz"]) -> Dict[str, int]:
    """One of the head's stored position tables, as the ten slots the device holds.

    Args:
      table: which table, `py` along Y or `pz` along Z.

    Returns:
      Each slot in increments, keyed as `configuration.predefined_y_slots` names them.

    Raises:
      RuntimeError: If the head was declared without that table, so there is nothing to answer.
    """
    axis = "y" if table == "py" else "z"
    stored = getattr(self._declared, f"predefined_{axis}_positions_increments")
    if stored is None:
      raise RuntimeError(
        f"the simulated {self._label} has no {table} table; set it on its configuration"
      )
    return cast(Dict[str, int], stored)

  async def _carries_a_tool(self) -> bool:
    """Whether the model has a tip or a tool on any of the head's shafts."""
    if self.resource is None:
      return False
    response = await self.resource.server.commands.find_resources(
      spb.FindResourcesRequest(
        scope=self.resource.ref,
        filter=spb.ResourceFilter(kinds=[pb.RESOURCE_KIND_TIP, pb.RESOURCE_KIND_HEAD_TOOL]),
        page_size=1,
      )
    )
    return bool(response.nodes)

  async def _modelled_a1(self) -> Optional[Coordinate]:
    """Where the model has channel A1's shaft corner, in mm on the deck; None while unmodelled."""
    deck = self.device.deck
    if self.resource is None or deck is None:
      return None
    (a1,) = await model.locations_in([self.shafts[HEAD_REFERENCE_SHAFT]], deck)
    return a1

  async def answer(self, module: str, command: str, **kwargs: Any) -> Optional[Tuple[Any, str]]:
    c = self.configuration
    if module == "C0" and command == "RA" and kwargs.get("ra") == c.x_offset_parameter:
      x_offset = self._declared.x_offset
      if x_offset is None:
        raise RuntimeError(
          f"the simulated {self._label} has no X offset; set it on its configuration"
        )
      return {c.x_offset_parameter: round(x_offset * 10)}, f"the {self._label}'s declared X offset"

    if module == "C0" and command in (c.tip_presence_command, c.position_command):
      a1 = await self._modelled_a1()
      if a1 is None:
        raise RuntimeError(f"the simulated {self._label} is not modelled, so it has nothing to say")
      if command == c.tip_presence_command:
        carries = await self._carries_a_tool()
        return {command.lower(): int(carries)}, f"whether the {self._label} is modelled with tips"
      # Channel A1, at the bottom of whatever it carries, as the master reports it.
      tool = (await self._get_tools([HEAD_REFERENCE_SHAFT]))[HEAD_REFERENCE_SHAFT]
      z = a1.z + (tool.attributes.location.z if tool is not None else 0.0)
      return (
        {
          "xs": abs(round(a1.x * 10)),
          "xd": 0 if a1.x >= 0 else 1,
          c.y_parameter: round(a1.y * 10),
          c.z_parameter: round(z * 10),
        },
        f"where the {self._label}'s channel A1 is modelled",
      )

    if module != c.module:
      return None

    if command == "QG":
      head_type = self._declared.head_type
      if head_type is None:
        raise RuntimeError(f"the simulated {self._label} has no type; set it on its configuration")
      code = next((k for k, name in c.head_types.items() if name == head_type), None)
      if code is None:
        raise RuntimeError(f"{head_type!r} is not one of the types {self._label} reports")
      return {"qg": code}, f"the {self._label}'s declared type"

    if command == "RY":
      # From the model where there is one, as the real read reports the drive. The drive answers
      # in the deck's frame, so the model is read in the deck's too - the resource hangs off the
      # arm, whose own position would otherwise come through. Before setup has put the head on the
      # arm there is nothing to read, and it answers from the middle of its travel.
      point = await self.get_reference_point_location()
      if point is not None:
        y = round(point.y, 2)
      else:
        # Nothing models it yet, so where it parks: the home slot of its own stored table.
        y = c.y_drive_increments_to_mm(self._stored("py")["home"] + c.predefined_y_position_origin)
      increments = c.y_drive_mm_to_increments(y)
      # The drive answers twice; the read takes the second.
      return {"ry": [increments, increments]}, f"where the {self._label} is modelled along Y"

    if command == "RZ":
      z = await self._modelled_z()
      increments = c.z_drive_mm_to_increments(z)
      return {"rz": [increments, increments]}, f"where the {self._label} is modelled along Z"

    if command == "RA":
      parameter = cast(str, kwargs.get("ra"))
      if parameter in ("py", "pz"):
        # As a head holds them: the position it parks at first, then nine slots nothing here
        # commands against. Answered as the drive stores them, offsets from its own origin
        # included, which is how the read converts them back.
        stored = self._stored(cast(Literal["py", "pz"], parameter))
        declared = self._declared
        names = declared.predefined_y_slots if parameter == "py" else declared.predefined_z_slots
        return (
          {parameter: [stored[name] for name in names]},
          f"the {self._label}'s stored {parameter} table",
        )
      value = self._simulated_drive_parameter(parameter)
      return (
        {parameter: self._drive_parameter_to_increments(parameter, value)},
        f"the {self._label}'s {parameter} default",
      )
    return None

  async def request_firmware_version(self) -> Tuple[str, datetime.date]:
    await self.recorded(self.configuration.module, "RF")
    version = self._declared.firmware_version
    if version is None:
      raise RuntimeError(f"the simulated {self._label} has no firmware version declared")
    return version, parse_firmware_version_date(version)

  def _simulated_drive_parameter(self, parameter: str) -> float:
    """What this head holds in a drive register, for the link to answer with.

    Guarded as the real read guards it: a name the head does not store is a caller's mistake, and
    should say so here as it would there rather than raising a lookup error.

    Args:
      parameter: the two-letter register name.

    Returns:
      The value in mm/s or mm/s2.

    Raises:
      RuntimeError: If this head was declared without a default for it.
    """
    self.require_drive_parameter(parameter)
    head = self._declared
    default = {
      "yv": head.y_drive_speed_default,
      "yr": head.y_drive_acceleration_default,
      "zv": head.z_drive_speed_default,
      "zr": head.z_drive_acceleration_default,
    }.get(parameter)
    if default is None:
      raise RuntimeError(
        f"the simulated {self._label} has no {parameter} default; set it on its config"
      )
    return default

  async def probe_z_max(self, *args: Any, **kwargs: Any) -> float:
    # The firmware retract inside the probe is what puts the head at its safety height. Its own
    # `move_to_safe_z` needs no such override: it is an ordinary move, which this already records.
    await self.update_location_by_reference_point(z=self._z_safety)
    return await super().probe_z_max(*args, **kwargs)

  async def move_to_y_position(self, y: float, *args: Any, **kwargs: Any):
    # A move is what puts the head somewhere. On the device the drive holds that and the read
    # reports it; here the model holds it, so the move writes it and the read finds it there.
    # Written after the move, not before: one the real method refuses never happened, and a model
    # updated first would put the head where it was told to go rather than where it is.
    resp = await super().move_to_y_position(y, *args, **kwargs)
    await self.update_location_by_reference_point(y=y)
    return resp

  async def move_stop_disc_to_z_position(self, z: float, *args: Any, **kwargs: Any):
    resp = await super().move_stop_disc_to_z_position(z, *args, **kwargs)
    await self.update_location_by_reference_point(z=z)
    return resp

  async def _modelled_z(self) -> float:
    """Where the model has the head's stop disc, in mm on the deck, or where a retract leaves it
    while nothing models it."""
    a1 = await self._modelled_a1()
    return self._z_safety if a1 is None else round(a1.z, 2)

  async def initialize(self, *args, **kwargs):
    """Whatever was mounted on the head comes off, and it reports itself up. Goes through the
    command path, so it is coordinated like the real one."""
    await super().initialize(*args, **kwargs)
    self.device.initialized[self.configuration.module] = True


class SimulatedHead96(_SimulatedHead, Head96):
  """The 96-head, answering for itself."""

  _firmware_key = "head96"
  _label = "96-head"

  @property
  def _declared(self) -> Head96Configuration:
    return self.device.simulated_head96

  async def request_hardware(self) -> List[str]:
    # Rendered from what this head is, rather than written out separately: a head configured
    # differently answers differently.
    await self.recorded(self.configuration.module, "QU")
    head = self._declared
    return [
      "1" if head.supports_clot_monitoring_clld else "0",
      "0" if head.stop_disc_type == "core_i" else "1",
      "0" if head.instrument_type == "legacy" else "1",
    ] + ["0"] * 7

  def _simulated_drive_parameter(self, parameter: str) -> float:
    # The dispensing and squeezer drives have no register to read, so they answer with what this
    # head's firmware documents.
    head = self._declared
    newer = head.firmware_year >= 2010
    documented = {
      "dv": 261.1,
      "dr": head.dispensing_drive_increments_to_uL(900000 if newer else 150000),
      "sv": head.squeezer_drive_speed_default,
      "sr": head.squeezer_drive_acceleration_default,
    }
    if parameter in documented:
      return documented[parameter]
    return super()._simulated_drive_parameter(parameter)

  async def _answer_clld_search(self, **kwargs: Any) -> Tuple[Any, str]:
    """What `ZL` answers: the surface under the sensing channels, or nothing.

    `lm` picks the sensing channels, those with a tip only: G11/H12, A1/B2, or all four corners.
    Each detects at its container's surface plus its tip's overhang; either sensor triggers first
    at the highest, both only at the lowest. The stop disc ends `zi` above where it detected, as
    `zj` 1 leaves it, and the height is latched for `RH`. A search that meets no liquid above `zh`
    ends there, zeroes the latch, and answers as the device does, with trace 70.
    """
    c = self.configuration
    deck = self.device.deck
    end = c.z_drive_increments_to_mm(int(kwargs["zh"]))
    mode = int(kwargs.get("lm", 2))
    names = {0: ("G11", "H12"), 1: ("A1", "B2")}.get(mode, ("A1", "B2", "G11", "H12"))
    detections: List[Tuple[float, Optional[handles.Container]]] = []
    if self.resource is not None and deck is not None:
      tools = await self._get_tools(list(names))
      tipped = [name for name in names if tools[name] is not None]
      points = await model.locations_in([self.shafts[n] for n in tipped], deck, "c", "c", "b")
      for name, point in zip(tipped, points):
        bottom = cast(pb.ResourceNode, tools[name]).attributes.location.z
        container = await _get_container_under(deck, point.x, point.y)
        if container is None:
          continue
        volume = await _held_volume(container)
        if volume <= 0:
          continue
        try:
          height = await container.compute_height_from_volume(volume)
        except ServerError:
          continue
        (cavity,) = await model.locations_in([container], deck, "c", "c", "cb")
        surface = cavity.z + round(height, 2)
        detections.append((round(surface - bottom, 2), container))
    if mode == 3 and len(detections) < len(names):
      detections = []
    detected, found_in = (
      (min if mode == 3 else max)(detections, key=lambda d: d[0]) if detections else (end - 1, None)
    )
    if found_in is None or detected < end:
      await self.update_location_by_reference_point(z=end)
      self.device.head96_last_lld_z = 0.0
      check_fw_string_error("H0ZLid0000er70")
      raise AssertionError("unreachable: a trace-70 answer raises")
    retreat = c.z_drive_increments_to_mm(int(kwargs.get("zi", 0)))
    up = str(kwargs.get("zj", 1)) == "1"
    await self.update_location_by_reference_point(
      z=round(detected + (retreat if up else -retreat), 2)
    )
    self.device.head96_last_lld_z = detected
    return None, f"the liquid in {found_in.name}"

  async def _answer_stroke(self, command: str, **kwargs: Any) -> Tuple[Any, str]:
    """What `PA` or `PB` does: Z follows the surface by `zd` down or `ze` up, never below `zh`,
    and the piston draws `da` or pushes `db` out and draws `dd` back. The liquid is the layer
    above's to book: a mix returns what it draws."""
    c = self.configuration
    z = await self._modelled_z()
    floor = c.z_drive_increments_to_mm(int(kwargs["zh"]))
    piston = self.device.head96_dispensing_drive_uL
    if command == "PA":
      z = max(z - c.z_drive_increments_to_mm(int(kwargs.get("zd", 0))), floor)
      piston += c.dispensing_drive_increments_to_uL(int(kwargs["da"]))
    else:
      z = min(z + c.z_drive_increments_to_mm(int(kwargs.get("ze", 0))), c.z_range[1])
      pushed = c.dispensing_drive_increments_to_uL(int(kwargs["db"]))
      drawn_back = c.dispensing_drive_increments_to_uL(int(kwargs.get("dd", 0)))
      piston = max(piston - pushed, 0.0) + drawn_back
    await self.update_location_by_reference_point(z=round(z, 2))
    self.device.head96_dispensing_drive_uL = round(piston, 2)
    return None, f"the 96-head's piston at {self.device.head96_dispensing_drive_uL} uL"

  async def _get_tip_overhang(self) -> float:
    """How far the tip on channel A1 hangs below the stop disc, in mm; 0.0 with none on."""
    if self.resource is None:
      return 0.0
    tool = (await self._get_tools([HEAD_REFERENCE_SHAFT]))[HEAD_REFERENCE_SHAFT]
    return 0.0 if tool is None else -tool.attributes.location.z

  async def _record_master_move(self, overhang: float, **kwargs: Any) -> None:
    """Put the arm, the head's Y and its stop disc where a master command leaves them.

    `xs`/`xd` and `yh` place channel A1, whose X is the arm's less `x_offset`. `ze` is the tip
    bottom the command ends at, so the stop disc ends `overhang` above it.
    """
    c = self.configuration
    arm = self.arm
    if arm is not None and c.x_offset is not None:
      x = int(kwargs["xs"]) / 10 * (-1 if str(kwargs.get("xd", 0)) == "1" else 1)
      await arm.update_location_by_reference_point(round(x + c.x_offset, 2))
    await self.update_location_by_reference_point(
      y=int(kwargs["yh"]) / 10, z=round(int(kwargs["ze"]) / 10 + overhang, 2)
    )

  async def _answer_liquid_command(self, command: str, **kwargs: Any) -> None:
    """What `C0 EA` or `C0 ED` does: the head ends over A1 at `ze`, and the piston moves.

    EA draws the blow-out air `bv`, the volume `af` and the transport air `vt`. ED pushes out `vt`
    and `df`, `bv` too in a blow-out mode (`da` 1 or 3), everything in an empty (`da` 4), and draws
    the stop-back volume `ev` back. All in 0.1 uL. The liquid is the layer above's to book.
    """
    await self._record_master_move(await self._get_tip_overhang(), **kwargs)
    piston = self.device.head96_dispensing_drive_uL
    if command == "EA":
      piston += sum(int(kwargs.get(field, 0)) for field in ("bv", "af", "vt")) / 10
    else:
      mode = str(kwargs.get("da", 0))
      pushed = sum(int(kwargs.get(field, 0)) for field in ("vt", "df")) / 10
      if mode in ("1", "3"):
        pushed += int(kwargs.get("bv", 0)) / 10
      piston = 0.0 if mode == "4" else max(piston - pushed, 0.0)
      piston += int(kwargs.get("ev", 0)) / 10
    self.device.head96_dispensing_drive_uL = round(piston, 2)

  async def answer(self, module: str, command: str, **kwargs: Any) -> Optional[Tuple[Any, str]]:
    c = self.configuration
    if module == "C0":
      if command in ("EA", "ED"):
        await self._answer_liquid_command(command, **kwargs)
        return None
      if command == "EP":
        # The stop disc ends a tip of the collected type above `ze`, as the channels' pick-up does.
        tip_length = self.device.defined_tip_lengths.get(int(kwargs["tt"]), 0.0)
        await self._record_master_move(tip_length, **kwargs)
        return None
      if command == "ER":
        await self._record_master_move(0.0, **kwargs)
        return None
    if module == c.module:
      if command == "ZL":
        return await self._answer_clld_search(**kwargs)
      if command == "RH":
        increments = c.z_drive_mm_to_increments(self.device.head96_last_lld_z)
        return {"rh": increments}, "where the 96-head last detected liquid"
      if command in ("PA", "PB"):
        return await self._answer_stroke(command, **kwargs)
      if command == "RD":
        # The drive answers twice; the read takes the second.
        increments = c.dispensing_drive_uL_to_increments(self.device.head96_dispensing_drive_uL)
        return {"rd": [increments, increments]}, "where the 96-head's piston stands"
    return await super().answer(module, command, **kwargs)


class SimulatedHead384(_SimulatedHead, Head384):
  """The 384-head, answering for itself."""

  _firmware_key = "head384"
  _label = "384-head"

  @property
  def _declared(self) -> Head384Configuration:
    return self.device.simulated_head384

  async def request_hardware(self) -> List[str]:
    # Rendered as the 96-head's is, from the two flags this head reports.
    await self.recorded(self.configuration.module, "QU")
    head = self._declared
    return [
      "1" if head.supports_clot_monitoring_clld else "0",
      "1" if head.supports_lld_absolute_threshold_check else "0",
    ] + ["0"] * 8


class SimulatedISWAP(_Simulated, iSWAP):
  """The iSWAP, answering for itself."""

  async def _unchecked_fw_park(self, traverse_height: Optional[float] = None):
    """Park, and put the model where parking leaves the arm: every drive on its stop."""
    resp = await super()._unchecked_fw_park(traverse_height)
    c = self.configuration
    stops = (
      c.elbow_predefined_y_positions_increments,
      c.elbow_predefined_z_positions_increments,
      c.elbow_drive_predefined_increments,
      c.wrist_drive_predefined_increments,
      c.gripper_drive_predefined_increments,
    )
    if any(table is None for table in stops):
      return resp
    y_stops, z_stops, elbow_stops, wrist_stops, gripper_stops = cast(Tuple[Any, ...], stops)
    await self.update_location_by_reference_point(
      y=c.y_increments_to_mm(y_stops.parking),
      z=c.z_increments_to_mm(z_stops.parking) + c.elbow_z_offset_above_finger,
    )
    await self.elbow_drive_update_angle(c.elbow_drive_increments_to_angle(elbow_stops.parking))
    await self.wrist_drive_update_angle(c.wrist_increments_to_deg(wrist_stops.parking))
    # Parking closes the jaws, and the gripper's table names that stop its home.
    await self.gripper_update_width(c.gripper_increments_to_mm(gripper_stops.home))
    return resp

  async def answer(self, module: str, command: str, **kwargs: Any) -> Optional[Tuple[Any, str]]:
    """Answer a read from the model.

    A simulated iSWAP keeps no positions of its own. Its moves record where they were sent once
    the command is away, so a read finds the model already holding it; until one has, the answers
    are where a device that has just been switched on is parked.
    """
    c = self.configuration
    if module == "R0":
      if command == "RW":
        angle = await self.elbow_drive_get_angle()
        if angle is not None:
          return (
            {"rw": c.elbow_drive_angle_to_increments(angle)},
            "which way the model has the arm pointing",
          )
        stops = (await self._request_slots("pw"))[: len(iSWAPElbowPositions.SLOTS)]
        parked = stops[iSWAPElbowPositions.SLOTS.index("parking")]
        return {"rw": parked}, "the elbow drive's parking stop"

      if command == "RY":
        point = await self.elbow_get_reference_point_location()
        if point is None:
          # Nothing models it yet, so where an initialized device leaves it: its parking stop, out
          # of the stored table rather than a position written down here.
          stops = (await self._request_slots("py"))[: len(iSWAPYPositions.SLOTS)]
          parked = stops[iSWAPYPositions.SLOTS.index("parking")]
          return {"ry": [parked, parked]}, "the elbow's parking stop"
        increments = c.y_mm_to_increments(point.y)
        # Two counters come back, the firmware's and the hardware's; the read takes the hardware.
        return {"ry": [increments, increments]}, "where the model has the elbow along Y"

      if command == "RZ":
        point = await self.elbow_get_reference_point_location()
        if point is None:
          # Nothing models it yet, so where an initialized device leaves it: its parking stop, out
          # of the stored table rather than a height written down here.
          stops = (await self._request_slots("pz"))[: len(iSWAPZPositions.SLOTS)]
          parked = stops[iSWAPZPositions.SLOTS.index("parking")]
          return {"rz": [parked, parked]}, "the elbow's parking stop"
        increments = c.z_mm_to_increments(point.z - c.elbow_z_offset_above_finger)
        return {"rz": [increments, increments]}, "where the model has the elbow along Z"
      if command == "RT":
        angle = await self.wrist_drive_get_angle()
        if angle is not None:
          return (
            {"rt": c.wrist_deg_to_increments(angle)},
            "which way the model has the wrist turned",
          )
        # Nothing models it yet, so where an initialized arm leaves it: its parking stop, out of
        # the stored table rather than an angle written down here.
        stops = (await self._request_slots("pt"))[: len(iSWAPWristPositions.SLOTS)]
        parked = stops[iSWAPWristPositions.SLOTS.index("parking")]
        return {"rt": parked}, "the wrist drive's parking stop"
      if command == "RH":
        # Nothing models the force sensor: a simulated arm meets nothing, so its peaks are its
        # idle reading and its last measurement is nothing at all.
        return {"rh": [0, 0, 0, 0, 0]}, "a simulated arm meets nothing, so it feels nothing"

      if command == "RG":
        # The drive answers twice, a target and an actual; the read takes the second.
        gripper = self.gripper
        if gripper is None:
          # Nothing models the jaws, so where an initialized gripper leaves them: the width it
          # homes and parks at, out of the stored table rather than written down here.
          stops = (await self._request_slots("pg"))[: len(iSWAPGripperPositions.SLOTS)]
          home = stops[iSWAPGripperPositions.SLOTS.index("home")]
          return {"rg": [home, home]}, "the gripper's home and parking width"
        width = c.gripper_mm_to_increments(await gripper.get_jaw_width())
        return {"rg": [width, width]}, "how far the model has the jaws open"
    if (module, command) == ("C0", "QP"):
      # Whether the arm holds something is whether the model has anything hanging off the gripper
      # that is not part of the gripper: its body and its two fingers are its own.
      gripper = self.gripper
      held = False
      if gripper is not None:
        spec = await self._gripper_spec()
        own = {spec.body, *spec.fingers}
        held = any(child.name not in own for child in await gripper.get_children())
      return {"ph": int(held)}, "whether the model has anything in the gripper"

    if (module, command) == ("C0", "RA") and kwargs.get("ra") == "kg":
      offset = self._declared.elbow_x_offset
      if offset is None:
        raise RuntimeError("the simulated iSWAP has no X offset; set it on its configuration")
      return {"kg": round(offset * 10)}, "the X offset it was declared with"
    return None

  async def _unchecked_fw_position_components_for_free_y_range(self):
    # The master packs the channels as far forward as they fit. Written before the command, as
    # the retract inside a probe is.
    pipettes = self.arm.pipettes
    widths = [] if pipettes is None else [c.width for c in pipettes.configuration.channels]
    if pipettes is not None and not any(w is None for w in widths):
      floor = cast(DeviceConfiguration, self.device.configuration).left_arm_min_y_position
      await pipettes.update_locations_by_reference_point(
        {
          channel: (floor + sum(cast(List[float], widths[channel + 1 :])), None)
          for channel in range(len(widths))
        }
      )
    return await super()._unchecked_fw_position_components_for_free_y_range()

  async def request_firmware_version(self) -> Tuple[str, datetime.date]:
    await self.recorded("R0", "RF")
    version = self._declared.firmware_version
    if version is None:
      raise RuntimeError("the simulated iSWAP has no firmware version declared")
    return version, parse_firmware_version_date(version)

  @property
  def _declared(self) -> iSWAPConfiguration:
    """The iSWAP this device was told it has.

    Distinct from `configuration`, which discovery fills from these answers exactly as it would
    off an device.
    """
    return self.device.simulated_iswap

  async def _request_slots(self, table: str) -> List[int]:
    # Rendered from what this iSWAP is, rather than written out separately: discovery reads these
    # tables back into the stops and link lengths, so an iSWAP configured differently answers
    # differently. Each table carries its drive's stops, then that link's length in tenths.
    declared = self._declared
    stops: Any
    if table == "py":
      stops, length = declared.elbow_predefined_y_positions_increments, None
    elif table == "pz":
      stops, length = declared.elbow_predefined_z_positions_increments, None
    elif table == "pg":
      stops, length = declared.gripper_drive_predefined_increments, None
    elif table == "pw":
      stops, length = declared.elbow_drive_predefined_increments, declared.link_1_length
    else:
      stops, length = declared.wrist_drive_predefined_increments, declared.tool_length
    if stops is None:
      raise RuntimeError(f"the simulated iSWAP has no {table} table; set it on its configuration")
    rendered = list(dataclasses.astuple(stops))
    return rendered if length is None else rendered + [round(length * 10)]

  async def initialize(self):
    """Goes through the command path, so it is coordinated like the real one."""
    await super().initialize()
    self.device.initialized["R0"] = True


class SimulatedFrontCover(_Simulated, FrontCover):
  """The front cover, answering for itself: it is shut."""

  async def answer(self, module: str, command: str, **kwargs: Any) -> Optional[Tuple[Any, str]]:
    if (module, command) == ("C0", "QC"):
      codes = self.configuration.position_codes
      return {"qc": codes[SIMULATED_COVER_POSITION]}, "the cover it is simulated at"
    return None


class SimulatedAutoload(_Simulated, Autoload):
  """The autoload, answering for itself. Its deck and its loading tray are empty."""

  async def _track_x(self, track: int) -> float:
    """Where a track starts along the deck, in mm."""
    return (await cast(handles.Deck, self.device.deck).track_location(track)).x

  async def _modelled_track(self) -> int:
    """Which track the sled is modelled on.

    Worked out from where the model has it rather than kept alongside: the sled's resource is
    what moves, and a track is a place on the deck. The nearest track to where it sits is the one
    it is on, since a move puts it on one exactly. Before setup has placed it there is nothing to
    read, and it answers the track it homes against.

    Returns:
      The track, counted from 1.
    """
    x = await self.get_reference_point_x()
    if x is None:
      # Nothing models it yet, so where an initialized autoload leaves it: parked, at the last
      # track. Initialization parks the sled and only then is the model built from what this
      # answers, so answering the first track puts the sled at the wrong end of the deck.
      return self.track_range[-1]
    tracks = await cast(handles.Deck, self.device.deck).get_hamilton_tracks()
    origin = to_coordinate(tracks.track_origin)
    starts = {
      t: (origin + Coordinate((t - 1) * tracks.track_pitch, 0, 0)).x for t in self.track_range
    }
    return min(self.track_range, key=lambda t: abs(starts[t] - x))

  async def answer(self, module: str, command: str, **kwargs: Any) -> Optional[Tuple[Any, str]]:
    declared = self.device.simulated_autoload
    c = self.configuration

    if module == "C0":
      if command == "CQ":
        autoload_type = declared.autoload_type
        if autoload_type is None:
          raise RuntimeError("the simulated autoload has no type; set it on its configuration")
        code = next((k for k, name in AUTOLOAD_TYPES.items() if name == autoload_type), None)
        if code is None:
          raise RuntimeError(f"{autoload_type!r} is not a type the autoload reports")
        return {"cq": code}, "the autoload it was declared to be"
      if command == "QA":
        return {"qa": await self._modelled_track()}, "the track the sled is modelled on"
      return None

    if module != "I0":
      return None

    if command == "QW":
      return {"qw": int(self.device.initialized["I0"])}, "whether it has been initialized"

    if command == "QX":
      if declared.initialization_track is None:
        raise RuntimeError(
          "the simulated autoload has no initialization_track; set it on its configuration"
        )
      return {"bx": declared.initialization_track}, "the track it was declared to home against"

    if command == "RJ":
      if declared.adjustment_date is None or declared.adjusted is None:
        raise RuntimeError(
          "the simulated autoload does not say whether it is adjusted; set adjustment_date and "
          "adjusted on its configuration"
        )
      return (
        {"jd": declared.adjustment_date.isoformat(), "js": int(declared.adjusted)},
        "the adjustment it was declared with",
      )

    if command == "RA":
      parameter = cast(str, kwargs.get("ra"))
      if parameter == "au":
        # What this device's own autoload answered: the 0.1 mm scanner, indicators fitted.
        return (
          {"au": [0 if declared.x_drive_mm_per_increment == 0.1 else 1, 0, 0, 0, 0]},
          "the module configuration it was declared with",
        )
      return (
        f"I0RA{parameter}{SIMULATED_AUTOLOAD_PARAMETER_VALUE}",
        f"the {parameter} parameter it stores",
      )

    # The drives answer twice, the firmware counter then the hardware one, and the read takes the
    # second. Where each is is what the model says: a simulated device has no drive to ask.
    if command == "RX":
      # The model is placed around the carrier-handling wheel, so the wheel stands that far right
      # of its left edge. Before setup has put the sled on the deck there is no model to read, and
      # the track it is on is what it has instead - which is how a park during initialization
      # survives long enough to reach the resource created after it.
      modelled = await self.get_reference_point_x()
      x = modelled if modelled is not None else await self._track_x(await self._modelled_track())
      # The X drive is the one drive here that does not count in the deck's coordinates, so the
      # deck position the model holds is put back into the drive's frame before it is encoded.
      # Answered in the deck's, the read comes back a drive zero too far right - past the end of
      # the drive's own travel, so the next absolute move is refused.
      increments = c.x_drive_mm_to_increments(c.from_deck_frame(x))
      return {"rx": [increments, increments]}, "where the sled is modelled"
    if command == "RS":
      # Nothing models which way the scanner faces, and the drive has a code for exactly that: it
      # sits at neither of its two stops. Answering one of them would be inventing a facing.
      return {"rs": c.scanner_rotations["undefined"]}, "no modelled scanner facing"
    if command == "RY":
      increments = c.y_drive_mm_to_increments(SIMULATED_AUTOLOAD_Y_POSITION)
      return {"ry": [increments, increments]}, "where the wheel is modelled along Y"
    if command == "RZ":
      increments = c.z_drive_mm_to_increments(SIMULATED_AUTOLOAD_Z_POSITION)
      return {"rz": [increments, increments]}, "where the wheel is modelled along Z"
    return None

  async def request_firmware_version(self) -> Tuple[str, datetime.date]:
    await self.recorded("I0", "RF")
    version = self.device.simulated_autoload.firmware_version
    if version is None:
      raise RuntimeError(
        "the simulated autoload has no firmware version; set it on its configuration"
      )
    return version, parse_firmware_version_date(version)

  async def request_adjustment_values(self) -> str:
    """Answer the adjustment block, which a simulated unit does not hold."""
    await self.recorded("I0", "RK")
    return SIMULATED_AUTOLOAD_ADJUSTMENT_VALUES

  async def request_parameter(self, parameter: str) -> str:
    """Answer a stored parameter by name.

    Args:
      parameter: the name to read.

    Returns:
      What the module holds for it.
    """
    await self.recorded("I0", "RA", ra=parameter)
    return SIMULATED_AUTOLOAD_PARAMETER_VALUE

  async def request_latest_barcode_read(self) -> Optional[str]:
    await self.recorded("I0", "RB")
    return SIMULATED_BARCODE

  async def _carrier_tracks(self) -> List[int]:
    """Which tracks hold a carrier, from the deck rather than from a sensor.

    A simulated device has no sensor to read, so what is on the deck is what the resource model
    says is on it. Each carrier is reported by the track its right rail sits over, which is the
    track every autoload command addresses it by.
    """
    deck = self.device.deck
    if deck is None:
      return []
    carriers = await deck.get_children(handles.Carrier)
    return sorted([(await deck.tracks_of(carrier))[1] for carrier in carriers])

  async def sense_carrier_presence_on_deck(self) -> List[int]:
    await self.recorded("C0", "RC")
    return await self._carrier_tracks()

  async def sense_carrier_presence_on_loading_tray(self) -> List[int]:
    # Nothing is on the tray: a carrier the model holds is on the deck, which is where it was
    # assigned. Moving one there is a move, and moves are modelled where they happen.
    await self.recorded("C0", "CS", subsystem="I0")
    return []

  async def sense_carrier_presence_on_single_loading_tray_track(
    self, track: int, park_after: bool = True
  ) -> bool:
    await self.recorded("C0", "CT", subsystem="I0", cp=f"{track:02}")
    return False

  async def move_to_x_position(
    self,
    x: float,
    speed: Optional[float] = None,
    acceleration_ramp: Optional[int] = None,
    current_limit: Optional[int] = None,
  ) -> Any:
    # A simulated drive goes exactly where it is told. The real one is read back afterwards, which
    # is what `Autoload` relies on, so the position has to be true here before that read happens or
    # the read returns the position the sled started at and it never moves.
    resp = await super().move_to_x_position(
      x, speed=speed, acceleration_ramp=acceleration_ramp, current_limit=current_limit
    )
    await self.update_location_by_reference_point(x)
    return resp

  async def load_carrier_from_tray_and_scan_carrier_barcode(
    self, track: int, *args, **kwargs
  ) -> Optional[str]:
    return SIMULATED_BARCODE

  async def load_carrier_from_autoload_belt(
    self, barcode_reading: bool = False, *args, **kwargs
  ) -> Dict[int, Optional[str]]:
    """The containers read nothing, and there are as many as were asked for."""
    if not barcode_reading:
      return {}
    containers = kwargs.get("containers_per_carrier", 5)
    return {position: SIMULATED_BARCODE for position in range(containers)}

  async def initialize(self, park_after: bool = True):
    await super().initialize(park_after=park_after)
    self.device.initialized["I0"] = True

  async def move_to_track(self, track: int, *args, **kwargs):
    # As `move_to_x_position` records where a position move put the sled, so this records where a
    # track move did. The deck is what knows where a track is.
    await super().move_to_track(track, *args, **kwargs)
    # A simulated device refuses to set up without a deck, so there is one.
    await self.update_location_by_reference_point(await self._track_x(track))


class SimulatedCoreGrippers(_Simulated, CoreGrippers):
  """The CoRe grippers, recording where each command leaves the arm and the two channels.

  A command is recorded as `SimulatedPipettes._record_tip_command` records a tip command: across
  at the height it starts from, down to where it works, and up to where it ends, each stop charged
  the time the drives would take. The reads that follow every command then find the channels there.
  """

  @property
  def _simulated_pipettes(self) -> SimulatedPipettes:
    return cast(SimulatedPipettes, self._pipettes)

  async def _tool_overhang(self) -> float:
    """How far a tool will hang below a channel's stop disc to its grip line once taken, in mm.

    Measured off a tool on the deck, as `SimulatedPipettes._below_stop_discs` measures one on a
    channel. Nothing when no tool is on the deck to measure.
    """
    deck = self._driver.deck
    if deck is None:
      return 0.0
    response = await deck.server.commands.find_resources(
      spb.FindResourcesRequest(
        scope=deck.ref,
        filter=spb.ResourceFilter(kinds=[pb.RESOURCE_KIND_HEAD_TOOL]),
      )
    )
    for node in response.nodes:
      tool = node.attributes
      if resource_model.grips(tool):
        return tool.size.z - tool.head_tool.fitting_depth - resource_model.grip_line_height(tool)
    return 0.0

  async def _record_pair(
    self,
    pair: Tuple[Optional[int], Optional[int]],
    x_position: int,
    back_channel_y: int,
    front_channel_y: int,
    z: int,
    descend_to: Optional[int] = None,
    overhang: Optional[float] = None,
  ) -> None:
    """Record a command that moves the back and front channel, in tenths of a millimetre.

    Nothing is recorded without a pair: a command sent without the tools taken names no channels
    to put anywhere.

    Args:
      pair: the back and front channel, 0-indexed.
      x_position: where the arm ends.
      back_channel_y: where the back channel ends along Y.
      front_channel_y: where the front channel ends along Y.
      z: the height the command ends at, measured at the grip line when tools are carried.
      descend_to: the lowest point of the stroke. Only the end is recorded when it is None.
      overhang: how far what the channels carry at the end hangs below the stop disc, in mm. What
        the front channel carries now when None.
    """
    back, front = pair
    if back is None or front is None:
      return
    pipettes = self._simulated_pipettes
    if overhang is None:
      overhang = await pipettes._below_stop_disc(front)
    channels = pipettes.num_channels
    ys = [0] * channels
    ys[back], ys[front] = back_channel_y, front_channel_y
    await pipettes._record_tip_command(
      x_positions=[x_position] * channels,
      y_positions=ys,
      tip_pattern=[channel in (back, front) for channel in range(channels)],
      z=z,
      overhang=overhang,
      descend_to=descend_to,
    )

  @staticmethod
  def _held_pair_ys(y_position: int, width: int) -> Tuple[int, int]:
    """The back and front channel's Y either side of a held plate's centre, a jaw width apart.

    Args:
      y_position: the plate's centre along Y, in tenths of a millimetre.
      width: how far apart the jaws stand, in tenths of a millimetre.
    """
    return y_position + width // 2, y_position - width // 2

  async def _unchecked_fw_pick_up_tools(
    self,
    x_position: int,
    back_channel_y: int,
    front_channel_y: int,
    begin_z: int,
    end_z: int,
    minimum_traverse_height_start: int,
    back_channel: int,
    front_channel: int,
    tip_type_index: int,
  ):
    resp = await super()._unchecked_fw_pick_up_tools(
      x_position,
      back_channel_y,
      front_channel_y,
      begin_z,
      end_z,
      minimum_traverse_height_start,
      back_channel,
      front_channel,
      tip_type_index,
    )
    await self._record_pair(
      (back_channel, front_channel),
      x_position,
      back_channel_y,
      front_channel_y,
      minimum_traverse_height_start,
      overhang=await self._tool_overhang(),
      descend_to=end_z,
    )
    return resp

  async def _unchecked_fw_drop_tools(
    self,
    x_position: int,
    back_channel_y: int,
    front_channel_y: int,
    begin_z: int,
    end_z: int,
    minimum_traverse_height_start: int,
    minimum_traverse_height_end: int,
  ):
    resp = await super()._unchecked_fw_drop_tools(
      x_position,
      back_channel_y,
      front_channel_y,
      begin_z,
      end_z,
      minimum_traverse_height_start,
      minimum_traverse_height_end,
    )
    await self._record_pair(
      (self._back_channel, self._front_channel),
      x_position,
      back_channel_y,
      front_channel_y,
      minimum_traverse_height_end,
      overhang=0.0,
      descend_to=end_z,
    )
    return resp

  async def _unchecked_fw_pick_up_resource(
    self,
    x_position: int,
    y_position: int,
    y_gripping_speed: int,
    z_position: int,
    z_speed: int,
    open_gripper_position: int,
    plate_width: int,
    grip_strength: int,
    minimum_traverse_height_start: int,
    minimum_z_position_end: int,
  ):
    resp = await super()._unchecked_fw_pick_up_resource(
      x_position,
      y_position,
      y_gripping_speed,
      z_position,
      z_speed,
      open_gripper_position,
      plate_width,
      grip_strength,
      minimum_traverse_height_start,
      minimum_z_position_end,
    )
    back_y, front_y = self._held_pair_ys(y_position, plate_width)
    await self._record_pair(
      (self._back_channel, self._front_channel),
      x_position,
      back_y,
      front_y,
      minimum_z_position_end,
      descend_to=z_position,
    )
    return resp

  async def _unchecked_fw_place_resource(
    self,
    x_position: int,
    y_position: int,
    z_position: int,
    press_on_distance: int,
    z_speed: int,
    open_gripper_position: int,
    minimum_traverse_height_start: int,
    minimum_z_position_end: int,
    x_acceleration_level: Optional[int] = None,
  ):
    resp = await super()._unchecked_fw_place_resource(
      x_position,
      y_position,
      z_position,
      press_on_distance,
      z_speed,
      open_gripper_position,
      minimum_traverse_height_start,
      minimum_z_position_end,
      x_acceleration_level,
    )
    back_y, front_y = self._held_pair_ys(y_position, open_gripper_position)
    await self._record_pair(
      (self._back_channel, self._front_channel),
      x_position,
      back_y,
      front_y,
      minimum_z_position_end,
      descend_to=z_position,
    )
    return resp

  async def _unchecked_fw_move_resource(
    self,
    x_position: int,
    x_acceleration_level: int,
    y_position: int,
    z_position: int,
    z_speed: int,
    minimum_traverse_height_start: int,
  ):
    resp = await super()._unchecked_fw_move_resource(
      x_position,
      x_acceleration_level,
      y_position,
      z_position,
      z_speed,
      minimum_traverse_height_start,
    )
    back, front = self._back_channel, self._front_channel
    if back is None or front is None:
      return resp
    # Carried as held: the jaws stay as far apart as the grip left them.
    pipettes = self._simulated_pipettes
    ys = await pipettes._modelled_ys()
    width = round((ys[back] - ys[front]) * 10)
    back_y, front_y = self._held_pair_ys(y_position, width)
    await self._record_pair((back, front), x_position, back_y, front_y, z_position)
    return resp


class STARSimulationDriver(STARDriver):
  """A simulated STAR, driven exactly like the real one."""

  def __init__(
    self,
    tips_mounted: Optional[List[bool]] = None,
    simulate_motion_time: bool = False,
    motion_time_scale: float = 0.25,
    deck: Optional[handles.Deck] = None,
    initialized: bool = False,
    left_side_panel_installed: bool = False,
    declared_configuration_json: Optional[str] = None,
  ):
    """
    Args:
      tips_mounted: one entry per channel, `True` where a tip sits on the channel. Defaults to no
        tips on any of them.
      simulate_motion_time: whether a command that moves the channels takes the time the drives
        would take, so a run can be followed rather than being over at once.
      motion_time_scale: the share of that time a move takes when it does.
      deck: the deck to reflect this device into. Needed by setup: a simulated device has no
        firmware to ask, so the resource model is the only thing it can answer from. A device
        gives its driver its deck when it makes its resources.
      initialized: whether the device and its modules report themselves already initialized. One
        that has just been switched on does not.
      left_side_panel_installed: whether this device has its left side panel on. Declared rather
        than discovered, as on a real one: the panel comes off in seconds.
      declared_configuration_json: path to a declared configuration, which this device then answers
        as. What the arguments above name takes precedence over it, and what neither names falls
        back to what this frame documents.

    Raises:
      ValueError: If `tips_mounted` does not have one entry per channel.
    """
    super().__init__(
      io=_UnusedTransport(),
      deck=deck,
      left_side_panel_installed=left_side_panel_installed,
      declared_configuration_json=declared_configuration_json,
    )

    # What the declaration says this device carries, whichever arm carries it. A simulated device
    # stands in for one of each, so the same feature on two arms is refused rather than half-read.
    carried: Dict[str, Any] = {}
    for side, features in self.declared.get("arms", {}).items():
      for name, feature in features.items():
        if name in carried:
          raise ValueError(
            f"the declared configuration has a {name} on more than one arm; a simulated device "
            f"stands in for one of each, so it cannot answer as this one (seen again on {side})"
          )
        carried[name] = feature

    configuration = self.declared.get("device")
    if configuration is None:
      raise ValueError(
        "a simulated device has to be told what it is simulating: pass "
        "`declared_configuration_json`, naming a file that records one"
      )
    self.simulated_configuration: DeviceConfiguration = configuration

    self.simulated_autoload: AutoloadConfiguration = (
      self.declared.get("autoload") or AutoloadConfiguration()
    )
    self.simulated_head96: Head96Configuration = carried.get("head96") or Head96Configuration()
    self.simulated_head384: Head384Configuration = carried.get("head384") or Head384Configuration()
    self.simulated_pipettes: Optional[PipettesConfiguration] = carried.get("pipettes")
    self.simulated_iswap: iSWAPConfiguration = carried.get("iswap") or iSWAPConfiguration()

    channels = self.simulated_configuration.num_pip_channels
    if tips_mounted is None:
      tips_mounted = [False] * channels
    if len(tips_mounted) != channels:
      raise ValueError(f"tips_mounted has {len(tips_mounted)} entries, expected {channels}")
    self.tips_mounted = list(tips_mounted)
    self.simulate_motion_time = simulate_motion_time
    self.motion_time_scale = motion_time_scale
    # What the drives would still be doing, in seconds: the longest move recorded since the last
    # command, waited out before the next one goes.
    self._motion_owed = 0.0
    # How far a tip of each defined type stands below the stop disc, by tip type index, as
    # `define_tip_needle` was told. A tip command names one of these, and what it collects hangs
    # that far down: the traverse height it ends at is the tip's, so the stop disc ends higher.
    self.defined_tip_lengths: Dict[int, float] = {}
    # What each channel's drive holds, by channel; filled from the power-on values when first asked.
    self.channel_drive_parameters: Dict[int, Dict[str, int]] = {}
    # What each channel is searching for liquid in while a batch search runs, by channel. A search
    # is answered from that container's tracker; without one, from whatever stands under the tip.
    self.liquid_searches: Dict[int, handles.Container] = {}
    # What each channel last detected liquid at, in mm on the deck; 0.0 until a search finds any.
    self.last_lld_heights: Dict[int, float] = {}
    # Where each channel's piston stands, in uL: what its aspirations drew.
    self.dispensing_drive_uL: Dict[int, float] = {}
    # TADM, by channel: whether its monitoring is on (`BG` to `BH`), the curves its strokes
    # recorded and not yet read, oldest first, and the one `QM` last moved the pointer to. A
    # curve is its operation (0 aspirate, 1 dispense) and its pressures.
    self.tadm_monitoring: Dict[int, bool] = {}
    self.tadm_fifo: Dict[int, List[Tuple[int, List[int]]]] = {}
    self.tadm_pointer: Dict[int, Optional[Tuple[int, List[int]]]] = {}
    # The transport air each channel's tip holds, in uL: the next dispense pushes it out first.
    self.transport_air_uL: Dict[int, float] = {}
    # Where the 96-head's stop disc last detected liquid, in mm on the deck; 0.0 until one does.
    self.head96_last_lld_z: float = 0.0
    # Where the 96-head's piston stands, in uL: what its strokes drew.
    self.head96_dispensing_drive_uL: float = 0.0

    # What each module says when asked whether it is initialized, and where things are.
    self.initialized = {module: initialized for module in ("C0", "I0", "R0", "H0")}

    # The features this device has, each answering for itself. Discovery builds only the ones
    # that are not already there, so these stand in for the real ones throughout.
    c = self.simulated_configuration
    if c.main_front_cover_monitoring_installed:
      self.front_cover = SimulatedFrontCover(self)
    if c.left_arm is not None:
      self.left_x_arm = SimulatedXArm(self, side="left")
    if c.right_arm is not None:
      self.right_x_arm = SimulatedXArm(self, side="right")
    if c.autoload_installed:
      self.autoload = SimulatedAutoload(self)

    # On the arm whose bits claim them, as discovery would put them. Read off the simulated
    # configuration rather than the arm's own: nothing has been discovered yet at this point.
    for arm, a in ((self.left_x_arm, c.left_arm), (self.right_x_arm, c.right_arm)):
      if arm is None or a is None:
        continue
      if a.pip_installed and c.num_pip_channels > 0:
        arm.pipettes = SimulatedPipettes(self)
        # Two channels carry the tools, as discovery builds them.
        if c.num_pip_channels >= 2:
          arm.core_grippers = SimulatedCoreGrippers(self)
      if a.head96_installed:
        arm.head96 = SimulatedHead96(self)
      if a.head384_installed:
        arm.head384 = SimulatedHead384(self)
      if a.iswap_installed:
        arm.iswap = SimulatedISWAP(self)

  # -- the device itself ----------------------------------------------------

  async def setup(self, *args: Any, **kwargs: Any):
    """Set up as the real driver does, once there is a deck to answer from.

    Raises:
      ValueError: If the driver has no deck.
    """
    if self.deck is None:
      raise ValueError("a simulated STAR answers from its resource model, so it needs a deck")
    await super().setup(*args, **kwargs)

  async def _open(self):
    """There is no link to open, and no replies to read."""

  async def _close(self):
    pass

  async def define_tip_needle(self, *args: Any, **kwargs: Any):
    """Remember how far a tip of this type hangs below the stop disc, then define it as usual.

    A tip command names a type rather than a tip, so this is where the model learns what a channel
    collecting that type will carry: `_record_tip_command` puts the stop disc that much above the
    traverse height the command ends at.
    """
    resp = await super().define_tip_needle(*args, **kwargs)
    index, length = kwargs.get("tip_type_table_index"), kwargs.get("tip_length")
    if index is not None and length is not None:
      self.defined_tip_lengths[int(index)] = float(length)
    return resp

  async def request_device_configuration(self) -> DeviceConfiguration:
    """What the device reports it carries, answered from what it was declared to be.

    As the channels answer: the reads a device answers this with go on the link, and what comes back
    is a configuration of its own rather than the declared one, so discovery records it and the
    cross-check compares the two as it does on a physical device. An arm keeps the device facts
    written to it across a re-read, as a physical device's discovery keeps them.
    """
    for command in ("RM", "QM", "RU", "UA"):
      await self.send_command(module="C0", command=command)
    answered = copy.deepcopy(self.simulated_configuration)
    if self.configuration is not None:
      for side in ("left_arm", "right_arm"):
        carried, arm = getattr(self.configuration, side), getattr(answered, side)
        if carried is not None and arm is not None:
          setattr(answered, side, arm.with_device_facts_of(carried))
    return answered

  async def request_cover_input_status(self) -> Tuple[bool, bool, bool]:
    return SIMULATED_COVER_INPUTS

  async def request_device_serial_number(self) -> str:
    await self.send_command(module="C0", command="RI")
    # What it was told it is, or what it was told to call itself when the recording did not say.
    declared = self.simulated_configuration.serial_number
    if declared is None:
      raise RuntimeError("the simulated device has no serial number; set it on its configuration")
    return declared

  async def request_firmware_version(self) -> Tuple[str, datetime.date]:
    await self.send_command(module="C0", command="RF")
    declared = self.simulated_configuration.firmware_version
    if declared is None:
      raise RuntimeError(
        "the simulated device has no firmware version; set it on its configuration"
      )
    return declared, parse_firmware_version_date(declared)

  async def request_initialization_status(self, module: str = "C0") -> bool:
    return self.initialized.get(module, False)

  async def _pre_initialize(self, read_timeout: int = 300):
    """Home every drive. The modules it de-initializes then need their own.

    Goes through the command path, so it is coordinated like the real one.

    Args:
      read_timeout: how long the real procedure would be given, in seconds. Nothing waits here.
    """
    await super()._pre_initialize(read_timeout=read_timeout)
    self.initialized["C0"] = True

  async def pay_motion_time(self) -> None:
    """Wait out what the moves recorded since the last wait would have taken. Nothing owed, nothing
    waited, so this costs nothing on a device that is not keeping time."""
    owed, self._motion_owed = self._motion_owed, 0.0
    if owed:
      await asyncio.sleep(owed * self.motion_time_scale)

  def owe_motion_time(self, *seconds: float) -> None:
    """Charge the device for a move, in seconds. The longest one owed stands: the drives move at
    once, so a command takes as long as its slowest axis."""
    self._motion_owed = max(self._motion_owed, *seconds)

  def _describe_link(self) -> str:
    return "simulation (no link)"

  async def _answer(self, module: str, command: str, **kwargs: Any) -> Optional[Tuple[Any, str]]:
    """What the device would answer, asked of the feature the command is about.

    Each feature answers for its own model, so the logic stays where the model is; this only
    decides who is asked. A command addressed to a module names its feature; one addressed to C0
    does not, so every feature is offered it and the first that answers has it.

    Args:
      module: the module the command was addressed to.
      command: the two-letter command code.
      kwargs: the command's own parameters, for the reads that vary by one.

    Returns:
      The answer and where it came from, or None when nothing here answers - every command that
      only moves.
    """
    for feature in self._simulated_features():
      answered = await feature.answer(module, command, **kwargs)
      if answered is not None:
        return answered
    return None

  def _simulated_features(self) -> List[_Simulated]:
    """Every feature that can answer for itself, arms first."""
    candidates: List[Any] = []
    for arm in self.arms:
      candidates += [arm, arm.pipettes, arm.head96, arm.head384, arm.iswap]
    candidates += [self.autoload, self.front_cover]
    return [feature for feature in candidates if isinstance(feature, _Simulated)]

  async def _send(
    self,
    module: str,
    command: str,
    auto_id=True,
    tip_pattern: Optional[List[bool]] = None,
    write_timeout: Optional[int] = None,
    read_timeout: Optional[int] = None,
    fmt: Optional[Any] = None,
    **kwargs: Any,
  ) -> Any:
    """Say what would have been sent, and answer from the model where there is an answer.

    A command that only moves is logged and answered with nothing. One whose answer is read is
    logged the same way and then answered by `_answer`, so a read puts its command on the link
    exactly as a move does.

    What it logs is what a real link logs: the assembled command as a write, and the answer as a
    read, so a simulated run reads like a recorded one.

    Replacing `_send` rather than `send_command` leaves the coordination in place, so a simulated
    run serializes what a real one serializes.
    """
    # The count is only read when there is a list to terminate, as the real assembler reads it:
    # discovery sends commands before it knows the count, and asking for it there would refuse
    # the very reads that establish it.
    carries_a_list = any(isinstance(value, list) for value in kwargs.values())
    cmd = assemble_channel_command(
      module=module,
      command=command,
      id_=None,
      tip_pattern=tip_pattern,
      num_channels=self.num_channels if carries_a_list else 0,
      **kwargs,
    )
    await self.pay_motion_time()
    answered = await self._answer(module, command, **kwargs)
    if answered is None:
      self._log_exchange(cmd, None)
      return None
    value, source = answered
    self._log_exchange(cmd, f"simulation: {value} from model {source}")
    return value

  async def send_raw_command(self, command: str, *args: Any, **kwargs: Any) -> None:
    self._log_exchange(command, None)
    return None

  def _log_exchange(self, written: str, read: Optional[str]) -> None:
    """Log a command, and its answer where there is one, as the transport logs a real exchange.

    Nothing answers in simulation unless a feature says so, so most commands log a write alone.
    """
    logger.log(LOG_LEVEL_IO, "%s write: %s", SIMULATED_LINK, written)
    if read is not None:
      logger.log(LOG_LEVEL_IO, "%s read: %s", SIMULATED_LINK, read)
