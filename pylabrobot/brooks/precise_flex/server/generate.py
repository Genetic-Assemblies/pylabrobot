"""Write the PreciseFlex server's generated files: `python -m pylabrobot.brooks.precise_flex.server.generate`.

Run it, then `make generate-rpc`, whenever a served method's signature changes; `server_tests.py`
fails while the files are not what this writes. It writes, for every served class:

- `v1/<service>.proto`: the service, one RPC per public coroutine, each request one field per
  argument named as the argument is, each response the result in `value` (a tuple's in `values`).
  A field keeps the number the file already gave it, so a client built against an earlier file
  still reads it; a new one takes the next.
- `generated_handlers.py`: each service's handlers, every one a call on the served device.
- `generated_remote.py`: the client classes, every public coroutine a call to the server, with the
  method's own signature.

How a value goes over follows from the method's annotation (`v1/types.proto` says the rules); the
hand-written messages in `types.proto`, `description.proto`, `errors.proto` and `positions.proto`
are not written here. This reads the methods' signatures and annotations to write the code; the
code it writes reads none of them.
"""

from __future__ import annotations

import ast
import builtins
import collections.abc
import dataclasses
import inspect
import os
import re
import textwrap
import typing
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from pylabrobot.brooks.precise_flex import kinematics
from pylabrobot.brooks.precise_flex.device import PreciseFlexDevice
from pylabrobot.brooks.precise_flex.driver.configuration import PreciseFlexConfiguration
from pylabrobot.brooks.precise_flex.driver.features.arm import MotionProfile, PreciseFlexArm
from pylabrobot.brooks.precise_flex.driver.features.gripper import PreciseFlexGripper
from pylabrobot.brooks.precise_flex.driver.features.rail import PreciseFlexRail
from pylabrobot.brooks.precise_flex.driver.features.vision import (
  PreciseFlexVision,
  StereoParameters,
  VisionConfiguration,
)
from pylabrobot.brooks.precise_flex.driver.master import PreciseFlexDriver
from pylabrobot.brooks.precise_flex.kinematics import (
  PF400Params,
  PreciseFlexAxis,
  PreciseFlexCartesianPose,
  PreciseFlexPose,
)
from pylabrobot.resources.coordinate import Coordinate

_PKG = "pylabrobot.brooks.precise_flex.server.v1"
_HERE = os.path.dirname(os.path.abspath(__file__))
_NoneType = type(None)


# -- what is served ------------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Service:
  """One service: the class whose methods it serves.

  Attributes:
    name: the service's name in the `.proto`.
    cls: the class whose methods it serves.
    file: the `.proto` file it is in, and the stem of its generated modules.
    prefix: what its messages' names start with.
    target: what the server's handlers call its methods on, on what the server serves.
  """

  name: str
  cls: type
  file: str
  prefix: str
  target: str


SERVICES = [
  Service("PreciseFlexService", PreciseFlexDevice, "precise_flex", "PreciseFlex", "device"),
  Service("DriverService", PreciseFlexDriver, "driver", "Driver", "driver()"),
  Service("ArmService", PreciseFlexArm, "arm", "Arm", "arm()"),
  Service("GripperService", PreciseFlexGripper, "gripper", "Gripper", "gripper()"),
  Service("RailService", PreciseFlexRail, "rail", "Rail", "rail()"),
  Service("VisionService", PreciseFlexVision, "vision", "Vision", "vision()"),
]


def _is_deprecated(fn: Callable[..., Any]) -> bool:
  """Whether a method is a deprecated alias: it warns, and calls the method it stands for, which
  a client inherits as it is."""
  return "is deprecated" in inspect.getsource(inspect.unwrap(fn))


def served_methods(cls: type) -> List[str]:
  """The methods of a class that the server serves: every public coroutine it defines, but the
  deprecated aliases. For the device, only those that are its own: what it carries is reached
  through its driver."""
  if cls is PreciseFlexDevice:
    return ["setup", "stop"]
  return [
    name
    for name, fn in inspect.getmembers(cls, inspect.iscoroutinefunction)
    if not name.startswith("_") and not _is_deprecated(fn)
  ]


