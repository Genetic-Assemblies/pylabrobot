"""The LightCycler 480 served over Connect, and a client for one served elsewhere.

`lightcycler_server_app(lightcycler)` serves one; `python -m pylabrobot.roche.lightcycler.server`
serves one on the network. `LightCycler480(lightcycler_server=url)` drives a served one as one in
this process is driven: the same methods, each a call to the server.
"""

from .client import LightCyclerServer, RemoteLightCycler480
from .serve import LightCycler480Service, lightcycler_server_app, serve

__all__ = [
  "LightCycler480Service",
  "LightCyclerServer",
  "RemoteLightCycler480",
  "lightcycler_server_app",
  "serve",
]
