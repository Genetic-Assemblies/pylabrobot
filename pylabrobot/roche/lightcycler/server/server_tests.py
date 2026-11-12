import asyncio
import inspect
import unittest
from typing import Any, AsyncIterator, Dict, List
from unittest import mock

from connectrpc.code import Code
from connectrpc.errors import ConnectError

from pylabrobot.legacy.thermocycling.standard import Protocol, Stage, Step
from pylabrobot.roche.lightcycler import (
  CommandFailedError,
  ExperimentFailedError,
  LightCycler480,
  LightCycler480Simulator,
  LightCyclerStep,
  LightCyclerTimeoutError,
)
from pylabrobot.roche.lightcycler.server import (
  LightCyclerServer,
  RemoteLightCycler480,
  lightcycler_server_app,
)
from pylabrobot.roche.lightcycler.server import __main__ as entry
from pylabrobot.roche.lightcycler.server.errors import from_error, to_error
from pylabrobot.roche.lightcycler.server.v1 import lightcycler_pb2 as pb
from pylabrobot.roche.lightcycler.wire import START_RUN


def reads(*temperatures: float, repeats: int = 1) -> Protocol:
  steps: List[Step] = [
    LightCyclerStep(temperature=[t], hold_seconds=1.0, acquire=True) for t in temperatures
  ]
  return Protocol([Stage(steps, repeats=repeats)])


class _DropsTheFirstRunStream:
  """The service, with the first experiment stream it gives dropping after its first update."""

  def __init__(self, service: Any) -> None:
    self._service = service
    self.dropped = False

  def __getattr__(self, name: str) -> Any:
    return getattr(self._service, name)

  async def run_experiment(self, request: pb.ExperimentRequest) -> AsyncIterator[Any]:
    async for update in self._service.run_experiment(request):
      yield update
      if not self.dropped:
        self.dropped = True
        raise ConnectError(Code.UNAVAILABLE, "connection reset")


class ParityTests(unittest.TestCase):
  def test_every_public_coroutine_is_a_call(self):
    remote = dict(inspect.getmembers(RemoteLightCycler480))
    for name, method in inspect.getmembers(LightCycler480):
      public = not name.startswith("_")
      if not public or not (
        inspect.iscoroutinefunction(method) or inspect.isasyncgenfunction(method)
      ):
        continue
      with self.subTest(name):
        self.assertTrue(remote[name].__qualname__.startswith("RemoteLightCycler480."))
        self.assertEqual(inspect.signature(remote[name]), inspect.signature(method))

  def test_a_served_lightcycler_refuses_what_its_server_decides(self):
    server = LightCyclerServer.in_process(lightcycler_server_app(LightCycler480(simulation=True)))
    self.assertIsInstance(LightCycler480(lightcycler_server=server), RemoteLightCycler480)
    with self.assertRaisesRegex(ValueError, "what its server makes it"):
      LightCycler480(host="192.168.95.41", lightcycler_server=server)
    with self.assertRaisesRegex(RuntimeError, "on its server"):
      _ = LightCycler480(lightcycler_server=server).driver

  def test_errors_go_over_as_their_class(self):
    for error in [
      CommandFailedError("ThermalParams", ["3", "3", "0"]),
      ExperimentFailedError("AB" * 16, "TimeoutError: read 1 was not there"),
      LightCyclerTimeoutError("SubsysStatus", 3.0),
      KeyError("no experiment X"),
      ValueError("well_count must be 96 or 384, not 48"),
      RuntimeError("the tray is open"),
      ConnectionError("the LightCycler's status connection closed"),
    ]:
      with self.subTest(type(error).__name__):
        again = from_error(to_error(error))
        self.assertIs(type(again), type(error))
        self.assertEqual(str(again), str(error))


