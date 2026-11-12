"""Serve a LightCycler 480: `python -m pylabrobot.roche.lightcycler.server --device 192.168.95.41`.

`--simulation` in place of `--device` serves a simulated instrument, its tray pressed by a simulated
button. `--switchbot` names the Bluetooth address of a SwitchBot Bot mounted on the tray button, so
`OpenTray` and `CloseTray` move the tray; without one they only say where it is. Needs uvicorn,
which the `resource-server` extra installs, and bleak for `--switchbot`.
"""

import argparse
import asyncio
from typing import Optional, Sequence

from ..device import LightCycler480
from ..driver import LightCycler480Driver
from ..tray_button import SwitchBotBot
from .serve import DEFAULT_PORT, serve


def main(argv: Optional[Sequence[str]] = None) -> None:
  parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
  where = parser.add_mutually_exclusive_group(required=True)
  where.add_argument("--device", help="the LightCycler's IP address")
  where.add_argument("--simulation", action="store_true", help="serve a simulated LightCycler")
  parser.add_argument(
    "--device-port", type=int, default=LightCycler480Driver.DEFAULT_PORT, help="its base port"
  )
  parser.add_argument("--switchbot", help="the Bluetooth address of the bot on the tray button")
  parser.add_argument("--bluetooth-adapter", help="the Bluetooth adapter to reach it with: hci1")
  parser.add_argument("--host", default="127.0.0.1")
  parser.add_argument("--port", type=int, default=DEFAULT_PORT)
  args = parser.parse_args(argv)

  button = None
  if args.switchbot is not None:
    button = SwitchBotBot(args.switchbot, adapter=args.bluetooth_adapter)
  lightcycler = LightCycler480(
    host=args.device, port=args.device_port, simulation=args.simulation, tray_button=button
  )

  async def run() -> None:
    await lightcycler.setup()
    try:
      await serve(lightcycler, host=args.host, port=args.port)
    finally:
      await lightcycler.stop()

  asyncio.run(run())


if __name__ == "__main__":
  main()
