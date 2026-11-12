"""A Cytomat behind a Connect service.

`cytomat_server_app(backend)` serves a `CytomatBackend`; `python -m
pylabrobot.legacy.storage.cytomat.server` serves one on the network.
`RemoteCytomatBackend(url)` is a `CytomatBackend` whose every call is made on the served one, so an
`Incubator` drives it unchanged.
"""

from pylabrobot.legacy.storage.cytomat.server.client import CytomatServer, RemoteCytomatBackend
from pylabrobot.legacy.storage.cytomat.server.serve import cytomat_server_app, serve

__all__ = ["CytomatServer", "RemoteCytomatBackend", "cytomat_server_app", "serve"]