# -- how a value goes over -----------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Kind:
  """How a value of one type goes over.

  Attributes:
    proto: its type in the `.proto`.
    shape: "scalar", "message", "repeated" or "map": how a field of it is set.
    to: an expression, of `{v}` the value, for what the field is set to.
    from_: an expression, of `{m}` the field, for the value.
    presence: whether a field of it has presence of its own (a message does).
  """

  proto: str
  shape: str
  to: str = "{v}"
  from_: str = "{m}"
  presence: bool = False


def _message(proto: str, name: str) -> Kind:
  return Kind(proto, "message", f"wire.{name}_to({{v}})", f"wire.{name}_from({{m}})", True)


def _enum(proto: str, name: str) -> Kind:
  return Kind(proto, "scalar", f"wire.{name}_to({{v}})", f"wire.{name}_from({{m}})")


_SCALARS = {bool: "bool", int: "int64", float: "double", str: "string", bytes: "bytes"}
_LITERALS = {
  frozenset({"right", "left"}): _enum("ElbowOrientation", "elbow_orientation"),
  frozenset({"cw", "ccw"}): _enum("Wrist", "wrist"),
  frozenset({"pc", "verbose"}): _enum("ResponseMode", "response_mode"),
  frozenset({"controller", "vision"}): _enum("CommandServer", "command_server"),
}
_CLASSES: Dict[Any, Kind] = {
  Coordinate: _message("Coordinate", "coordinate"),
  PreciseFlexCartesianPose: _message("CartesianPose", "cartesian_pose"),
  PreciseFlexPose: _message("Pose", "pose"),
  MotionProfile: _message("MotionProfile", "motion_profile"),
  PF400Params: _message("KinematicParameters", "kinematic_parameters"),
  StereoParameters: _message("StereoParameters", "stereo_parameters"),
  PreciseFlexAxis: _enum("Axis", "axis"),
  PreciseFlexConfiguration: Kind(
    "string", "scalar", "wire.configuration_to({v})", "wire.configuration_from({m})"
  ),
  VisionConfiguration: Kind(
    "string", "scalar", "wire.vision_configuration_to({v})", "wire.vision_configuration_from({m})"
  ),
}
_IMAGE = _message("Image", "image")
_PARAMETER = _message("ParameterValue", "parameter_value")


def _strip_optional(hint: Any) -> Tuple[Any, bool]:
  if typing.get_origin(hint) is typing.Union and _NoneType in typing.get_args(hint):
    rest = [arg for arg in typing.get_args(hint) if arg is not _NoneType]
    return (rest[0] if len(rest) == 1 else typing.Union[tuple(rest)]), True
  return hint, False


def kind_of(hint: Any) -> Kind:
  """How a value of a type (not None) goes over.

  Raises:
    TypeError: If no rule says.
  """
  if hint is inspect.Parameter.empty:
    return _PARAMETER
  if hint in _SCALARS:
    return Kind(_SCALARS[hint], "scalar")
  if hint in _CLASSES:
    return _CLASSES[hint]
  if isinstance(hint, str) or getattr(hint, "__forward_arg__", None) == "np.ndarray":
    return _IMAGE
  origin, args = typing.get_origin(hint), typing.get_args(hint)
  if origin is typing.Literal and all(isinstance(a, str) for a in args):
    return _LITERALS[frozenset(args)]
  if origin is typing.Union:
    members = [typing.get_origin(a) for a in args]
    if members == [typing.Literal, None] and args[1] is int:
      return _message("Camera", "camera")
  if origin is dict and args[0] is PreciseFlexAxis:
    if args[1] is float:
      return _message("JointState", "joint_state")
    return _message("JointLimits", "joint_limits")
  if origin is dict and args == (str, List[str]):
    return Kind("StringList", "map", "wire.string_lists_to({v})", "wire.string_lists_from({m})")
  if origin in (list, collections.abc.Sequence):
    item = kind_of(args[0])
    to = item.to.format(v="item")
    from_ = item.from_.format(m="item")
    return Kind(item.proto, "repeated", f"[{to} for item in {{v}}]", f"[{from_} for item in {{m}}]")
  if origin is tuple and args and args[-1] is not Ellipsis and len(set(args)) == 1:
    each = ", ".join(f"{{m}}[{i}]" for i in range(len(args)))
    return Kind(_SCALARS[args[0]], "repeated", "list({v})", f"({each})")
  if origin is tuple and args == (str, bytes):
    return _message("VisionServerResult", "vision_server_result")
  raise TypeError(f"no rule says how a {hint!r} goes over")


