"""A STAR driven through a STAR server: the same API, what the server keeps, and what it refuses."""

import asyncio
import importlib.util
import inspect
import json
import os
import socket
import tempfile
import typing
import unittest

from google.protobuf import json_format
from pyqwest import Client

from pylabrobot.hamilton.star import STAR, STARlet
from pylabrobot.hamilton.star.driver.errors import STARFirmwareError, check_fw_string_error
from pylabrobot.hamilton.star.driver.features.pipettes import (
  PipetteMeasurement,
  Pipettes,
  TADMCurve,
)
from pylabrobot.hamilton.star.driver.lld_mode import LLDMode
from pylabrobot.hamilton.star.server import client, generate
from pylabrobot.hamilton.star.server.client import STARServer, remote_device
from pylabrobot.hamilton.star.server.errors import from_connect_error, to_connect_error
from pylabrobot.hamilton.star.server.serve import star_server_app
from pylabrobot.hamilton.star.server.settings import Settings, read_settings
from pylabrobot.resources import hamilton_96_tiprack_300uL_filter, hamilton_tip_carrier_L5
from pylabrobot.resources.errors import NoTipError
from pylabrobot.resources.server.asgi_transport import ASGITransport
from pylabrobot.resources.server.errors import ServerError
from pylabrobot.resources.server.v1 import types_pb2 as pb

_REMOTE = {
  "STARService": client.RemoteSTARDevice,
  "DriverService": client.RemoteSTARDriver,
  "PipettesService": client.RemotePipettes,
  "Head96Service": client.RemoteHead96,
  "Head384Service": client.RemoteHead384,
  "ISwapService": client.RemoteISWAP,
  "CoreGrippersService": client.RemoteCoreGrippers,
  "AutoloadService": client.RemoteAutoload,
  "XArmService": client.RemoteXArm,
  "FrontCoverService": client.RemoteFrontCover,
}


def _served_starlet():
  device = STARlet(simulation=True)
  return device, remote_device(STARServer.local(device), device.resource_server, "STARlet")


class ApiTests(unittest.TestCase):
  def test_every_method_is_served_with_its_own_signature(self):
    for service in generate.SERVICES:
      cls = service.cls
      remote = dict(inspect.getmembers(_REMOTE[service.name]))
      own = dict(inspect.getmembers(cls))
      served = {rpc.python for rpc in generate.rpcs(service)}
      for name in generate.served_methods(cls):
        with self.subTest(method=f"{cls.__name__}.{name}"):
          self.assertIn(name, served)
          self.assertIsNot(remote[name], own[name])
          self.assertEqual(
            [
              (p.name, p.kind, p.default)
              for p in inspect.signature(remote[name]).parameters.values()
            ],
            [(p.name, p.kind, p.default) for p in inspect.signature(own[name]).parameters.values()],
          )
          self.assertEqual(typing.get_type_hints(remote[name]), typing.get_type_hints(own[name]))
          self.assertEqual(remote[name].__doc__, own[name].__doc__)


class ErrorTests(unittest.TestCase):
  def back(self, error: BaseException) -> BaseException:
    raised = from_connect_error(to_connect_error(error))
    assert raised is not None
    return raised

  def test_a_firmware_error_comes_back_module_by_module(self):
    with self.assertRaises(STARFirmwareError) as caught:
      check_fw_string_error("C0TPid0000er99/00 P308/75")
    error = caught.exception
    (module,) = error.errors
    error.errors[module].message += " (edited after it was raised)"
    raised = self.back(error)
    assert isinstance(raised, STARFirmwareError)
    self.assertEqual(str(raised), str(error))
    self.assertEqual(raised.raw_response, error.raw_response)
    self.assertIs(type(raised.errors[module]), type(error.errors[module]))

  def test_a_refusal_and_plain_errors_come_back_as_they_were(self):
    for error in (
      ServerError(pb.PROBLEM_NO_TIP, "no tip there", "A1"),
      NoTipError("tips_A1 holds no tip"),
      ValueError("channel must be in [0, 7], is 9"),
      KeyError("A13"),
      RuntimeError(),
    ):
      with self.subTest(error=repr(error)):
        raised = self.back(error)
        self.assertIs(type(raised), type(error))
        self.assertEqual(str(raised), str(error))
    refusal = self.back(ServerError(pb.PROBLEM_NO_TIP, "no tip there", "A1"))
    assert isinstance(refusal, ServerError)
    self.assertEqual((refusal.problem, refusal.resource_name), (pb.PROBLEM_NO_TIP, "A1"))


class ServedTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.device, self.star = _served_starlet()
    await self.star.setup()

  async def test_settings_and_constants_are_read_but_not_assigned_on_a_client(self):
    assert self.star.pipettes is not None and self.device.pipettes is not None
    self.assertEqual(
      self.star.pipettes.default_minimum_traverse_height,
      self.device.pipettes.default_minimum_traverse_height,
    )
    with self.assertRaisesRegex(AttributeError, "settings file"):
      self.star.pipettes.default_minimum_traverse_height = 200.0
    with self.assertRaisesRegex(AttributeError, "constant"):
      self.star.pipettes.ztouch_cascade_interval = 0.0

  async def test_what_a_call_changes_on_the_server_reaches_the_client(self):
    assert self.star.iswap is not None and self.device.iswap is not None
    self.device.iswap.configuration.elbow_drive_predefined_increments = None
    await self.star.iswap.request_firmware_version()
    self.assertIsNone(self.star.iswap.configuration.elbow_drive_predefined_increments)
    positions = await self.star.iswap.elbow_drive_request_positions()
    self.assertEqual(self.star.iswap.configuration.elbow_drive_predefined_increments, positions)

  async def test_a_failed_call_raises_what_the_device_raises(self):
    assert self.star.deck is not None and self.star.pipettes is not None
    carrier = await self.star.deck.assign_child_resource(
      hamilton_tip_carrier_L5(name="tc"), track=1
    )
    tips = await carrier[1].assign_child_resource(hamilton_96_tiprack_300uL_filter(name="tips"))
    await self.star.pipettes.pick_up_tips(tips.get_tip_spots("A1:H1"))
    with self.assertRaises(NoTipError):
      await self.star.pipettes.pick_up_tips(tips.get_tip_spots("A1:H1"))


class SettingsTests(unittest.IsolatedAsyncioTestCase):
  async def test_the_servers_settings_are_in_place_after_setup_and_a_client_reads_them(self):
    settings = json_format.ParseDict(
      {
        "pipettes": {"default_minimum_traverse_height": 200.0},
        "head96": {"default_mix_swap_speed": 7.5},
      },
      Settings(),
    )
    device = STARlet(simulation=True)
    star = remote_device(STARServer.local(device, settings), device.resource_server, "STARlet")
    await star.setup()
    assert device.pipettes is not None and device.head96 is not None
    assert star.pipettes is not None and star.head96 is not None
    self.assertEqual(device.pipettes.default_minimum_traverse_height, 200.0)
    self.assertEqual(device.head96.default_mix_swap_speed, 7.5)
    self.assertEqual(star.pipettes.default_minimum_traverse_height, 200.0)
    self.assertEqual(star.head96.default_mix_swap_speed, 7.5)
    # Those not given keep the code's.
    self.assertEqual(star.pipettes.default_z_speed, Pipettes.default_z_speed)

  def test_a_settings_file_names_only_settings(self):
    with tempfile.TemporaryDirectory() as directory:
      path = os.path.join(directory, "settings.json")
      with open(path, "w") as f:
        json.dump({"pipettes": {"default_minimum_traverse_height": 200.0}}, f)
      self.assertEqual(read_settings(path).pipettes.default_minimum_traverse_height, 200.0)
      with open(path, "w") as f:
        json.dump({"pipettes": {"ztouch_cascade_interval": 0.0}}, f)
      with self.assertRaises(ValueError):
        read_settings(path)


