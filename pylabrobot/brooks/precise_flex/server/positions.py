"""Taught positions, and carrying plates between them: `PositionsService` (`v1/positions.proto`).

A position is a name the server keeps with a joint state: the Z column, shoulder, elbow and wrist,
and the rail on an arm with one. They are kept in a JSON file, a `ListResponse` message, written
whole each time one is taught or forgotten, and read when the server starts.

A position is where a plate sits: taught with the gripper's tool point at the plate's bottom. A
grip says how to hold the plate: the jaws close `height` above the position, `width` apart, and the
arm approaches and leaves from `plate_height` above that. Every visit starts and ends folded in the
parking pose, and the rail moves only then. A carry is made of the arm's own calls, the ones the
other services serve: `park`, `move_rail`, `move_to_joint_state`, `pick_up_at_joint_state` and
`drop_at_joint_state`.

A carry streams its progress every few seconds, so nothing between the server and a client sees an
idle call and cuts it. It runs on the server: it finishes even if the client goes away.
"""

import asyncio
import os
import tempfile
import time
from typing import TYPE_CHECKING, Any, AsyncIterator, Awaitable, Callable, Dict, Optional

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext
from google.protobuf import json_format

from pylabrobot.brooks.precise_flex.kinematics import JointState, PreciseFlexAxis
from pylabrobot.brooks.precise_flex.server import wire
from pylabrobot.brooks.precise_flex.server.errors import to_connect_error
from pylabrobot.brooks.precise_flex.server.v1 import positions_pb2 as ppb
from pylabrobot.brooks.precise_flex.server.v1 import types_pb2 as tpb
from pylabrobot.brooks.precise_flex.server.v1.positions_connect import (
  PositionsServiceASGIApplication,
)

if TYPE_CHECKING:
  from pylabrobot.brooks.precise_flex.server.serve import ASGIApp, Served

Ctx = RequestContext[Any, Any]

# How often a carry says how far it has got, in seconds.
PROGRESS_INTERVAL = 5.0

# The axes a position keeps, besides the rail: the jaws are the grip's.
POSITION_AXES = (
  PreciseFlexAxis.BASE,
  PreciseFlexAxis.SHOULDER,
  PreciseFlexAxis.ELBOW,
  PreciseFlexAxis.WRIST,
)


def read_positions(path: str) -> Dict[str, ppb.Position]:
  """The positions in a JSON file, by name. A file that is not there holds none.

  Raises:
    ValueError: If the file is not a `ListResponse`, or a position lacks an axis it needs.
  """
  if not os.path.exists(path):
    return {}
  with open(path, encoding="utf-8") as f:
    text = f.read()
  try:
    saved = json_format.Parse(text, ppb.ListResponse())
  except json_format.ParseError as error:
    raise ValueError(f"{path} is not a PreciseFlex server's positions: {error}") from error
  for position in saved.positions:
    missing = [axis.name for axis in POSITION_AXES if axis not in _joints(position)]
    if missing:
      raise ValueError(f"position '{position.name}' in {path} has no {', '.join(missing)}")
  return {position.name: position for position in saved.positions}


def write_positions(path: str, positions: Dict[str, ppb.Position]) -> None:
  """Write the positions to a JSON file whole, replacing it only once every byte is down."""
  saved = ppb.ListResponse(positions=[positions[name] for name in sorted(positions)])
  text = json_format.MessageToJson(saved, preserving_proto_field_name=True, indent=2)
  directory = os.path.dirname(os.path.abspath(path))
  fd, temporary = tempfile.mkstemp(prefix=".positions-", suffix=".json", dir=directory)
  try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
      f.write(text + "\n")
      f.flush()
      os.fsync(f.fileno())
    os.replace(temporary, path)
  except BaseException:
    os.unlink(temporary)
    raise


def _joints(position: ppb.Position) -> JointState:
  return wire.joint_state_from(position.joint_state)