@dataclasses.dataclass(frozen=True)
class Field:
  """A request's field for an argument, or a response's for a result.

  Attributes:
    name: the argument's name; `value` or `values` for a result.
    kind: how its value goes over.
    label: "", "optional" or "repeated", as the `.proto` writes it.
    may_be_none: whether its value may be None: unset, or for `wrapped`, set with `value` unset.
    wrapped: the `Optional...` message it is held in, for a value that may be None where the
      default is not.
    required: whether the argument has no default, so a request always carries it.
  """

  name: str
  kind: Kind
  label: str
  may_be_none: bool = False
  wrapped: Optional[str] = None
  required: bool = True

  @property
  def proto(self) -> str:
    if self.wrapped is not None:
      return self.wrapped
    if self.kind.shape == "map":
      return f"map<string, {self.kind.proto}>"
    return self.kind.proto


def _field(name: str, hint: Any, default: Any) -> Field:
  """The field an argument is, from its annotation and its default."""
  inner, may_be_none = _strip_optional(hint)
  if typing.get_origin(inner) in (list, collections.abc.Sequence) and may_be_none:
    item = kind_of(typing.get_args(inner)[0])
    if item.proto != "int64":
      raise TypeError(f"no rule says how a {hint!r} goes over")
    kind = Kind("IntList", "message", "{v}", "list({m}.values)", True)
    return Field(name, kind, "", True, required=default is inspect.Parameter.empty)
  kind = kind_of(inner)
  required = default is inspect.Parameter.empty
  if may_be_none and default is not None and not required:
    if kind.proto != "double":
      raise TypeError(f"no rule says how a {hint!r} defaulting to {default!r} goes over")
    return Field(name, kind, "", True, wrapped="OptionalDouble", required=False)
  if kind.shape in ("repeated", "map"):
    return Field(name, kind, "repeated" if kind.shape == "repeated" else "", may_be_none)
  label = "optional" if not kind.presence and (may_be_none or not required) else ""
  return Field(name, kind, label, may_be_none, required=required)


def _result(hint: Any) -> Optional[Field]:
  """The response's field for a method's result; None for a method that returns nothing."""
  if hint is None or hint is _NoneType or hint is inspect.Signature.empty:
    return None
  inner, may_be_none = _strip_optional(hint)
  kind = kind_of(inner)
  if kind.shape == "repeated":
    return Field("values", kind, "repeated")
  label = "optional" if may_be_none and not kind.presence else ""
  return Field("value", kind, label, may_be_none)


# -- reading a method ----------------------------------------------------------------------------


def _hints(fn: Callable[..., Any]) -> Dict[str, Any]:
  """A method's annotations, the ones that name what is imported only for type checking left as
  their text."""
  fn = inspect.unwrap(fn)
  localns = {"kinematics": kinematics, "PreciseFlexConfiguration": PreciseFlexConfiguration}
  hints: Dict[str, Any] = {}
  for name, annotation in fn.__annotations__.items():
    if annotation == "np.ndarray":
      hints[name] = annotation
      continue
    holder = typing.get_type_hints(
      _Holder(name, annotation), globalns=fn.__globals__, localns=localns
    )
    hints[name] = holder[name]
  return hints


class _Holder:
  """One annotation, as `typing.get_type_hints` reads them."""

  def __init__(self, name: str, annotation: Any):
    self.__annotations__ = {name: annotation}


def _def_node(fn: Callable[..., Any]) -> ast.AsyncFunctionDef:
  source = textwrap.dedent(inspect.getsource(inspect.unwrap(fn)))
  node = ast.parse(source).body[0]
  assert isinstance(node, ast.AsyncFunctionDef)
  return node


