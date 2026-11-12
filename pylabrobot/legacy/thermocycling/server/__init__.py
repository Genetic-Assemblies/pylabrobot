"""Legacy thermocycler backends behind a Connect service.

`thermocycler_server_app({name: backend})` serves thermocyclers' backends;
`python -m pylabrobot.legacy.thermocycling.server` serves them on the network.
`RemoteThermocyclerBackend(name, thermocycler_server=url)` is a `ThermocyclerBackend` whose every
call is made on the served one, so `Thermocycler(backend=RemoteThermocyclerBackend(...), ...)` runs
unchanged.
"""

from pylabrobot.legacy.thermocycling.server.client import (
  RemoteThermocyclerBackend,
  ThermocyclerServer,
)
from pylabrobot.legacy.thermocycling.server.serve import serve, thermocycler_server_app

__all__ = [
  "RemoteThermocyclerBackend",
  "ThermocyclerServer",
  "serve",
  "thermocycler_server_app",
]
