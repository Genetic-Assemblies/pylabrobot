"""Racks named on a command line: `--rack cytomat_rack_10mm_47:rack_1`, a factory and a name."""

import argparse
from types import ModuleType
from typing import Callable, List, Sequence, Tuple

from pylabrobot.resources import PlateCarrier


def named_rack(text: str) -> Tuple[str, str]:
  """A `FACTORY:NAME` argument, as the factory's name and the rack's."""
  factory, sep, name = text.partition(":")
  if not sep or not factory or not name:
    raise argparse.ArgumentTypeError(
      f"expected FACTORY:NAME, cytomat_rack_10mm_47:rack_1 say, not '{text}'"
    )
  return factory, name


def make_racks(module: ModuleType, named: Sequence[Tuple[str, str]]) -> List[PlateCarrier]:
  """Each rack made by its factory in `module`.

  Raises:
    ValueError: If the module has no factory of a name.
  """
  racks = []
  for factory_name, name in named:
    factory: Callable[[str], PlateCarrier] = getattr(module, factory_name, None)  # type: ignore[assignment]
    if factory_name.startswith("_") or not callable(factory):
      raise ValueError(f"{module.__name__} has no rack '{factory_name}'")
    racks.append(factory(name))
  return racks