@dataclasses.dataclass
class RPC:
  """One RPC: the method it calls, and its request's and response's fields."""

  service: Service
  python: str
  fn: Callable[..., Any]
  fields: List[Field]
  result: Optional[Field]
  doc: str

  @property
  def name(self) -> str:
    return "".join(part[:1].upper() + part[1:] for part in self.python.split("_"))

  @property
  def request(self) -> str:
    return f"{self.service.prefix}{self.name}Request"

  @property
  def response(self) -> str:
    return f"{self.service.prefix}{self.name}Response"


def rpcs(service: Service) -> List[RPC]:
  """Every RPC of a service, in the order its methods are named."""
  made = []
  for name in served_methods(service.cls):
    fn = getattr(service.cls, name)
    signature = inspect.signature(fn)
    hints = _hints(fn)
    fields = []
    for parameter in list(signature.parameters.values())[1:]:
      if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
        raise TypeError(f"{service.cls.__name__}.{name} takes *args or **kwargs")
      hint = hints.get(parameter.name, inspect.Parameter.empty)
      fields.append(_field(parameter.name, hint, parameter.default))
    result = _result(hints.get("return", inspect.Signature.empty))
    doc = inspect.getdoc(fn) or ""
    made.append(RPC(service, name, fn, fields, result, doc.split("\n\n")[0]))
  return made


# -- the .proto ----------------------------------------------------------------------------------


def _numbers(path: str) -> Dict[str, Dict[str, int]]:
  """The number of each field of each message a `.proto` file already has."""
  if not os.path.exists(path):
    return {}
  numbers: Dict[str, Dict[str, int]] = {}
  message: Optional[str] = None
  with open(path, encoding="utf-8") as f:
    for line in f:
      opened = re.match(r"message (\w+) \{", line)
      if opened:
        message = opened.group(1)
        numbers[message] = {}
        continue
      field = re.match(r"\s+(?:optional |repeated )?\S+ (\w+) = (\d+);", line)
      if field and message is not None:
        numbers[message][field.group(1)] = int(field.group(2))
      if line.startswith("}"):
        message = None
  return numbers


def _comment(text: str, indent: str) -> List[str]:
  lines = []
  for paragraph in text.splitlines():
    wrapped = textwrap.wrap(paragraph, 100 - len(indent) - 3) or [""]
    lines += [f"{indent}// {line}".rstrip() for line in wrapped]
  return lines


def _message_lines(name: str, fields: List[Field], known: Dict[str, int]) -> List[str]:
  if not fields:
    return [f"message {name} {{}}", ""]
  lines = [f"message {name} {{"]
  next_number = max([0, *known.values()]) + 1
  for field in fields:
    number = known.get(field.name)
    if number is None:
      number, next_number = next_number, next_number + 1
    label = f"{field.label} " if field.label else ""
    lines.append(f"  {label}{field.proto} {field.name} = {number};")
  return lines + ["}", ""]


def proto_text(service: Service) -> str:
  path = os.path.join(_HERE, "v1", f"{service.file}.proto")
  known = _numbers(path)
  doc = (inspect.getdoc(service.cls) or "").split("\n\n")[0]
  lines = [
    "// Generated by `python -m pylabrobot.brooks.precise_flex.server.generate`. DO NOT EDIT.",
    'syntax = "proto3";',
    "",
    *_comment(doc, ""),
    "//",
    f"// Each RPC calls `{service.cls.__name__}`'s method of its name, in snake case, each argument "
    "a field",
    "// named as the argument is (`types.proto` says how a value goes over).",
    f"package {_PKG};",
    "",
  ]
  served = rpcs(service)
  if service.cls is PreciseFlexDevice:
    lines.append('import "pylabrobot/brooks/precise_flex/server/v1/description.proto";')
  every = [f for rpc in served for f in rpc.fields + ([rpc.result] if rpc.result else [])]
  if any(f.kind.proto not in _SCALARS.values() or f.wrapped for f in every):
    lines.append('import "pylabrobot/brooks/precise_flex/server/v1/types.proto";')
  lines.append("")
  for rpc in served:
    lines += _message_lines(rpc.request, rpc.fields, known.get(rpc.request, {}))
    result = [] if rpc.result is None else [rpc.result]
    lines += _message_lines(rpc.response, result, known.get(rpc.response, {}))
  lines.append(f"service {service.name} {{")
  if service.cls is PreciseFlexDevice:
    lines.append("  // The device as the server holds it: what a client keeps of it.")
    lines.append("  rpc Describe(DescribeRequest) returns (Description);")
  for rpc in served:
    lines += _comment(rpc.doc, "  ")
    lines.append(f"  rpc {rpc.name}({rpc.request}) returns ({rpc.response});")
  lines.append("}")
  return "\n".join(lines) + "\n"


