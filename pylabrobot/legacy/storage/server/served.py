"""What serving a legacy incubator backend takes, whichever it is: its racks, the sites and plates
its calls take, its calls made one at a time on the wire, and long calls streamed.

The server holds the backend and the racks it was told (`set_racks`), and no plates: a call that
takes a plate says where it is, and the server puts a plate of its name there for the call, so the
backend reads the site from it as it does in this process, and takes it away after.

A backend speaks to its device a command and its reply at a time, and a move is several commands;
in a process of its own one caller is all it has. Here several clients call it, so every command
waits for the one before it (`io`), and every move for the move before it (`motion`).
"""

import asyncio
import contextlib
import json
import time
from typing import (
  Any,
  AsyncIterator,
  Awaitable,
  Callable,
  Dict,
  Iterator,
  List,
  Optional,
  Protocol,
  Set,
  TypeVar,
)

from connectrpc.errors import ConnectError

from pylabrobot.legacy.storage.backend import IncubatorBackend
from pylabrobot.legacy.storage.server.errors import to_connect_error
from pylabrobot.legacy.storage.server.v1 import incubator_pb2 as ipb
from pylabrobot.resources import Coordinate, Plate, PlateCarrier, PlateHolder, Well
from pylabrobot.resources.barcode import Barcode
from pylabrobot.resources.server.v1 import types_pb2 as tpb

# An ASGI 3 application.
ASGIApp = Callable[[Dict[str, Any], Any, Any], Awaitable[None]]

# How often a long call says how far it has got, in seconds.
PROGRESS_INTERVAL = 5.0

T = TypeVar("T")

# The footprint of an SBS plate, in mm.
_PLATE_X = 127.76
_PLATE_Y = 85.48


class Progress(Protocol):
  """A device's progress message: how far a long call has got."""

  elapsed: float
  done: bool


P = TypeVar("P", bound=Progress)


class TaskLock:
  """A lock a task may take again while it holds it: a backend's command, made while it holds the
  wire, may make another (a Cytomat's reads its error register)."""

  def __init__(self) -> None:
    self._lock = asyncio.Lock()
    self._owner: Optional["asyncio.Task[Any]"] = None
    self._depth = 0

  async def __aenter__(self) -> None:
    task = asyncio.current_task()
    if self._owner is not None and self._owner is task:
      self._depth += 1
      return
    await self._lock.acquire()
    self._owner, self._depth = task, 1

  async def __aexit__(self, *exc: object) -> None:
    self._depth -= 1
    if self._depth == 0:
      self._owner = None
      self._lock.release()


def stand_in(name: str, barcode: Optional[Barcode] = None) -> Plate:
  """A plate of this name, for the length of a call: one well on an SBS footprint."""
  well = Well(name=f"{name}_A1", size_x=1, size_y=1, size_z=1).at(Coordinate(0, 0, 0))
  plate = Plate(name=name, size_x=_PLATE_X, size_y=_PLATE_Y, size_z=0, ordered_items={"A1": well})
  plate.barcode = barcode
  return plate


def to_barcode(message: tpb.Barcode) -> Barcode:
  return Barcode(
    data=message.data,
    symbology=message.symbology,  # type: ignore[arg-type]
    position_on_resource=message.position_on_resource,  # type: ignore[arg-type]
  )


def from_barcode(barcode: Barcode) -> tpb.Barcode:
  return tpb.Barcode(
    data=barcode.data,
    symbology=barcode.symbology,
    position_on_resource=barcode.position_on_resource,
  )


def describe_racks(racks: List[PlateCarrier]) -> List[ipb.Rack]:
  return [
    ipb.Rack(
      name=rack.name,
      model=rack.model or "",
      sites=[
        ipb.Site(name=site.name, index=index, size_z=site.get_size_z())
        for index, site in sorted(rack.sites.items())
      ],
    )
    for rack in racks
  ]


