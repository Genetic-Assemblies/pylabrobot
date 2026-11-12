"""Serve a HighRes sample store: `python -m pylabrobot.high_res.sample_storage.server --simulation`.

`--device` is the store's address on the network (its remote-control port is 1000); `--simulation`
serves a simulated one instead, with two stackers of 24 slots and one nest. The store is set up
before it is served, reading its stackers and nests from the device. Needs uvicorn, which the
`resource-server` extra installs.
"""

import argparse
import asyncio
from typing import Dict, Optional, Sequence, Type

from pylabrobot.high_res.sample_storage import AmbiStore, SteriStore, TundraStore
from pylabrobot.high_res.sample_storage.driver import HighResSampleStorage
from pylabrobot.high_res.sample_storage.server.serve import serve
from pylabrobot.high_res.sample_storage.simulator import SampleStorageSimulator

MODELS: Dict[str, Type[HighResSampleStorage]] = {
  "TundraStore": TundraStore,
  "SteriStore": SteriStore,
  "AmbiStore": AmbiStore,
}


def main(argv: Optional[Sequence[str]] = None) -> None:
  parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
  parser.add_argument("--name", default="tundra_store", help="the store's name: its tree's root")
  parser.add_argument("--model", choices=sorted(MODELS), default="TundraStore")
  where = parser.add_mutually_exclusive_group(required=True)
  where.add_argument("--device", help="the store's IP address or name")
  where.add_argument("--simulation", action="store_true", help="serve a simulated store")
  parser.add_argument("--device-port", type=int, default=1000, help="its remote-control port")
  parser.add_argument("--home", action="store_true", help="home it when it is set up")
  parser.add_argument("--host", default="127.0.0.1")
  parser.add_argument("--port", type=int, default=8091)
  args = parser.parse_args(argv)

  store = MODELS[args.model](
    host=args.device or "simulation", name=args.name, port=args.device_port
  )
  if args.simulation:
    store.io = SampleStorageSimulator(product_name=args.model)  # type: ignore[assignment]

  async def run() -> None:
    await store.setup(home=args.home)
    try:
      await serve(store, host=args.host, port=args.port, set_up=True)
    finally:
      await store.stop()

  asyncio.run(run())


if __name__ == "__main__":
  main()
