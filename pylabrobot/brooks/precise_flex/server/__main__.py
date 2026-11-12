"""Serve a PreciseFlex: `python -m pylabrobot.brooks.precise_flex.server --simulation`.

Without `--simulation`, it drives the arm at `--arm-host`. `--positions` names the JSON file the
taught positions are kept in. With `--resource-server`, the device's resources are kept there;
with `--resource-port` instead, in a resource server held in this process and served on that port.
`--settings-json` names the defaults the arm's features use where a call names none
(`v1/description.proto`'s `Settings`). Needs uvicorn, which the `resource-server` extra installs.
"""

import argparse
import asyncio
from typing import Any, Dict, Optional, Sequence

from pylabrobot.brooks.precise_flex.device import PreciseFlex400
from pylabrobot.brooks.precise_flex.driver.master import PreciseFlexDriver
from pylabrobot.brooks.precise_flex.server.description import read_settings
from pylabrobot.brooks.precise_flex.server.serve import serve
from pylabrobot.resources.server.client import ResourceServer


def main(argv: Optional[Sequence[str]] = None) -> None:
  parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
  parser.add_argument("--name", default="PreciseFlex400", help="what to call the device")
  link = parser.add_mutually_exclusive_group(required=True)
  link.add_argument("--simulation", action="store_true", help="serve a simulated arm")
  link.add_argument("--arm-host", help="the arm controller's address")
  parser.add_argument("--arm-port", type=int, default=10100)
  parser.add_argument(
    "--declared-configuration-json", help="a configuration the arm is declared to have"
  )
  parser.add_argument(
    "--gripper-length", type=float, default=162.0, help="wrist to tool point, in mm; a fallback"
  )
  parser.add_argument("--gripper-z-offset", type=float, default=0.0)
  parser.add_argument(
    "--closed-gripper-position",
    type=float,
    help="the gripper axis's position, in the controller's units, at the narrow end of the jaws; "
    "needed with --arm-host",
  )
  parser.add_argument("--vision-host", help="the vision server's address")
  parser.add_argument("--positions", help="the JSON file the taught positions are kept in")
  resources = parser.add_mutually_exclusive_group()
  resources.add_argument("--resource-server", help="the resource server to keep the arm in")
  resources.add_argument(
    "--resource-port",
    type=int,
    help="serve a resource server held here, the arm in it, on this port",
  )
  parser.add_argument("--settings-json", help="the defaults the arm's features use")
  parser.add_argument("--host", default="127.0.0.1")
  parser.add_argument("--port", type=int, default=8090)
  args = parser.parse_args(argv)

  kwargs: Dict[str, Any] = {"name": args.name}
  if args.simulation:
    kwargs.update(simulation=True, declared_configuration_json=args.declared_configuration_json)
  else:
    if args.closed_gripper_position is None:
      parser.error("--arm-host needs --closed-gripper-position")
    kwargs["driver"] = PreciseFlexDriver(
      host=args.arm_host,
      port=args.arm_port,
      gripper_length=args.gripper_length,
      gripper_z_offset=args.gripper_z_offset,
      closed_gripper_position=args.closed_gripper_position,
      vision_host=args.vision_host,
      declared_configuration_json=args.declared_configuration_json,
    )
  device = PreciseFlex400(**kwargs)
  settings = None if args.settings_json is None else read_settings(args.settings_json)
  resource_server = (
    ResourceServer.local() if args.resource_port is not None else args.resource_server
  )
  asyncio.run(
    serve(
      device,
      host=args.host,
      port=args.port,
      settings=settings,
      resource_server=resource_server,
      resource_port=args.resource_port,
      positions_path=args.positions,
    )
  )


if __name__ == "__main__":
  main()
