"""Serve a Liconic: `python -m pylabrobot.legacy.storage.liconic.server --simulation --rack
liconic_rack_17mm_22:cassette_1`.

`--serial-port` is the port the Liconic is on; `--simulation` serves a simulated one, with a
simulated barcode reader, which takes it that a robot loads and clears the transfer station as
moves need. Each `--rack FACTORY:NAME` is a cassette the backend is told, made by a factory in
`pylabrobot.legacy.storage.liconic.racks`, in the order the device numbers them; a client's
`set_racks` replaces them. The backend is set up before it is served. A barcode reader on the
device is not configured from here. Needs uvicorn, which the `resource-server` extra installs.
"""

import argparse
import asyncio
from typing import Optional, Sequence

from pylabrobot.legacy.storage.liconic import racks as liconic_racks
from pylabrobot.legacy.storage.liconic.constants import LiconicType
from pylabrobot.legacy.storage.liconic.liconic_backend import ExperimentalLiconicBackend
from pylabrobot.legacy.storage.liconic.server.serve import serve
from pylabrobot.legacy.storage.liconic.simulator import LiconicSimulator
from pylabrobot.legacy.storage.server.racks import make_racks, named_rack


def main(argv: Optional[Sequence[str]] = None) -> None:
  parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
  parser.add_argument(
    "--model", choices=[t.value for t in LiconicType], default=LiconicType.STX44_IC.value
  )
  where = parser.add_mutually_exclusive_group(required=True)
  where.add_argument("--serial-port", help="the serial port the Liconic is on")
  where.add_argument("--simulation", action="store_true", help="serve a simulated Liconic")
  parser.add_argument(
    "--rack",
    type=named_rack,
    action="append",
    default=[],
    metavar="FACTORY:NAME",
    help="a cassette, in the order the device numbers them; may be repeated",
  )
  parser.add_argument("--host", default="127.0.0.1")
  parser.add_argument("--port", type=int, default=8093)
  args = parser.parse_args(argv)

  racks = make_racks(liconic_racks, args.rack)
  backend: ExperimentalLiconicBackend
  if args.simulation:
    backend = LiconicSimulator(args.model, strict_transfer_station=False)
  else:
    backend = ExperimentalLiconicBackend(model=args.model, port=args.serial_port)

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
