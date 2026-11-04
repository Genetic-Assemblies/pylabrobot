"""What a served call raised, as a Connect error, and back: the client raises the same class, with
the same message, as the device would have raised in this process."""

import asyncio
from typing import Dict, List, Optional, Tuple, Type

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from protobuf.wkt import Any as AnyMessage

from pylabrobot.hamilton.star.driver import errors as star_errors
from pylabrobot.hamilton.star.driver.errors import STARFirmwareError, STARModuleError
from pylabrobot.hamilton.star.server.v1 import errors_pb2 as epb
from pylabrobot.lib.liquid_handling.errors import ChannelsDoNotFitError
from pylabrobot.resources.errors import (
  HasTipError,
  NoLocationError,
  NoTipError,
  ResourceNotFoundError,
  TooLittleLiquidError,
  TooLittleVolumeError,
)
from pylabrobot.resources.server.errors import ServerError

ERROR_TYPE = "pylabrobot.hamilton.star.server.v1.Error"
# What an aspirate or a dispense measured before it failed, beside the `Error`.
MEASUREMENTS_TYPE = "pylabrobot.hamilton.star.server.v1.PipetteMeasurements"

# Each kind and the class it is, the subclasses ahead of what they derive from.
_KINDS: List[Tuple[Type[BaseException], int, Code]] = [
  (STARFirmwareError, epb.ERROR_KIND_FIRMWARE, Code.ABORTED),
  (ServerError, epb.ERROR_KIND_RESOURCE_SERVER, Code.FAILED_PRECONDITION),
  (HasTipError, epb.ERROR_KIND_HAS_TIP, Code.FAILED_PRECONDITION),
  (NoTipError, epb.ERROR_KIND_NO_TIP, Code.FAILED_PRECONDITION),
  (TooLittleLiquidError, epb.ERROR_KIND_TOO_LITTLE_LIQUID, Code.FAILED_PRECONDITION),
  (TooLittleVolumeError, epb.ERROR_KIND_TOO_LITTLE_VOLUME, Code.FAILED_PRECONDITION),
  (ResourceNotFoundError, epb.ERROR_KIND_RESOURCE_NOT_FOUND, Code.NOT_FOUND),
  (NoLocationError, epb.ERROR_KIND_NO_LOCATION, Code.FAILED_PRECONDITION),
  (ChannelsDoNotFitError, epb.ERROR_KIND_CHANNELS_DO_NOT_FIT, Code.INVALID_ARGUMENT),
  (NotImplementedError, epb.ERROR_KIND_NOT_IMPLEMENTED, Code.UNIMPLEMENTED),
  (asyncio.TimeoutError, epb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (TimeoutError, epb.ERROR_KIND_TIMEOUT, Code.DEADLINE_EXCEEDED),
  (ConnectionError, epb.ERROR_KIND_CONNECTION, Code.UNAVAILABLE),
  (KeyError, epb.ERROR_KIND_KEY, Code.INVALID_ARGUMENT),
  (IndexError, epb.ERROR_KIND_INDEX, Code.INVALID_ARGUMENT),
  (AssertionError, epb.ERROR_KIND_ASSERTION, Code.INTERNAL),
  (TypeError, epb.ERROR_KIND_TYPE, Code.INVALID_ARGUMENT),
  (ValueError, epb.ERROR_KIND_VALUE, Code.INVALID_ARGUMENT),
  (RuntimeError, epb.ERROR_KIND_RUNTIME, Code.FAILED_PRECONDITION),
]
_CLASSES: Dict[int, Type[BaseException]] = {}
for _cls, _kind, _ in _KINDS:
  _CLASSES.setdefault(_kind, _cls)


# Each module error class and its kind.
_MODULE_KINDS: List[Tuple[Type[STARModuleError], int]] = [
  (star_errors.CommandSyntaxError, epb.MODULE_ERROR_KIND_COMMAND_SYNTAX),
  (star_errors.HardwareError, epb.MODULE_ERROR_KIND_HARDWARE),
  (star_errors.CommandNotCompletedError, epb.MODULE_ERROR_KIND_COMMAND_NOT_COMPLETED),
  (star_errors.ClotDetectedError, epb.MODULE_ERROR_KIND_CLOT_DETECTED),
  (star_errors.BarcodeUnreadableError, epb.MODULE_ERROR_KIND_BARCODE_UNREADABLE),
  (star_errors.TipTooLittleVolumeError, epb.MODULE_ERROR_KIND_TIP_TOO_LITTLE_VOLUME),
  (star_errors.TipAlreadyFittedError, epb.MODULE_ERROR_KIND_TIP_ALREADY_FITTED),
  (star_errors.HamiltonNoTipError, epb.MODULE_ERROR_KIND_HAMILTON_NO_TIP),
  (star_errors.NoCarrierError, epb.MODULE_ERROR_KIND_NO_CARRIER),
  (star_errors.NotCompletedError, epb.MODULE_ERROR_KIND_NOT_COMPLETED),
  (star_errors.DispenseWithPressureLLDError, epb.MODULE_ERROR_KIND_DISPENSE_WITH_PRESSURE_LLD),
  (star_errors.NoTeachInSignalError, epb.MODULE_ERROR_KIND_NO_TEACH_IN_SIGNAL),
  (star_errors.LoadingTrayError, epb.MODULE_ERROR_KIND_LOADING_TRAY),
  (
    star_errors.SequencedAspirationWithPressureLLDError,
    epb.MODULE_ERROR_KIND_SEQUENCED_ASPIRATION_WITH_PRESSURE_LLD,
  ),
  (
    star_errors.NotAllowedParameterCombinationError,
    epb.MODULE_ERROR_KIND_NOT_ALLOWED_PARAMETER_COMBINATION,
  ),
  (star_errors.CoverCloseError, epb.MODULE_ERROR_KIND_COVER_CLOSE),
  (star_errors.AspirationError, epb.MODULE_ERROR_KIND_ASPIRATION),
  (star_errors.WashFluidOrWasteError, epb.MODULE_ERROR_KIND_WASH_FLUID_OR_WASTE),
  (star_errors.IncubationError, epb.MODULE_ERROR_KIND_INCUBATION),
  (star_errors.TADMMeasurementError, epb.MODULE_ERROR_KIND_TADM_MEASUREMENT),
  (star_errors.NoElementError, epb.MODULE_ERROR_KIND_NO_ELEMENT),
  (star_errors.ElementStillHoldingError, epb.MODULE_ERROR_KIND_ELEMENT_STILL_HOLDING),
  (star_errors.ElementLostError, epb.MODULE_ERROR_KIND_ELEMENT_LOST),
  (
    star_errors.IllegalTargetPlatePositionError,
    epb.MODULE_ERROR_KIND_ILLEGAL_TARGET_PLATE_POSITION,
  ),
  (star_errors.IllegalUserAccessError, epb.MODULE_ERROR_KIND_ILLEGAL_USER_ACCESS),
  (star_errors.PositionNotReachableError, epb.MODULE_ERROR_KIND_POSITION_NOT_REACHABLE),
  (star_errors.UnexpectedLLDError, epb.MODULE_ERROR_KIND_UNEXPECTED_LLD),
  (star_errors.AreaAlreadyOccupiedError, epb.MODULE_ERROR_KIND_AREA_ALREADY_OCCUPIED),
  (star_errors.ImpossibleToOccupyAreaError, epb.MODULE_ERROR_KIND_IMPOSSIBLE_TO_OCCUPY_AREA),
  (star_errors.AntiDropControlError, epb.MODULE_ERROR_KIND_ANTI_DROP_CONTROL),
  (star_errors.DecapperError, epb.MODULE_ERROR_KIND_DECAPPER),
  (star_errors.DecapperHandlingError, epb.MODULE_ERROR_KIND_DECAPPER_HANDLING),
  (star_errors.StopError, epb.MODULE_ERROR_KIND_STOP),
  (star_errors.SubsystemError, epb.MODULE_ERROR_KIND_SUBSYSTEM),
  (star_errors.WrongCarrierError, epb.MODULE_ERROR_KIND_WRONG_CARRIER),
  (star_errors.NoCarrierBarcodeError, epb.MODULE_ERROR_KIND_NO_CARRIER_BARCODE),
  (star_errors.LiquidLevelError, epb.MODULE_ERROR_KIND_LIQUID_LEVEL),
  (star_errors.NotDetectedError, epb.MODULE_ERROR_KIND_NOT_DETECTED),
  (star_errors.NotAspiratedError, epb.MODULE_ERROR_KIND_NOT_ASPIRATED),
  (star_errors.ImproperDispensationError, epb.MODULE_ERROR_KIND_IMPROPER_DISPENSATION),
  (star_errors.NoLabwareError, epb.MODULE_ERROR_KIND_NO_LABWARE),
  (star_errors.UnexpectedLabwareError, epb.MODULE_ERROR_KIND_UNEXPECTED_LABWARE),
  (star_errors.WrongLabwareError, epb.MODULE_ERROR_KIND_WRONG_LABWARE),
  (star_errors.BarcodeMaskError, epb.MODULE_ERROR_KIND_BARCODE_MASK),
  (star_errors.BarcodeNotUniqueError, epb.MODULE_ERROR_KIND_BARCODE_NOT_UNIQUE),
  (star_errors.BarcodeAlreadyUsedError, epb.MODULE_ERROR_KIND_BARCODE_ALREADY_USED),
  (star_errors.KitLotExpiredError, epb.MODULE_ERROR_KIND_KIT_LOT_EXPIRED),
  (star_errors.DelimiterError, epb.MODULE_ERROR_KIND_DELIMITER),
  (star_errors.UnknownHamiltonError, epb.MODULE_ERROR_KIND_UNKNOWN_HAMILTON),
]
_MODULE_KIND_OF: Dict[Type[STARModuleError], int] = dict(_MODULE_KINDS)
_MODULE_CLASS_OF: Dict[int, Type[STARModuleError]] = {kind: cls for cls, kind in _MODULE_KINDS}


def _message(error: BaseException) -> str:
  """What the error was made with, so making it again gives the same `str()`."""
  if len(error.args) == 1 and isinstance(error.args[0], str):
    return error.args[0]
  return str(error)


def to_connect_error(error: BaseException) -> ConnectError:
  """An error a call raised, as a Connect error carrying an `Error` detail."""
  detail = epb.Error(message=_message(error))
  code = Code.UNKNOWN
  for cls, kind, kind_code in _KINDS:
    if isinstance(error, cls):
      detail.kind, code = kind, kind_code  # type: ignore[assignment]
      break
  if isinstance(error, STARFirmwareError):
    detail.firmware_reply = error.raw_response
    for module, module_error in error.errors.items():
      detail.module_errors.add(
        module=module,
        kind=_MODULE_KIND_OF[type(module_error)],
        message=module_error.message,
        trace_information=module_error.trace_information,
        raw_response=module_error.raw_response,
        raw_module=module_error.raw_module,
      )
  if isinstance(error, ServerError):
    detail.problem = error.problem
    detail.resource_name = error.resource_name
  details = [
    AnyMessage(type_url=f"type.googleapis.com/{ERROR_TYPE}", value=detail.SerializeToString())
  ]
  measurements = getattr(error, "measurements", None)
  if measurements:
    from pylabrobot.hamilton.star.server import generated_codec as codec
    from pylabrobot.hamilton.star.server.v1 import pipettes_pb2

    measured = pipettes_pb2.PipetteMeasurements(
      measurements=codec.encode_pipettes_aspirate_response(measurements).measurements
    )
    details.append(
      AnyMessage(
        type_url=f"type.googleapis.com/{MEASUREMENTS_TYPE}", value=measured.SerializeToString()
      )
    )
  return ConnectError(code, str(error), details)


def from_connect_error(error: ConnectError) -> Optional[BaseException]:
  """The error a call raised, from the Connect error it came as; None when it carries none. What
  an aspirate or a dispense measured before failing is its `measurements`, as raised."""
  raised = _raised(error)
  if raised is None:
    return None
  for item in error.details:
    if item.type_name == MEASUREMENTS_TYPE:
      from pylabrobot.hamilton.star.server import generated_codec as codec
      from pylabrobot.hamilton.star.server.v1 import pipettes_pb2

      measured = pipettes_pb2.PipetteMeasurements.FromString(item.message_bytes)
      raised.measurements = codec.decode_pipettes_aspirate_response(  # type: ignore[attr-defined]
        pipettes_pb2.PipettesAspirateResponse(measurements=measured.measurements)
      )
  return raised


def _raised(error: ConnectError) -> Optional[BaseException]:
  for item in error.details:
    if item.type_name != ERROR_TYPE:
      continue
    detail = epb.Error.FromString(item.message_bytes)
    if detail.kind == epb.ERROR_KIND_FIRMWARE:
      modules = {
        m.module: _MODULE_CLASS_OF[m.kind](
          message=m.message,
          trace_information=m.trace_information,
          raw_response=m.raw_response,
          raw_module=m.raw_module,
        )
        for m in detail.module_errors
      }
      firmware = STARFirmwareError(errors=modules, raw_response=detail.firmware_reply)
      # Its message was fixed when it was raised, before anything edited its modules' messages.
      firmware.args = (detail.message,)
      return firmware
    if detail.kind == epb.ERROR_KIND_RESOURCE_SERVER:
      return ServerError(detail.problem, detail.message, detail.resource_name)
    cls = _CLASSES.get(detail.kind, Exception)
    return cls(detail.message) if detail.message else cls()
  return None
