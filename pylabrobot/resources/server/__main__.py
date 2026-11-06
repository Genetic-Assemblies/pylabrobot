"""Serve a resource server on its own: `python -m pylabrobot.resources.server --port 8080`.

The store is held in memory in this process. Devices served elsewhere keep their resources on it by
its URL, so several of them share one tree. Needs uvicorn, which the `resource-server` extra
installs.
"""

import argparse
from typing import Optional, Sequence

from pylabrobot.resources.server.memory import MemoryStore, asgi_app


def main(argv: Optional[Sequence[str]] = None) -> None:
  parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
  parser.add_argument("--host", default="127.0.0.1", help="the address to listen on")
  parser.add_argument("--port", type=int, default=8080, help="the port to listen on")
  args = parser.parse_args(argv)

  import uvicorn

  uvicorn.run(asgi_app(MemoryStore()), host=args.host, port=args.port)


if __name__ == "__main__":
  main()