# -- the handlers --------------------------------------------------------------------------------


def _decode_argument(field: Field, out: List[str], indent: str) -> None:
  access = f"request.{field.name}"
  value = field.kind.from_.format(m=access)
  if field.wrapped is not None:
    out.append(f"{indent}if request.HasField({field.name!r}):")
    out.append(
      f"{indent}  kwargs[{field.name!r}] = {access}.value if {access}.HasField('value') else None"
    )
  elif field.kind.shape in ("repeated", "map"):
    out.append(f"{indent}kwargs[{field.name!r}] = {value}")
  elif field.required and not field.label and not field.kind.presence:
    out.append(f"{indent}kwargs[{field.name!r}] = {value}")
  else:
    out.append(f"{indent}if request.HasField({field.name!r}):")
    out.append(f"{indent}  kwargs[{field.name!r}] = {value}")


def _encode(field: Field, target: str, value: str, out: List[str], indent: str) -> None:
  """Set a field of `target` to a value that is not None."""
  converted = field.kind.to.format(v=value)
  access = f"{target}.{field.name}"
  if field.wrapped is not None:
    out.append(f"{indent}{access}.value = {converted}")
  elif field.kind.proto == "IntList":
    out.append(f"{indent}{access}.values.extend({value})")
    out.append(f"{indent}{access}.SetInParent()")
  elif field.kind.shape == "repeated":
    out.append(f"{indent}{access}.extend({converted})")
  elif field.kind.shape == "map":
    out.append(f"{indent}for key, item in {converted}.items():")
    out.append(f"{indent}  {access}[key].CopyFrom(item)")
  elif field.kind.shape == "message":
    out.append(f"{indent}{access}.CopyFrom({converted})")
  else:
    out.append(f"{indent}{access} = {converted}")


def handlers_text() -> str:
  out = [
    "# Generated by `python -m pylabrobot.brooks.precise_flex.server.generate`. DO NOT EDIT.",
    '"""Each PreciseFlex service\'s handlers: every RPC a call on the device a server serves."""',
    "",
    "from __future__ import annotations",
    "",
    "from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict",
    "",
    "from connectrpc.request import RequestContext",
    "",
    "from pylabrobot.brooks.precise_flex.server import wire",
    "from pylabrobot.brooks.precise_flex.server.v1 import description_pb2",
  ]
  for service in SERVICES:
    out.append(f"from {_PKG} import {service.file}_connect, {service.file}_pb2")
  out += [
    "",
    "if TYPE_CHECKING:",
    "  from pylabrobot.brooks.precise_flex.server.serve import Served",
    "",
    "# An ASGI 3 application.",
    "ASGIApp = Callable[[Dict[str, Any], Any, Any], Awaitable[None]]",
    "Ctx = RequestContext[Any, Any]",
    "",
  ]
  for service in SERVICES:
    pb = f"{service.file}_pb2"
    out += [
      "",
      f"class {service.prefix}Handlers:",
      f'  """{service.name}: each RPC a call on the served {service.cls.__name__}."""',
      "",
      "  def __init__(self, served: Served) -> None:",
      "    self._served = served",
      "",
    ]
    if service.cls is PreciseFlexDevice:
      out += [
        "  async def describe(",
        "    self, request: description_pb2.DescribeRequest, ctx: Ctx",
        "  ) -> description_pb2.Description:",
        "    return await self._served.describe(ctx)",
        "",
      ]
    for rpc in rpcs(service):
      out += [
        f"  async def {rpc.python}(",
        f"    self, request: {pb}.{rpc.request}, ctx: Ctx",
        f"  ) -> {pb}.{rpc.response}:",
        "    kwargs: Dict[str, Any] = {}",
        "",
        f"    async def run() -> {pb}.{rpc.response}:",
        f"      target = self._served.{service.target}",
      ]
      for field in rpc.fields:
        _decode_argument(field, out, "      ")
      if rpc.result is None:
        out.append(f"      await target.{rpc.python}(**kwargs)")
        out.append(f"      return {pb}.{rpc.response}()")
      else:
        out.append(f"      result = await target.{rpc.python}(**kwargs)")
        out.append(f"      response = {pb}.{rpc.response}()")
        if rpc.result.may_be_none:
          out.append("      if result is not None:")
          _encode(rpc.result, "response", "result", out, "        ")
        else:
          _encode(rpc.result, "response", "result", out, "      ")
        out.append("      return response")
      out += [
        "",
        f"    return await self._served.run(ctx, {service.file.replace('precise_flex', 'device')!r}, "
        f"{rpc.python!r}, run, kwargs)",
        "",
      ]
  out += [
    "",
    "def applications(served: Served) -> Dict[str, ASGIApp]:",
    '  """Each service\'s application, by the path its calls start with."""',
    "  return {",
  ]
  for service in SERVICES:
    out.append(
      f'    "/{_PKG}.{service.name}/": {service.file}_connect.{service.name}ASGIApplication('
      f"{service.prefix}Handlers(served)),"
    )
  out += ["  }", ""]
  return "\n".join(out)


