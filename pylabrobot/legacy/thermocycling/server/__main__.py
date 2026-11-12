"""Serve thermocyclers: `python -m pylabrobot.legacy.thermocycling.server --thermocycler
tc_1:odtc:192.168.1.20`.

Each `--thermocycler NAME:BACKEND:ADDRESS` is a thermocycler driven by a legacy backend: `odtc` (an
Inheco ODTC, `ExperimentalODTCBackend`, at the IP ADDRESS), `proflex` or `atc` (a ThermoFisher
ProFlex or ATC, `ProflexBackend` or `ATCBackend`, at the IP ADDRESS, without SSL). With
`--simulation`, each `--thermocycler NAME` is a `ThermocyclerSimulatorBackend`, and a backend given
is not used. Needs uvicorn, which the `resource-server` extra installs.
"""

import argparse
import asyncio
from typing import Callable, Dict, Optional, Sequence, Tuple

from pylabrobot.legacy.thermocycling.backend import ThermocyclerBackend
from pylabrobot.legacy.thermocycling.server.serve import serve
from pylabrobot.legacy.thermocycling.simulator import ThermocyclerSimulatorBackend


def _odtc(address: str) -> ThermocyclerBackend:
  from pylabrobot.legacy.thermocycling.inheco.odtc_backend import ExperimentalODTCBackend

  return ExperimentalODTCBackend(ip=address)


def _proflex(address: str) -> ThermocyclerBackend:
  from pylabrobot.legacy.thermocycling.thermo_fisher import ProflexBackend

  return ProflexBackend(ip=address)


def _atc(address: str) -> ThermocyclerBackend:
  from pylabrobot.legacy.thermocycling.thermo_fisher import ATCBackend

  return ATCBackend(ip=address)


# Each backend a thermocycler may be driven by, by the name the command line gives it.
BACKENDS: Dict[str, Callable[[str], ThermocyclerBackend]] = {
  "odtc": _odtc,
  "proflex": _proflex,
  "atc": _atc,
}


def _named_backend(text: str) -> Tuple[str, Optional[Tuple[str, str]]]:
  """NAME or NAME:BACKEND:ADDRESS."""
  name, sep, rest = text.partition(":")
  backend, _, address = rest.partition(":")
  if not name or (sep and (backend not in BACKENDS or not address)):
    raise argparse.ArgumentTypeError(
      f"expected NAME:BACKEND:ADDRESS, tc_1:odtc:192.168.1.20 say, with BACKEND one of "
      f"{', '.join(BACKENDS)}, not '{text}'"
    )
  return name, (backend, address) if sep else None


def thermocyclers(args: argparse.Namespace) -> Dict[str, ThermocyclerBackend]:
  made: Dict[str, ThermocyclerBackend] = {}
  for name, backend in args.thermocycler:
    if name in made:
      raise SystemExit(f"two thermocyclers are named '{name}'")
    if args.simulation:
      made[name] = ThermocyclerSimulatorBackend(
        num_zones=args.simulation_zones, speed=args.simulation_speed
      )
    elif backend is None:
      raise SystemExit(
        f"thermocycler '{name}' needs a backend, NAME:BACKEND:ADDRESS, without --simulation"
      )
    else:
      kind, address = backend
      made[name] = BACKENDS[kind](address)
  return made


def main(argv: Optional[Sequence[str]] = None) -> None:
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument(
    "--thermocycler",
    type=_named_backend,
    action="append",
    required=True,
    metavar="NAME:BACKEND:ADDRESS",
    help=f"a thermocycler to serve: its name, its backend ({', '.join(BACKENDS)}) and its "
    "address; may be repeated",
  )
  parser.add_argument("--simulation", action="store_true", help="serve simulated thermocyclers")
  parser.add_argument(
    "--simulation-speed",
    type=float,
    default=1.0,
    help="how many times faster than a real one a simulated thermocycler runs",
  )
  parser.add_argument(
    "--simulation-zones",
    type=int,
    default=1,
    help="how many temperature zones a simulated thermocycler's block has",
  )
  parser.add_argument("--host", default="127.0.0.1")
  parser.add_argument("--port", type=int, default=8096)
  args = parser.parse_args(argv)

  asyncio.run(serve(thermocyclers(args), host=args.host, port=args.port))


if __name__ == "__main__":
  main()
