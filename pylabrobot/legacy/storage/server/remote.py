"""What a client of a served legacy incubator backend takes, whichever it is: how calls reach the
server and their errors come back, and how the plates and sites a call takes are named."""

import json
from typing import AsyncIterator, Awaitable, Callable, Generic, List, Optional, Sequence, TypeVar

from connectrpc.errors import ConnectError

from pylabrobot.legacy.storage.server.errors import ErrorClasses
from pylabrobot.legacy.storage.server.served import from_barcode
from pylabrobot.legacy.storage.server.v1 import incubator_pb2 as ipb
from pylabrobot.resources import Plate, PlateCarrier, PlateHolder
from pylabrobot.resources.server.v1 import types_pb2 as tpb

R = TypeVar("R")
C = TypeVar("C")


class BackendServer(Generic[C]):
  """A backend server: where a backend is served, and how its calls get there.

  Attributes:
    client: the device's service client.
  """

  def __init__(self, address: str, client: C, errors: ErrorClasses):
    self.address = address
    self.client = client
    self._errors = errors

  def _raised(self, error: ConnectError) -> BaseException:
    """What the served backend raised, from the Connect error it came as."""
    return self._errors.from_connect_error(error) or error

  async def call(self, response: Awaitable[R]) -> R:
    """A call's response, raising what the served backend raised as it raised it."""
    try:
      return await response
    except ConnectError as error:
      raise self._raised(error) from None

  async def stream(
    self,
    progress: AsyncIterator[R],
    what: str,
    each: Callable[[R], None] = lambda _: None,
  ) -> R:
    """Read a long call's progress until the server says it is done; its last progress.

    Args:
      each: given every progress as it comes, the last too.

    Raises:
      ConnectionError: If the stream ends before the call is done.
    """
    last: Optional[R] = None
    try:
      async for message in progress:
        each(message)
        if getattr(message, "done"):
          last = message
    except ConnectError as error:
      raise self._raised(error) from None
    if last is None:
      raise ConnectionError(f"the server stopped before {what} was done")
    return last

  async def close(self) -> None:
    await self.client.close()  # type: ignore[attr-defined]


def site_ref(site: PlateHolder) -> tpb.ResourceRef:
  """A site, by its name and its rack's."""
  rack = site.parent
  root = rack.name if isinstance(rack, PlateCarrier) else ""
  return tpb.ResourceRef(name=tpb.NameRef(root=root, name=site.name))


def plate_message(plate: Plate, racks: Sequence[PlateCarrier]) -> ipb.Plate:
  """A plate, with the site of the racks it is in; none when it is not in them."""
  message = ipb.Plate(name=plate.name)
  site = plate.parent
  if isinstance(site, PlateHolder) and site.parent is not None:
    if site.parent.name in {rack.name for rack in racks}:
      message.site.CopyFrom(site_ref(site))
  if plate.barcode is not None:
    message.barcode.CopyFrom(from_barcode(plate.barcode))
  return message


def racks_request(racks: List[PlateCarrier]) -> ipb.SetRacksRequest:
  """Racks as `set_racks` sends them, without the plates in them."""
  request = ipb.SetRacksRequest()
  for rack in racks:
    data = rack.serialize()
    for site in data.get("children", []):
      site.pop("children", None)
    request.racks.append(json.dumps(data))
  return request