# -- the client ----------------------------------------------------------------------------------


def _names_in(node: ast.AST) -> Set[str]:
  """The names an annotation or a default uses, those in a string annotation among them."""
  if isinstance(node, ast.Constant) and isinstance(node.value, str):
    return _names_in(ast.parse(node.value, mode="eval").body)
  if isinstance(node, ast.Name):
    return {node.id}
  if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
    if node.value.id == "Literal":
      return {"Literal"}
  names: Set[str] = set()
  for child in ast.iter_child_nodes(node):
    names |= _names_in(child)
  return names


class _ClassNames(ast.NodeTransformer):
  """Name what a class body defines, as an annotation in it uses it, through the class: its
  subclass, in another module, does not see it."""

  def __init__(self, cls: type, module_globals: Dict[str, Any]):
    self.cls = cls
    self.module_globals = module_globals

  def visit_Name(self, node: ast.Name) -> ast.AST:
    if node.id not in self.module_globals and node.id in vars(self.cls):
      return ast.Attribute(value=ast.Name(id=self.cls.__name__), attr=node.id, ctx=node.ctx)
    return node


def _signature_text(node: ast.AsyncFunctionDef) -> str:
  arguments = ast.unparse(node.args)
  returns = "" if node.returns is None else f" -> {ast.unparse(node.returns)}"
  return f"async def {node.name}({arguments}){returns}:"


def _annotations(node: ast.AsyncFunctionDef) -> List[ast.AST]:
  arguments = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
  found: List[ast.AST] = [a.annotation for a in arguments if a.annotation is not None]
  return found + ([node.returns] if node.returns is not None else [])


