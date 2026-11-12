"""What a client keeps of a served arm (`v1/description.proto`), and the server's settings.

The server describes its device: its configuration, its settings as its features hold them now,
whether it holds a plate, and the resources its parts are on the resource server. A client takes
the description up into the same classes, so what their attributes hold reads without a call.

Settings are the defaults the arm's features use where a call names none. They are a JSON file
holding the `Settings` message, read when the server starts and put in place then and after every
setup. Anything not in it keeps the default in the code.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

from google.protobuf import json_format

from pylabrobot.brooks.precise_flex.device import PreciseFlexDevice
from pylabrobot.brooks.precise_flex.server import wire
from pylabrobot.brooks.precise_flex.server.v1 import description_pb2 as dpb
from pylabrobot.brooks.precise_flex.server.v1 import types_pb2 as tpb
from pylabrobot.resources.server.v1 import types_pb2 as rpb

if TYPE_CHECKING:
  from pylabrobot.brooks.precise_flex.server.client import RemotePreciseFlexDevice

Settings = dpb.Settings

# Each arm setting, and the attribute of the arm it is. `parking_position` goes on its own.
ARM_SETTINGS = (
  "profile_index",
  "station_index",
  "station_z_clearance",
  "horizontal_compliance",
  "horizontal_compliance_torque",
  "default_recovery_speed_percent",
  "default_ztouch_search_speed_percent",
  "default_ztouch_approach_speed_percent",
)
GRIPPER_SETTINGS = ("default_finger_speed_percent", "default_grasp_force")


def read_settings(path: str) -> dpb.Settings:
  """Read a settings file. A field it does not know is an error, so a misspelled one is caught.

  Raises:
    ValueError: If the file is not a `Settings` message.
  """
  with open(path, encoding="utf-8") as f:
    text = f.read()
  try:
    return json_format.Parse(text, dpb.Settings())
  except json_format.ParseError as error:
    raise ValueError(f"{path} is not a PreciseFlex server's settings: {error}") from error


def put_in_place(device: PreciseFlexDevice, settings: Optional[dpb.Settings]) -> None:
  """Set what `settings` gives on the device's features.

  Raises:
    ValueError: If a feature refuses a value, as the arm refuses a parking position outside its
      soft limits.
  """
  if settings is None:
    return
  arm, gripper = device.arm, device.gripper
  for name in ARM_SETTINGS:
    if settings.arm.HasField(name):
      setattr(arm, name, getattr(settings.arm, name))
  if settings.arm.HasField("parking_position"):
    arm.parking_position = wire.joint_state_from(settings.arm.parking_position)
  for name in GRIPPER_SETTINGS:
    if settings.gripper.HasField(name):
      setattr(gripper, name, getattr(settings.gripper, name))


def settings_of(device: PreciseFlexDevice) -> dpb.Settings:
  """The settings as the device's features hold them now."""
  arm, gripper = device.arm, device.gripper
  settings = dpb.Settings()
  for name in ARM_SETTINGS:
    setattr(settings.arm, name, getattr(arm, name))
  if arm.parking_position is not None:
    settings.arm.parking_position.CopyFrom(wire.joint_state_to(arm.parking_position))
  for name in GRIPPER_SETTINGS:
    setattr(settings.gripper, name, getattr(gripper, name))
  return settings


def describe(
  device: PreciseFlexDevice,
  resources: Optional[dpb.Resources],
  holding: Optional[bool],
) -> dpb.Description:
  """The description of a served device.

  Args:
    resources: its parts on the resource server, once made there.
    holding: whether it holds a plate, as the server last knows.
  """
  driver = device.driver
  low, high = device.gripper.jaw_width_range
  description = dpb.Description(
    name=device.name,
    model=device.model or "",
    size_x=device.get_size_x(),
    size_y=device.get_size_y(),
    size_z=device.get_size_z(),
    has_rail=driver.rail is not None,
    has_vision=driver.vision is not None,
    vision_server_connected=driver.vision_server_connected,
    gripper=dpb.GripperDescription(
      closed_gripper_position=device.gripper.closed_gripper_position,
      jaw_width_range=tpb.Range(low=low, high=high),
      is_dual_gripper=device.gripper._is_dual_gripper,
    ),
    settings=settings_of(device),
  )
  if driver._configuration is not None:
    description.configuration_json = wire.configuration_to(driver._configuration)
  if driver.vision is not None:
    description.vision_configuration_json = wire.vision_configuration_to(
      driver.vision.configuration
    )
  if resources is not None:
    description.resources.CopyFrom(resources)
  if holding is not None:
    description.holding = holding
  return description


async def apply(device: "RemotePreciseFlexDevice", description: dpb.Description) -> None:
  """Take a description up into a client's device, its driver and its features."""
  from pylabrobot.brooks.precise_flex.server.client import (
    RemotePreciseFlexRail,
    RemotePreciseFlexVision,
  )

  # The client's device stands in for the server's, with no tree of its own: its name is the
  # server's device's, whatever the client called it before it was described.
  device._name = description.name
  device.model = description.model
  device._size_x, device._size_y, device._size_z = (
    description.size_x,
    description.size_y,
    description.size_z,
  )
  driver = device.driver
  configuration = (
    wire.configuration_from(description.configuration_json)
    if description.HasField("configuration_json")
    else None
  )
  driver._configuration = configuration
  driver.described = description
  driver.arm.configuration = None if configuration is None else configuration.arm
  driver.gripper.configuration = None if configuration is None else configuration.gripper
  if description.has_rail:
    if driver.rail is None:
      driver.rail = RemotePreciseFlexRail(driver)
    driver.rail.configuration = None if configuration is None else configuration.rail
  else:
    driver.rail = None
  if description.has_vision:
    if driver.vision is None:
      driver.vision = RemotePreciseFlexVision(driver)
    if description.HasField("vision_configuration_json"):
      driver.vision.configuration = wire.vision_configuration_from(
        description.vision_configuration_json
      )
  else:
    driver.vision = None

  handles: Dict[str, Any] = {}
  server = device.resource_server
  for name in ("device", "base_plate", "arm", "link_1", "link_2", "gripper"):
    ref: rpb.ResourceRef = getattr(description.resources, name)
    handles[name] = (
      await server.get_by_id(ref.id)
      if server is not None and description.resources.HasField(name)
      else None
    )
  device.body = handles["device"]
  device.base_plate = handles["base_plate"]
  driver.base_plate = handles["base_plate"]
  driver.arm.resource = handles["arm"]
  driver.arm.link_1 = handles["link_1"]
  driver.arm.link_2 = handles["link_2"]
  driver.gripper.resource = handles["gripper"]
