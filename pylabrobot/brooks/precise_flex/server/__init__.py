"""The PreciseFlex behind a Connect service.

`precise_flex_server_app(device)` serves a device; `python -m pylabrobot.brooks.precise_flex.server`
serves one on the network. `PreciseFlex400(precise_flex_server=url)` drives a served arm as one in
this process is driven: the same classes and methods, each call made on the server's device. The
server also keeps taught positions and carries plates between them (`PositionsService`). The
defaults its features use where a call names none are the server's, from a settings file
(`read_settings`); a client reads them and cannot set them.
"""

from pylabrobot.brooks.precise_flex.server.client import (
  PreciseFlexServer,
  RemotePreciseFlexDevice,
  RemotePreciseFlexDriver,
  remote_device,
)
from pylabrobot.brooks.precise_flex.server.description import Settings, read_settings
from pylabrobot.brooks.precise_flex.server.serve import precise_flex_server_app, serve

__all__ = [
  "PreciseFlexServer",
  "RemotePreciseFlexDevice",
  "RemotePreciseFlexDriver",
  "Settings",
  "precise_flex_server_app",
  "read_settings",
  "remote_device",
  "serve",
]
