"""Serve XPeels: `python -m pylabrobot.azenta.xpeel.server --xpeel peeler_1:/dev/ttyUSB1`.

Each `--xpeel NAME:PORT` is a peeler on a serial port. With `--simulation`, each `--xpeel NAME` is a
simulated one (an `XPeel` on a simulated peeler's port), and a port given is not used. Needs
uvicorn, which the `resource-server` extra installs.
"""

import argparse
import asyncio
from typing import Dict, Optional, Sequence, Tuple

from pylabrobot.azenta.xpeel.server.serve import serve
from pylabrobot.azenta.xpeel.simulator import SimulatedXPeel
from pylabrobot.azenta.xpeel.xpeel import XPeel


def _named_port(text: str) -> Tuple[str, Optional[str]]:
  """NAME or NAME:PORT."""
  name, sep, port = text.partition(":")
  if not name or (sep and not port):
    raise argparse.ArgumentTypeError(f"expected NAME:PORT, peeler_1:/dev/ttyUSB1 say, not '{text}'")
  return name, port if sep else None


def peelers(args: argparse.Namespace) -> Dict[str, XPeel]:
  made: Dict[str, XPeel] = {}
  for name, port in args.xpeel:
    if name in made:
      raise SystemExit(f"two peelers are named '{name}'")
    if args.simulation:
      made[name] = SimulatedXPeel(
        port=port or "simulated", timeout=args.timeout, speed=args.simulation_speed
      )
    elif port is None:
      raise SystemExit(f"peeler '{name}' needs its serial port, NAME:PORT, without --simulation")
    else:
      made[name] = XPeel(port=port, timeout=args.timeout)
  return made


def main(argv: Optional[Sequence[str]] = None) -> None:
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument(
    "--xpeel",
    type=_named_port,
    action="append",
    required=True,
    metavar="NAME:PORT",
    help="a peeler to serve: its name and its serial port; may be repeated",
  )
  parser.add_argument("--simulation", action="store_true", help="serve simulated peelers")
  parser.add_argument(
    "--simulation-speed",
    type=float,
    default=1.0,
    help="how many times faster than a real one a simulated peeler runs",
  )
  parser.add_argument(
    "--timeout",
    type=float,
    default=XPeel.RESPONSE_TIMEOUT,
    help="XPeel's timeout: how long it waits for an answer, in seconds",
  )
  parser.add_argument("--host", default="127.0.0.1")
  parser.add_argument("--port", type=int, default=8095)
  args = parser.parse_args(argv)

  asyncio.run(serve(peelers(args), host=args.host, port=args.port))


if __name__ == "__main__":
  main()