class HeaderTests(unittest.IsolatedAsyncioTestCase):
  async def test_a_connections_headers_go_with_every_call(self):
    device = STARlet(simulation=True)
    app = star_server_app(device)
    seen = []

    async def recording(scope, receive, send):
      seen.append((scope["path"].rsplit("/", 1)[-1], dict(scope["headers"]).get(b"authorization")))
      await app(scope, receive, send)

    star_server = STARServer(
      "http://star.test",
      Client(transport=ASGITransport(recording)),
      headers={"authorization": "Bearer token"},
    )
    star = STARlet(star_server=star_server, resource_server=device.resource_server)
    await star.setup()
    self.assertIn("Describe", [path for path, _ in seen])
    self.assertEqual({token for _, token in seen}, {b"Bearer token"})


class FactoryTests(unittest.IsolatedAsyncioTestCase):
  async def test_what_the_server_decides_is_not_given_with_it(self):
    with self.assertRaises(ValueError):
      STARlet(
        star_server="http://127.0.0.1:1", resource_server="http://127.0.0.1:2", simulation=True
      )

  async def test_a_served_star_is_given_its_resource_server(self):
    with self.assertRaisesRegex(ValueError, "resource_server"):
      STARlet(star_server="http://127.0.0.1:1")

  async def test_the_served_device_is_the_one_asked_for(self):
    device = STARlet(simulation=True)
    star = STAR(star_server=STARServer.local(device), resource_server=device.resource_server)
    with self.assertRaisesRegex(ValueError, "serves a STARlet, not a STAR"):
      await star.setup()


def _free_port() -> int:
  with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    return int(s.getsockname()[1])


@unittest.skipIf(importlib.util.find_spec("uvicorn") is None, "serving needs uvicorn")
class NetworkTests(unittest.IsolatedAsyncioTestCase):
  async def test_a_device_served_on_a_port(self):
    from pylabrobot.hamilton.star.server.serve import serve

    port, resource_port = _free_port(), _free_port()
    served = asyncio.create_task(
      serve(STARlet(simulation=True), port=port, resource_port=resource_port)
    )
    try:
      for p in (port, resource_port):
        for _ in range(100):
          try:
            _, writer = await asyncio.open_connection("127.0.0.1", p)
            writer.close()
            break
          except OSError:
            await asyncio.sleep(0.05)
      star = STARlet(
        star_server=f"http://127.0.0.1:{port}",
        resource_server=f"http://127.0.0.1:{resource_port}",
      )
      await star.setup()
      assert star.pipettes is not None
      self.assertEqual(len(await star.pipettes.request_y_positions()), 8)
      await star.stop()
    finally:
      served.cancel()
      await asyncio.gather(served, return_exceptions=True)


class MeasurementErrorTests(unittest.TestCase):
  def test_what_a_failed_aspiration_measured_comes_back_with_its_error(self):
    error = RuntimeError("channel 1 found no liquid in plate_D1")
    error.measurements = [  # type: ignore[attr-defined]
      PipetteMeasurement(channel=0, lld_mode=LLDMode.CAPACITIVE, liquid_height=7.25, tadm=None),
      PipetteMeasurement(
        channel=1,
        lld_mode=LLDMode.CAPACITIVE,
        liquid_height=None,
        tadm=TADMCurve("0001", "aspirate", True, [0, -40, -80, -40]),
      ),
    ]
    raised = from_connect_error(to_connect_error(error))
    assert raised is not None
    self.assertIsInstance(raised, RuntimeError)
    self.assertEqual(raised.measurements, error.measurements)  # type: ignore[attr-defined]

  def test_an_error_without_measurements_carries_none(self):
    raised = from_connect_error(to_connect_error(ValueError("no")))
    self.assertFalse(hasattr(raised, "measurements"))
