"""A Liconic behind a Connect service.

`liconic_server_app(backend)` serves an `ExperimentalLiconicBackend`; `python -m
pylabrobot.legacy.storage.liconic.server` serves one on the network.
`RemoteLiconicBackend(url)` is an `ExperimentalLiconicBackend` whose every call is made on the
served one, so an `Incubator` drives it unchanged.
"""

from pylabrobot.legacy.storage.liconic.server.client import LiconicServer, RemoteLiconicBackend
from pylabrobot.legacy.storage.liconic.server.serve import liconic_server_app, serve

__all__ = ["LiconicServer", "RemoteLiconicBackend", "liconic_server_app", "serve"]