class ServedTests(unittest.IsolatedAsyncioTestCase):
  async def asyncSetUp(self):
    self.local = LightCycler480(simulation=True)
    self.local.tray_poll_interval = 0.01
    assert isinstance(self.local.driver, LightCycler480Simulator)
    self.instrument = self.local.driver.instrument
    await self.local.setup()
    self.server = LightCyclerServer.in_process(
      lightcycler_server_app(self.local, progress_interval=0.01)
    )
    remote = LightCycler480(lightcycler_server=self.server)
    assert isinstance(remote, RemoteLightCycler480)
    self.remote = remote
    self.remote.reconnect_delay = 0.0
    await self.remote.setup()

  async def asyncTearDown(self):
    await self.remote.stop()
    await self.local.stop()

  def runs_started(self) -> int:
    return len([p for _, p in self.instrument.received if p.type == START_RUN])

  async def test_the_tray_is_moved_through_the_server(self):
    await self.remote.open_tray()
    await self.remote.close_tray()
    tray = await self.remote.request_tray_state()
    self.assertEqual((tray.open, tray.plate_loaded), (False, True))
    self.assertEqual(tray, await self.local.request_tray_state())
    status = await self.remote.request_status()
    self.assertEqual(status, await self.local.request_status())
    self.assertEqual(status.state, 10)

  async def test_a_remote_run_is_the_local_experiment(self):
    await self.remote.close_tray()
    protocol = Protocol(
      [
        Stage([Step(temperature=[95], hold_seconds=2.0)], repeats=1),
        Stage(
          [LightCyclerStep([95], 1.0), LightCyclerStep([60], 1.0, rate=2.5, acquire=True)],
          repeats=2,
        ),
      ]
    )
    experiment = await self.remote.run_experiment(protocol, well_count=96, volume=10)
    self.assertEqual(experiment, await self.local.get_experiment(experiment.id))
    self.assertEqual(experiment, await self.remote.get_experiment(experiment.id))
    self.assertEqual(experiment.status, "complete")
    self.assertEqual(
      [(a.cycle, len(a.values)) for a in experiment.acquisitions], [(0, 96), (1, 96)]
    )
    self.assertEqual(await self.remote.list_experiments(), await self.local.list_experiments())

  async def test_what_the_device_raises_the_client_raises(self):
    with self.assertRaisesRegex(RuntimeError, "tray is open"):
      await self.remote.start_experiment(reads(37))
    await self.remote.close_tray()
    with self.assertRaisesRegex(ValueError, "one time"):
      bad = Protocol([Stage([LightCyclerStep([37], 1.0), LightCyclerStep([37], 2.0)], 1)])
      await self.remote.run_experiment(bad)
    with self.assertRaises(KeyError):
      await self.remote.get_experiment("F" * 32)
    with self.assertRaises(KeyError):
      await self.remote.wait_for_experiment("F" * 32)
    self.local.tray_button = None
    with self.assertRaisesRegex(RuntimeError, "no tray button"):
      await self.remote.open_tray()

  async def test_an_experiment_that_fails_raises_its_error_on_the_client(self):
    await self.remote.close_tray()
    self.instrument.seconds_per_second = 0.05
    started = await self.remote.start_experiment(reads(37, 37))
    await asyncio.sleep(0.02)
    await self.instrument.stop()
    with self.assertRaises(ExperimentFailedError) as raised:
      await self.remote.wait_for_experiment(started)
    self.assertEqual(raised.exception.experiment_id, started)

  async def test_an_experiment_is_streamed_read_by_read(self):
    await self.remote.close_tray()
    self.instrument.seconds_per_second = 0.02
    started = await self.remote.start_experiment(reads(37, 37, 37))
    seen = [e async for e in self.remote.watch_experiment(started)]
    self.assertEqual([len(e.acquisitions) for e in seen][-1], 3)
    self.assertEqual([a.number for a in seen[-1].acquisitions], [1, 2, 3])
    self.assertIn("running", [e.status for e in seen])
    # Nothing changed between some updates: the stream says so every progress interval.
    self.assertGreater(len(seen), 5)

  async def test_an_experiment_finishes_on_the_server_when_its_client_goes(self):
    await self.remote.close_tray()
    self.instrument.seconds_per_second = 0.02
    request = pb.ExperimentRequest(
      protocol=self.remote._request(reads(37, 37), 384, 20, None).protocol
    )
    request.experiment_id = "AB" * 16
    stream = self.server.service.run_experiment(request)
    first = await stream.__anext__()
    self.assertNotEqual(first.experiment.status, pb.EXPERIMENT_STATUS_COMPLETE)
    await stream.aclose()  # type: ignore[attr-defined]
    done = await self.local.wait_for_experiment("AB" * 16, timeout=5)
    self.assertEqual(len(done.acquisitions), 2)

  async def test_a_dropped_run_stream_is_rejoined_by_its_id_and_not_run_twice(self):
    await self.remote.close_tray()
    self.instrument.seconds_per_second = 0.02
    dropping = _DropsTheFirstRunStream(self.server.service)
    self.remote.server.service = dropping  # type: ignore[assignment]
    experiment = await self.remote.run_experiment(reads(37, 37, 37))
    self.assertTrue(dropping.dropped)
    self.assertEqual(self.runs_started(), 1)
    self.assertEqual([a.number for a in experiment.acquisitions], [1, 2, 3])

  async def test_a_run_retried_by_its_id_joins_the_one_running(self):
    await self.remote.close_tray()
    self.instrument.seconds_per_second = 0.02
    experiment_id = "0123456789ABCDEF0123456789ABCDEF"
    a, b = await asyncio.gather(
      self.remote.run_experiment(reads(37, 37), experiment_id=experiment_id),
      self.remote.run_experiment(reads(37, 37), experiment_id=experiment_id),
    )
    self.assertEqual(a, b)
    self.assertEqual(self.runs_started(), 1)
    with self.assertRaisesRegex(ValueError, "another protocol"):
      await self.remote.start_experiment(reads(50), experiment_id=experiment_id)

  async def test_another_client_follows_an_experiment_by_its_id(self):
    await self.remote.close_tray()
    self.instrument.seconds_per_second = 0.02
    started = await self.remote.start_experiment(reads(37, 37))
    other = LightCycler480(lightcycler_server=self.server)
    with self.assertRaises(TimeoutError):
      await other.wait_for_experiment(started, timeout=0.001)
    done = await other.wait_for_experiment(started)
    self.assertEqual(len(done.acquisitions), 2)

  async def test_the_instruments_logs_are_read_through_the_server(self):
    await self.remote.open_tray()
    await self.remote.close_tray()
    for _ in range(100):
      if await self.local.request_logs():
        break
      await asyncio.sleep(0.01)
    self.assertEqual(await self.remote.request_logs(), await self.local.request_logs())
    self.assertTrue(await self.remote.request_logs())


class CommandLineTests(unittest.TestCase):
  def test_simulation_serves_a_simulated_lightcycler_on_8097(self):
    served: Dict[str, Any] = {}

    async def serve(lightcycler: LightCycler480, host: str, port: int) -> None:
      served.update(lightcycler=lightcycler, host=host, port=port)
      served["status"] = await lightcycler.request_status()

    with mock.patch.object(entry, "serve", serve):
      entry.main(["--simulation"])
    self.assertEqual((served["host"], served["port"]), ("127.0.0.1", 8097))
    self.assertEqual(served["status"].firmware_version, "1.8.6.1501")
    self.assertIsNotNone(served["lightcycler"].tray_button)


if __name__ == "__main__":
  unittest.main()
