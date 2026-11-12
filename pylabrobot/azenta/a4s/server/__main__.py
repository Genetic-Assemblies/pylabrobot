"""Serve a4S sealers: `python -m pylabrobot.azenta.a4s.server --a4s sealer_1:/dev/ttyUSB0`.

Each `--a4s NAME:PORT` is a sealer on a serial port. With `--simulation`, each `--a4s NAME` is a
simulated one (an `A4S` on a simulated sealer's port), and a port given is not used. Needs uvicorn,
which the `resource-server` extra installs.
"""

import argparse
import asyncio
from typing import Dict, Optional, Sequence, Tuple

from pylabrobot.azenta.a4s.a4s import A4S
from pylabrobot.azenta.a4s.server.serve import serve
from pylabrobot.azenta.a4s.simulator import SimulatedA4S


def _named_port(text: str) -> Tuple[str, Optional[str]]:
  """NAME or NAME:PORT."""
  name, sep, port = text.partition(":")
  if not name or (sep and not port):
    raise argparse.ArgumentTypeError(f"expected NAME:PORT, sealer_1:/dev/ttyUSB0 say, not '{text}'")
  return name, port if sep else None


def sealers(args: argparse.Namespace) -> Dict[str, A4S]:
  made: Dict[str, A4S] = {}
  for name, port in args.a4s:
    if name in made:
      raise SystemExit(f"two sealers are named '{name}'")
    if args.simulation:
      made[name] = SimulatedA4S(
        port=port or "simulated", timeout=args.timeout, speed=args.simulation_speed
      )
    elif port is None:
      raise SystemExit(f"sealer '{name}' needs its serial port, NAME:PORT, without --simulation")
    else:
      made[name] = A4S(port=port, timeout=args.timeout)
  return made


def main(argv: Optional[Sequence[str]] = None) -> None:
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument(
    "--a4s",
    type=_named_port,
    action="append",
    required=True,
    metavar="NAME:PORT",
    help="a sealer to serve: its name and its serial port; may be repeated",
  )
  parser.add_argument("--simulation", action="store_true", help="serve simulated sealers")
  parser.add_argument(
    "--simulation-speed",
    type=float,
    default=1.0,
    help="how many times faster than a real one a simulated sealer runs",
  )
  parser.add_argument(
    "--timeout", type=int, default=20, help="A4S's timeout: how long a wait waits, in seconds"
  )
  parser.add_argument("--host", default="127.0.0.1")
  parser.add_argument("--port", type=int, default=8094)
  args = parser.parse_args(argv)

  asyncio.run(serve(sealers(args), host=args.host, port=args.port))


if __name__ == "__main__":
  main()
