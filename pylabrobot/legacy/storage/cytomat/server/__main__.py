"""Serve a Cytomat: `python -m pylabrobot.legacy.storage.cytomat.server --simulation --rack
cytomat_rack_10mm_47:rack_1`.

`--serial-port` is the port the Cytomat is on; `--simulation` serves a simulated one, which takes
it that a robot loads and clears the transfer station as moves need. Each `--rack FACTORY:NAME` is
a rack the backend is told, made by a factory in `pylabrobot.legacy.storage.cytomat.racks`, in the
order the device numbers them; a client's `set_racks` replaces them. The backend is set up before
it is served. Needs uvicorn, which the `resource-server` extra installs.
"""

import argparse
import asyncio
from typing import Optional, Sequence

from pylabrobot.legacy.storage.cytomat import racks as cytomat_racks
from pylabrobot.legacy.storage.cytomat.constants import CytomatType
from pylabrobot.legacy.storage.cytomat.cytomat import CytomatBackend
from pylabrobot.legacy.storage.cytomat.server.serve import serve
from pylabrobot.legacy.storage.cytomat.simulator import CytomatSimulator
from pylabrobot.legacy.storage.server.racks import make_racks, named_rack


def main(argv: Optional[Sequence[str]] = None) -> None:
  parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
  parser.add_argument(
    "--model", choices=[t.value for t in CytomatType], default=CytomatType.C6000.value
  )
  where = parser.add_mutually_exclusive_group(required=True)
  where.add_argument("--serial-port", help="the serial port the Cytomat is on")
  where.add_argument("--simulation", action="store_true", help="serve a simulated Cytomat")
  parser.add_argument(
    "--rack",
    type=named_rack,
    action="append",
    default=[],
    metavar="FACTORY:NAME",
    help="a rack, in the order the device numbers them; may be repeated",
  )
  parser.add_argument("--host", default="127.0.0.1")
  parser.add_argument("--port", type=int, default=8092)
  args = parser.parse_args(argv)

  racks = make_racks(cytomat_racks, args.rack)
  backend: CytomatBackend
  if args.simulation:
    backend = CytomatSimulator(args.model, strict_transfer_station=False)
  else:
    backend = CytomatBackend(model=args.model, port=args.serial_port)

  async def run() -> None:
    await backend.setup()
    if racks:
      await backend.set_racks(racks)
    try:
      await serve(backend, host=args.host, port=args.port)
    finally:
      await backend.stop()

  asyncio.run(run())


if __name__ == "__main__":
  main()
