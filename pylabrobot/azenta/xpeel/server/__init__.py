"""Azenta XPeels behind a Connect service.

`xpeel_server_app({name: xpeel})` serves peelers; `python -m pylabrobot.azenta.xpeel.server` serves
them on the network. `RemoteXPeel(name, xpeel_server=url)` is an `XPeel` that drives a served one as
one in this process is driven: the same methods, each call made on the server's peeler.
"""

from pylabrobot.azenta.xpeel.server.client import RemoteXPeel, XPeelServer
from pylabrobot.azenta.xpeel.server.serve import serve, xpeel_server_app

__all__ = ["RemoteXPeel", "XPeelServer", "serve", "xpeel_server_app"]