def remote_text() -> str:
  typing_names: Set[str] = set()
  imports: Dict[str, Set[str]] = {}
  body: List[str] = []
  for service in SERVICES:
    cls = service.cls
    pb = f"{service.file}_pb2"
    imports.setdefault(cls.__module__, set()).add(cls.__name__)
    body += [
      "",
      f"class _Remote{service.prefix}Calls({cls.__name__}):",
      f'  """{cls.__name__}, every method the server serves a call to it."""',
      "",
      "  _precise_flex_server: PreciseFlexServer",
      "",
    ]
    for rpc in rpcs(service):
      node = _def_node(rpc.fn)
      node = _ClassNames(cls, inspect.unwrap(rpc.fn).__globals__).visit(node)
      module = inspect.unwrap(rpc.fn).__module__
      for annotation in _annotations(node):
        for name in _names_in(annotation):
          if name in typing.__all__:
            typing_names.add(name)
          elif name not in ("None", "self") and not hasattr(builtins, name):
            if not any(name in names for names in imports.values()):
              imports.setdefault(module, set()).add(name)
      for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
        if any(isinstance(found, ast.Name) for found in ast.walk(default)):
          raise TypeError(f"{cls.__name__}.{rpc.python} has a default that names something")
      body.append(f"  {_signature_text(node)}")
      body.append(f"    request = {pb}.{rpc.request}()")
      for field in rpc.fields:
        if field.wrapped is not None:
          body.append(f"    if {field.name} is None:")
          body.append(f"      request.{field.name}.SetInParent()")
          body.append("    else:")
          _encode(field, "request", field.name, body, "      ")
        elif field.may_be_none:
          body.append(f"    if {field.name} is not None:")
          _encode(field, "request", field.name, body, "      ")
        else:
          _encode(field, "request", field.name, body, "    ")
      call = f"self._precise_flex_server.clients.{service.file}.{rpc.python}(request)"
      if rpc.result is None:
        body.append(f"    await self._precise_flex_server.call({call})")
      else:
        body.append(f"    response = await self._precise_flex_server.call({call})")
        value = rpc.result.kind.from_.format(m=f"response.{rpc.result.name}")
        if rpc.result.may_be_none:
          body.append(f"    return {value} if response.HasField({rpc.result.name!r}) else None")
        else:
          body.append(f"    return {value}")
      body += ["", f"  {rpc.python}.__doc__ = {cls.__name__}.{rpc.python}.__doc__", ""]
  out = [
    "# Generated by `python -m pylabrobot.brooks.precise_flex.server.generate`. DO NOT EDIT.",
    '"""The PreciseFlex\'s classes, every public coroutine a call to a PreciseFlex server."""',
    "",
    "from __future__ import annotations",
    "",
    f"from typing import {', '.join(sorted(typing_names | {'TYPE_CHECKING', 'Any'}))}",
    "",
    "from pylabrobot.brooks.precise_flex.server import wire",
  ]
  for service in SERVICES:
    out.append(f"from {_PKG} import {service.file}_connect, {service.file}_pb2")
  classes = {service.cls.__module__: service.cls.__name__ for service in SERVICES}
  for module in sorted(classes):
    out.append(f"from {module} import {classes[module]}")
  out += [
    "",
    "if TYPE_CHECKING:",
    "  from pylabrobot.brooks.precise_flex.server.client import PreciseFlexServer",
  ]
  for module in sorted(imports):
    names = sorted(imports[module] - {classes.get(module)})
    if names:
      out.append(f"  from {module} import {', '.join(names)}")
  out += [
    "",
    "",
    "class PreciseFlexClients:",
    '  """A Connect client for every PreciseFlex service the generated classes call."""',
    "",
    "  def __init__(self, address: str, http: Any, interceptors: Any) -> None:",
  ]
  for service in SERVICES:
    out.append(
      f"    self.{service.file} = {service.file}_connect.{service.name}Client("
      "address, http_client=http, interceptors=interceptors)"
    )
  out += ["", "  async def close(self) -> None:"]
  for service in SERVICES:
    out.append(f"    await self.{service.file}.close()")
  out += body
  return "\n".join(out).rstrip("\n") + "\n"


# -- writing them --------------------------------------------------------------------------------


def outputs() -> Dict[str, str]:
  """Every file this writes, by its path, and what it holds."""
  written = {
    os.path.join(_HERE, "v1", f"{service.file}.proto"): proto_text(service) for service in SERVICES
  }
  written[os.path.join(_HERE, "generated_handlers.py")] = handlers_text()
  written[os.path.join(_HERE, "generated_remote.py")] = remote_text()
  return written


def main(argv: Optional[Sequence[str]] = None) -> None:
  for path, text in outputs().items():
    with open(path, "w", encoding="utf-8") as f:
      f.write(text)
    print(f"wrote {os.path.relpath(path)}")


if __name__ == "__main__":
  main()


__all__ = ["RPC", "SERVICES", "Service", "outputs", "rpcs", "served_methods"]
