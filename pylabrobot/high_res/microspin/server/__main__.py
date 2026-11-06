"""Serve a MicroSpin: `python -m pylabrobot.high_res.microspin.server --device 192.168.127.60`.

`--resource-server` names the resource server to keep the device's resources on, so several device
servers share one tree. Without it, the resources are held in this process and served on their own
port, `--resource-port`. `--settings-json` names the defaults the device uses where a call names
none (`Settings` in `v1/microspin.proto`); without it, they are the code's. Needs uvicorn, which the
`resource-server` extra installs.
"""

import argparse
import asyncio
from typing import Optional, Sequence

from ..device import MicroSpin
from .serve import read_settings, serve


def main(argv: Optional[Sequence[str]] = None) -> None:
  parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
  parser.add_argument("--name", default="microspin", help="what to call the device's body")
  where = parser.add_mutually_exclusive_group(required=True)
  where.add_argument("--device", help="the MicroSpin's IP address or name")
  where.add_argument("--simulation", action="store_true", help="serve a simulated MicroSpin")
  parser.add_argument("--device-port", type=int, default=1000, help="its remote-control port")
  parser.add_argument(
    "--resource-server",
    help="the resource server to keep the device's resources on; held here and served on "
    "--resource-port when not given",
  )
  parser.add_argument("--resource-port", type=int, default=8080)
  parser.add_argument("--settings-json", help="a JSON file of the device's defaults")
  parser.add_argument("--host", default="127.0.0.1")
  parser.add_argument("--port", type=int, default=8082)
  args = parser.parse_args(argv)

  microspin = MicroSpin(
    name=args.name,
    host=args.device,
    port=args.device_port,
    simulation=args.simulation,
    resource_server=args.resource_server,
  )
  settings = None if args.settings_json is None else read_settings(args.settings_json)

  async def run() -> None:
    await microspin.setup()
    try:
      await serve(
        microspin,
        host=args.host,
        port=args.port,
        resource_port=args.resource_port if args.resource_server is None else None,
        settings=settings,
      )
    finally:
      await microspin.stop()

  asyncio.run(run())


if __name__ == "__main__":
  main()