class Positions:
  """The positions a server keeps, in its file first when it has one."""

  def __init__(self, path: Optional[str]):
    self.path = path
    self.by_name: Dict[str, ppb.Position] = read_positions(path) if path is not None else {}

  def get(self, name: str) -> ppb.Position:
    position = self.by_name.get(name)
    if position is None:
      raise ConnectError(Code.NOT_FOUND, f"no position is named '{name}'")
    return position

  def _keep(self, positions: Dict[str, ppb.Position]) -> None:
    if self.path is not None:
      write_positions(self.path, positions)
    self.by_name = positions

  def teach(self, position: ppb.Position) -> None:
    self._keep({**self.by_name, position.name: position})

  def forget(self, name: str) -> None:
    self.get(name)
    self._keep({n: p for n, p in self.by_name.items() if n != name})


def _check_grip(grip: ppb.Grip) -> None:
  """
  Raises:
    ValueError: If the width or the plate's height is not above 0, or the height is below 0.
  """
  if grip.width <= 0:
    raise ValueError(f"a grip's width is above 0 mm, not {grip.width}")
  if grip.height < 0:
    raise ValueError(f"a grip's height is 0 mm or more, not {grip.height}")
  if grip.plate_height <= 0:
    raise ValueError(f"a grip's plate_height is above 0 mm, not {grip.plate_height}")


