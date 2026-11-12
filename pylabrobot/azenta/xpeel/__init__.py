"""The Azenta XPeel seal remover: `XPeel` drives one; `pylabrobot.azenta.xpeel.server` serves it."""

from pylabrobot.azenta.xpeel.xpeel import HAS_SERIAL, XPeel

__all__ = ["HAS_SERIAL", "XPeel"]
