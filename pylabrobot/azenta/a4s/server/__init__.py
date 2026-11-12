"""Azenta a4S sealers behind a Connect service.

`a4s_server_app({name: a4s})` serves sealers; `python -m pylabrobot.azenta.a4s.server` serves them
on the network. `RemoteA4S(name, a4s_server=url)` is an `A4S` that drives a served one as one in
this process is driven: the same methods, each call made on the server's sealer.
"""

from pylabrobot.azenta.a4s.server.client import A4SServer, RemoteA4S
from pylabrobot.azenta.a4s.server.serve import a4s_server_app, serve

__all__ = ["A4SServer", "RemoteA4S", "a4s_server_app", "serve"]