class ServedBackend:
  """One backend, each call made on it."""

  def __init__(self, backend: IncubatorBackend, io: str):
    """
    Args:
      backend: the backend to serve.
      io: the name of its method that sends a command and reads the reply, which every command
        goes through: each call to it waits for the one before.
    """
    self.backend = backend
    self.io = TaskLock()
    self.motion = asyncio.Lock()
    send = getattr(backend, io)

    async def one_at_a_time(*args: Any, **kwargs: Any) -> Any:
      async with self.io:
        return await send(*args, **kwargs)

    setattr(backend, io, one_at_a_time)
    # Calls that keep running when their client has gone, held so they are not collected.
    self._running: Set["asyncio.Task[Any]"] = set()

  @property
  def racks(self) -> List[PlateCarrier]:
    return list(self.backend._racks or [])

  # -- what calls take --

  def site(self, ref: tpb.ResourceRef) -> PlateHolder:
    """The site of the racks a reference names.

    Raises:
      ValueError: If it is not a reference by name, or names no one site of the racks.
    """
    if ref.WhichOneof("ref") != "name":
      raise ValueError("this server names sites by name: give a NameRef")
    root, name = ref.name.root, ref.name.name
    found = [
      site
      for rack in self.racks
      if root in ("", rack.name)
      for site in rack.sites.values()
      if site.name == name
    ]
    if not found:
      where = f"rack '{root}'" if root else "the racks"
      raise ValueError(f"there is no site '{name}' in {where}")
    if len(found) > 1:
      raise ValueError(f"'{name}' names a site in more than one rack: give its rack as the root")
    return found[0]

  @contextlib.contextmanager
  def plate(self, message: ipb.Plate) -> Iterator[Plate]:
    """A plate of the name the message gives, in its site for as long as the call takes."""
    barcode = to_barcode(message.barcode) if message.HasField("barcode") else None
    plate = stand_in(message.name, barcode)
    site = self.site(message.site) if message.HasField("site") else None
    if site is not None:
      site.assign_child_resource(plate)
    try:
      yield plate
    finally:
      if plate.parent is not None:
        plate.unassign()

  async def take_racks(self, request: ipb.SetRacksRequest) -> None:
    """Tell the backend the racks a client sent, as `set_racks` does."""
    racks = []
    for definition in request.racks:
      rack = PlateCarrier.deserialize(json.loads(definition))
      for site in rack.sites.values():
        if site.resource is not None:
          site.resource.unassign()
      racks.append(rack)
    await self.backend.set_racks(racks)

  # -- calls --

  async def call(self, work: Callable[[], Awaitable[T]], motion: bool = False) -> T:
    """Make a call on the backend, raising what it raised as a Connect error.

    Args:
      motion: whether it moves the device, so waits for any move under way.
    """
    try:
      if motion:
        async with self.motion:
          return await work()
      return await work()
    except ConnectError:
      raise
    except Exception as error:
      raise to_connect_error(error) from error

  async def stream(
    self,
    work: Callable[[], Awaitable[T]],
    progress: Callable[..., P],
    result: Callable[[T, P], None] = lambda _, __: None,
    motion: bool = True,
    partial: Optional[Callable[[P], bool]] = None,
  ) -> AsyncIterator[P]:
    """Make a long call, saying how far it has got every `PROGRESS_INTERVAL` seconds, and when it
    is done, with what it returned.

    Args:
      progress: makes a progress message from `elapsed` and `done`.
      result: puts what the call returned in the last progress.
      motion: whether it moves the device. A move finishes when its client goes away, and waits
        for any move under way; anything else (a wait) is dropped.
      partial: when the call fails, puts what it did before it failed in a progress, which is
        sent ahead of the error when it says it put anything there.
    """
    start = time.monotonic()

    async def run() -> T:
      if motion:
        async with self.motion:
          return await work()
      return await work()

    task = asyncio.ensure_future(run())
    try:
      while True:
        done, _ = await asyncio.wait({task}, timeout=PROGRESS_INTERVAL)
        if done:
          break
        yield progress(elapsed=time.monotonic() - start)
      try:
        value = task.result()
      except Exception as error:
        failed = to_connect_error(error)
        if partial is not None:
          before = progress(elapsed=time.monotonic() - start)
          if partial(before):
            yield before
        raise failed from error
      last = progress(elapsed=time.monotonic() - start, done=True)
      result(value, last)
      yield last
    finally:
      if not task.done():
        if motion:
          self._running.add(task)
          task.add_done_callback(self._running.discard)
        else:
          task.cancel()
