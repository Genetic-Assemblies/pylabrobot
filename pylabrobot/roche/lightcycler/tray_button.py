"""What presses the LightCycler's tray button.

The instrument's TCP protocol, as far as it is known, has no command that moves the tray: the
button on its front does, each press moving it out or in. flo4 mounted a SwitchBot Bot (the
"Fingerbot") on the button and pressed it over Bluetooth LE; `SwitchBotBot` is a port of flo4's
driver for it (`lib/switchbot`), and needs `bleak`.
"""

import asyncio
import logging
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


class TrayButton(Protocol):
  """Presses the tray button once."""

  async def press(self) -> None: ...


# The SwitchBot Bot's GATT characteristics for commands and for answers, in service
# cba20d00-224d-11e6-9fb8-0002a5d5c51b.
_COMMAND_CHARACTERISTIC = "cba20002-224d-11e6-9fb8-0002a5d5c51b"
_ANSWER_CHARACTERISTIC = "cba20003-224d-11e6-9fb8-0002a5d5c51b"
# 0x57 prefixes a command, 0x01 is the control family, and in press mode 0x01 taps the button.
_PRESS = bytes([0x57, 0x01, 0x01])


class SwitchBotBot:
  """A SwitchBot Bot in press mode, mounted on the tray button, pressed over Bluetooth LE.

  Each press scans for the bot, connects, subscribes to its answers (it acts on no command
  without), writes the press, waits for the answer and disconnects. The bot's mode is set in the
  SwitchBot app; a bot in switch mode holds the button down instead.
  """

  def __init__(
    self,
    address: str,
    adapter: Optional[str] = None,
    scan_timeout: float = 10.0,
    answer_timeout: float = 5.0,
  ) -> None:
    """
    Args:
      address: the bot's Bluetooth address, `C1:23:45:67:89:AB` say.
      adapter: the Bluetooth adapter to use on Linux, `hci1` say; the default one when not given.
      scan_timeout: how long to look for the bot, in seconds.
      answer_timeout: how long to wait for it to answer a press, in seconds.
    """
    self.address = address
    self.adapter = adapter
    self.scan_timeout = scan_timeout
    self.answer_timeout = answer_timeout

  async def press(self) -> None:
    """Tap the button once.

    Raises:
      ImportError: `bleak` is not installed.
      ConnectionError: The bot was not found.
      TimeoutError: It did not answer the press.
    """
    try:
      from bleak import BleakClient, BleakScanner  # type: ignore[import-not-found,unused-ignore]
    except ImportError as error:
      raise ImportError("pressing a SwitchBot Bot needs bleak: pip install bleak") from error

    options: dict = {} if self.adapter is None else {"adapter": self.adapter}
    device = await BleakScanner.find_device_by_address(
      self.address, timeout=self.scan_timeout, **options
    )
    if device is None:
      raise ConnectionError(f"no SwitchBot Bot at {self.address} was found")
    answered: "asyncio.Future[bytes]" = asyncio.get_running_loop().create_future()

    def on_answer(_: Any, data: bytearray) -> None:
      if not answered.done():
        answered.set_result(bytes(data))

    async with BleakClient(device, **options) as client:
      await client.start_notify(_ANSWER_CHARACTERISTIC, on_answer)
      await client.write_gatt_char(_COMMAND_CHARACTERISTIC, _PRESS, response=False)
      try:
        answer = await asyncio.wait_for(answered, timeout=self.answer_timeout)
      except asyncio.TimeoutError as error:
        raise TimeoutError(f"the SwitchBot Bot at {self.address} did not answer") from error
    logger.info("[lightcycler] pressed the tray button (bot answered %s)", answer.hex())
