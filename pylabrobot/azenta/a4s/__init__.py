"""The Azenta a4S thermal sealer: `A4S` drives one; `pylabrobot.azenta.a4s.server` serves it."""

from pylabrobot.azenta.a4s.a4s import A4S, HAS_SERIAL, A4SStatus

__all__ = ["A4S", "A4SStatus", "HAS_SERIAL"]