class PositionsHandlers:
  """PositionsService, on a served device."""

  def __init__(self, served: "Served"):
    self._served = served

  @property
  def _device(self) -> Any:
    return self._served.device

  def _rail_of(self, position: ppb.Position) -> Optional[float]:
    """The rail position to go to for a position; None on an arm with no rail.

    Raises:
      ValueError: If the position was taught with a rail and the arm has none, or the other way.
    """
    on_rail = self._device.rail is not None
    taught_on_rail = position.joint_state.HasField("rail")
    if on_rail and not taught_on_rail:
      raise ValueError(f"position '{position.name}' was taught without a rail, and the arm has one")
    if not on_rail and taught_on_rail:
      raise ValueError(f"position '{position.name}' was taught on a rail, and the arm has none")
    return position.joint_state.rail if on_rail else None

  # -- carrying --

  async def _visit(
    self,
    position: ppb.Position,
    grip: ppb.Grip,
    act: Callable[[JointState], Awaitable[None]],
    say: Callable[[str], None],
    verb: str,
  ) -> None:
    """Go folded to a position's rail position, down to where the grip holds a plate there, `act`
    there, and back up and folded."""
    arm = self._device.arm
    at = _joints(position)
    station = {axis: at[axis] for axis in POSITION_AXES}
    station[PreciseFlexAxis.BASE] += grip.height
    above = {**station, PreciseFlexAxis.BASE: station[PreciseFlexAxis.BASE] + grip.plate_height}
    rail = self._rail_of(position)
    say("park")
    await arm.park()
    if rail is not None:
      say("rail")
      await self._device.rail.move_rail(rail)
    say("approach")
    await arm.move_to_joint_state(above)
    say(verb)
    # The controller approaches and leaves the station by this much itself.
    clearance = arm.station_z_clearance
    arm.station_z_clearance = grip.plate_height
    try:
      await act(station)
    finally:
      arm.station_z_clearance = clearance
    say("leave")
    await arm.move_to_joint_state(above)
    say("park")
    await arm.park()

  async def _carry(
    self, source: ppb.Position, target: ppb.Position, grip: ppb.Grip, say: Callable[[str], None]
  ) -> None:
    served, device = self._served, self._device

    async def pick_up(station: JointState) -> None:
      await device.arm.pick_up_at_joint_state(station, resource_width=grip.width)
      served.holding = not await device.gripper.sense_fully_closed()
      if not served.holding:
        raise RuntimeError(f"the arm closed its jaws on nothing at '{source.name}'")

    async def drop(station: JointState) -> None:
      await device.arm.drop_at_joint_state(station, resource_width=grip.width)
      served.holding = False

    async with served.motion:
      try:
        await self._visit(source, grip, pick_up, say, "pick up")
        await self._visit(target, grip, drop, say, "drop")
      finally:
        await served._record_quietly()

  def carry(self, request: ppb.CarryRequest, ctx: Ctx) -> AsyncIterator[tpb.Progress]:
    served = self._served
    try:
      source = served.positions.get(request.from_position)
      target = served.positions.get(request.to_position)
      _check_grip(request.grip)
      self._rail_of(source)
      self._rail_of(target)
      served.require_set_up()
      if served.holding:
        raise RuntimeError("the arm already holds a plate: drop it first")
    except Exception as error:
      raise to_connect_error(error) from error
    grip = ppb.Grip()
    grip.CopyFrom(request.grip)
    return self._stream(ctx, lambda say: self._carry(source, target, grip, say))

  async def _stream(
    self, ctx: Ctx, call: Callable[[Callable[[str], None]], Awaitable[None]]
  ) -> AsyncIterator[tpb.Progress]:
    """Make a long call, saying how far it has got every `PROGRESS_INTERVAL` seconds, and when it
    is done. It runs on when the client goes away."""
    served = self._served
    served.stamp(ctx)
    start = time.monotonic()
    step = [""]

    def say(now: str) -> None:
      step[0] = now

    task = asyncio.ensure_future(call(say))
    try:
      while True:
        done, _ = await asyncio.wait({task}, timeout=PROGRESS_INTERVAL)
        if done:
          break
        yield tpb.Progress(elapsed=time.monotonic() - start, step=step[0])
      try:
        task.result()
      except Exception as error:
        raise to_connect_error(error) from error
      finally:
        served.stamp(ctx, trailer=True)
      yield tpb.Progress(elapsed=time.monotonic() - start, done=True, step=step[0])
    finally:
      if not task.done():
        served.running.add(task)
        task.add_done_callback(served.running.discard)

  # -- the rest of the service --

  async def list(self, request: ppb.ListRequest, ctx: Ctx) -> ppb.ListResponse:
    self._served.stamp(ctx)
    by_name = self._served.positions.by_name
    return ppb.ListResponse(positions=[by_name[name] for name in sorted(by_name)])

  async def teach(self, request: ppb.TeachRequest, ctx: Ctx) -> ppb.TeachResponse:
    served = self._served
    try:
      if not request.name:
        raise ValueError("a position needs a name")
      async with served.motion:
        if request.HasField("joint_state"):
          joints = wire.joint_state_from(request.joint_state)
        else:
          served.require_set_up()
          joints = await self._device.arm.request_joint_state()
        missing = [axis.name for axis in POSITION_AXES if axis not in joints]
        if self._device.rail is not None and PreciseFlexAxis.RAIL not in joints:
          missing.append(PreciseFlexAxis.RAIL.name)
        if missing:
          raise ValueError(f"a position needs {', '.join(missing)}")
        kept = {axis: joints[axis] for axis in POSITION_AXES}
        if PreciseFlexAxis.RAIL in joints and (
          self._device.rail is not None or request.HasField("joint_state")
        ):
          kept[PreciseFlexAxis.RAIL] = joints[PreciseFlexAxis.RAIL]
        position = ppb.Position(name=request.name, joint_state=wire.joint_state_to(kept))
        served.positions.teach(position)
    except ConnectError:
      raise
    except Exception as error:
      raise to_connect_error(error) from error
    finally:
      served.stamp(ctx)
    return ppb.TeachResponse(position=position)

  async def forget(self, request: ppb.ForgetRequest, ctx: Ctx) -> ppb.ForgetResponse:
    served = self._served
    try:
      async with served.motion:
        served.positions.forget(request.name)
    except ConnectError:
      raise
    except Exception as error:
      raise to_connect_error(error) from error
    finally:
      served.stamp(ctx)
    return ppb.ForgetResponse()

  async def get_holding(self, request: ppb.GetHoldingRequest, ctx: Ctx) -> ppb.GetHoldingResponse:
    served = self._served
    try:
      if served.set_up and served.holding is not False:
        # Jaws closed all the way hold nothing; jaws stopped short hold what the server says.
        if await self._device.gripper.sense_fully_closed():
          served.holding = False
    except Exception as error:
      raise to_connect_error(error) from error
    finally:
      served.stamp(ctx)
    response = ppb.GetHoldingResponse()
    if served.holding is not None:
      response.holding = served.holding
    return response


def positions_application(served: "Served") -> Dict[str, "ASGIApp"]:
  """The positions service's application, by the path its calls start with."""
  return {
    "/pylabrobot.brooks.precise_flex.server.v1.PositionsService/": PositionsServiceASGIApplication(
      PositionsHandlers(served)
    )
  }
