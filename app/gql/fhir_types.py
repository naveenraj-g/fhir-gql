"""
Builds GraphQL object and input types from the generated FHIR R4 Pydantic models.

Why this module exists
----------------------
fhir-server generates one fully-typed Pydantic model per FHIR R4 datatype and per resource
(`app.schemas.fhir_datatypes`, `app.schemas.fhir_resources`; copied here verbatim). Declaring a
hand-written Strawberry class for every one of those models (hundreds per resource, thousands in
all) is neither practical nor safe from drift, so the GraphQL types are *derived* from the same
models instead, at import time:

* `output_type(Model)` -> a Strawberry object type (`Fhir<Model>Type`), every field nullable;
* `input_type(Model)`  -> a Strawberry input type (`Fhir<Model>Input`), where a field the model
  requires (R4's 1..1 / 1..*) is non-null.

How the types stay in step with the models
------------------------------------------
* The field names are the FHIR names (`valueQuantity`, `class`) - the same names the REST API,
  the stored `content` and HL7's documentation use - and each field carries HL7's own element
  description from the model.
* **Reads pass the backend's FHIR JSON straight through.** Every generated output field reads its
  value from the raw FHIR dict by the FHIR element name (`_reader`), so a resolver just returns
  the dict a connector produced. Nothing is validated on the way out on purpose: the gateway
  fronts other EHRs (Epic, OpenEMR, Oracle Health, Medplum) whose records need not satisfy every
  R4 minimum, and a record missing one required element must not fail the whole query. (A
  Pydantic model instance works as a source too.)
* On the way in, `input_to_dict()` turns a Strawberry input object back into the FHIR JSON
  document (camelCase keys, unset fields left out), which is validated with the same Pydantic
  model before it is sent to a connector.

What a Pydantic annotation turns into
-------------------------------------
`str`/`int`/`float`/`bool` stay themselves; a `Literal[...]` code list becomes a `String` (the
accepted codes are in the field description); a bare `dict` (`Extension.value[x]` complex values,
`contained`) becomes the `JSON` scalar; a nested model becomes its own GraphQL type; a list stays
a list. Recursive elements (Questionnaire.item.item) work because every class is created before
any of them is decorated.
"""

import dataclasses
import types
import typing
from typing import Any

import strawberry
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from strawberry.scalars import JSON
from strawberry.types.base import StrawberryObjectDefinition

from app.schemas.fhir_resources.base import DomainResource

# GraphQL type names get this prefix so they can never collide with a scalar or with the
# gateway's own types (`FhirCoding`, `FhirObservation`, ...).
_PREFIX = "Fhir"

# Server-managed elements of a resource: `id` is assigned by the server and `meta` is stamped on
# at read time, so neither is offered on a *write* (input) type of a resource.
_SERVER_MANAGED = {"id", "meta"}


class _Builder:
    """
    One family of generated GraphQL types (all output types, or all input types).

    The two families are kept in separate builders because GraphQL requires different classes for
    an object and an input even when both describe the same model.
    """

    def __init__(self, *, is_input: bool) -> None:
        # Whether this builder produces `@strawberry.input` (True) or `@strawberry.type` (False).
        self.is_input = is_input
        # Suffix that tells an input type from an output type with the same model
        # (`FhirCodingType` / `FhirCodingInput`, matching the gateway's naming).
        self.suffix = "Input" if is_input else "Type"
        # model class -> the (still undecorated) generated class, so a cycle finds its target.
        self.classes: dict[type[BaseModel], type] = {}
        # generated class -> {python attribute name: FHIR element name}, used by input_to_dict.
        self.fhir_names: dict[type, dict[str, str]] = {}

    # -- public entry point -------------------------------------------------------------------

    def build(self, model: type[BaseModel], *, name: str | None = None) -> type:
        """Return the GraphQL type for `model`, creating it and everything it refers to once."""
        # Pass 1: create an empty class for the model and every model reachable from it, so that
        # field annotations can point at real classes even when the models refer to each other.
        new = self._discover(model, name)
        # Pass 2: give each new class its fields and decorate it with Strawberry.
        for cls_model, cls in new:
            self._decorate(cls_model, cls)
        return self.classes[model]

    # -- pass 1 -------------------------------------------------------------------------------

    def _discover(
        self, model: type[BaseModel], name: str | None
    ) -> list[tuple[type[BaseModel], type]]:
        """Create (but do not yet decorate) a class for `model` and each model it reaches."""
        created: list[tuple[type[BaseModel], type]] = []
        todo = [(model, name)]
        while todo:
            current, explicit_name = todo.pop()
            if current in self.classes and explicit_name is None:
                continue
            # A model is registered once; the first request decides its GraphQL name.
            if current not in self.classes:
                type_name = explicit_name or f"{_PREFIX}{current.__name__}{self.suffix}"
                cls = type(type_name, (), {"__module__": __name__})
                self.classes[current] = cls
                created.append((current, cls))
            # Queue every model that one of this model's fields refers to.
            for info in current.model_fields.values():
                todo.extend((m, None) for m in _models_in(info.annotation))
        return created

    # -- pass 2 -------------------------------------------------------------------------------

    def _decorate(self, model: type[BaseModel], cls: type) -> None:
        """Fill `cls` with one Strawberry field per model field, then register it."""
        annotations: dict[str, Any] = {}
        names: dict[str, str] = {}
        is_resource = issubclass(model, DomainResource)
        for attr, info in model.model_fields.items():
            # A resource's server-managed elements are not writable.
            if self.is_input and is_resource and attr in _SERVER_MANAGED:
                continue
            # FHIR keyword elements (`class`, `from`) are `class_` / `from_` in Python and carry
            # the real name as the Pydantic alias; GraphQL uses the FHIR name.
            fhir_name = info.alias or attr
            names[attr] = fhir_name
            gql_type = self._gql_type(info.annotation)
            # Output fields are always nullable (the server may legitimately not hold an element,
            # and another EHR's data may omit one R4 requires); input fields follow the model.
            required = self.is_input and info.is_required()
            annotations[attr] = gql_type if required else gql_type | None
            setattr(
                cls,
                attr,
                _field(
                    info,
                    attr,
                    fhir_name,
                    gql_type | None,
                    is_input=self.is_input,
                    required=required,
                ),
            )
        cls.__annotations__ = annotations
        self.fhir_names[cls] = names
        decorator = strawberry.input if self.is_input else strawberry.type
        decorator(cls, description=(model.__doc__ or "").strip() or None)

    def _gql_type(self, annotation: Any) -> Any:
        """Translate one Pydantic field annotation into the annotation Strawberry understands."""
        origin = typing.get_origin(annotation)
        args = typing.get_args(annotation)
        # `X | None` / Optional[X]: nullability is decided by the caller, so unwrap it.
        if origin in (typing.Union, types.UnionType):
            real = [a for a in args if a is not type(None)]
            return self._gql_type(real[0]) if len(real) == 1 else JSON
        # list[X] stays a list of the translated element type.
        if origin is list:
            return list[self._gql_type(args[0])]
        # Literal[...] code lists are exposed as plain strings.
        if origin is typing.Literal:
            return str
        # Annotated[X, ...] (the constrained primitives): the constraints are not GraphQL's job.
        if origin is typing.Annotated:
            return self._gql_type(args[0])
        # A bare dict is an open FHIR structure (an extension value, a contained resource).
        if annotation is dict or origin is dict:
            return JSON
        # A nested generated model becomes its own GraphQL type.
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return self.classes[annotation]
        # str / int / float / bool map to the GraphQL scalar of the same name.
        return annotation


def _reader(attr: str, fhir_name: str, annotation: Any) -> Any:
    """
    The resolver of one output field: read the element out of the source object.

    The source is normally the raw FHIR dict a connector returned (looked up by the FHIR name); a
    Pydantic model instance (looked up by attribute) is accepted as well. A missing element is
    `None`, which GraphQL serialises as null.
    """

    def read(root: Any) -> Any:
        if isinstance(root, dict):
            return root.get(fhir_name)
        return getattr(root, attr, None)

    # Strawberry takes the field's GraphQL type from the resolver's return annotation.
    read.__annotations__["return"] = annotation
    return read


def _field(
    info: FieldInfo,
    attr: str,
    fhir_name: str,
    annotation: Any,
    *,
    is_input: bool,
    required: bool,
) -> Any:
    """A Strawberry field carrying the FHIR element name and HL7's description."""
    kwargs: dict[str, Any] = {"name": fhir_name, "description": info.description}
    if not is_input:
        # An output field reads its value out of the source FHIR document.
        return strawberry.field(resolver=_reader(attr, fhir_name, annotation), **kwargs)
    # A required input field has no default; everything else defaults to "not supplied".
    if not required:
        kwargs["default"] = None
    return strawberry.field(**kwargs)


def _models_in(annotation: Any) -> list[type[BaseModel]]:
    """Every Pydantic model an annotation mentions (through unions, lists and Annotated)."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return [annotation]
    found: list[type[BaseModel]] = []
    for arg in typing.get_args(annotation):
        found.extend(_models_in(arg))
    return found


# One builder per family, shared by every resource so a datatype used by many resources (Coding,
# Reference, ...) becomes a single GraphQL type.
_OUTPUT = _Builder(is_input=False)
_INPUT = _Builder(is_input=True)


def output_type(model: type[BaseModel]) -> type:
    """The GraphQL object type for `model` (a resource or any datatype)."""
    return _OUTPUT.build(model)


def input_type(model: type[BaseModel], *, name: str | None = None) -> type:
    """
    The GraphQL input type for `model`.

    `name` lets the merge-patch variant of a resource (`Observation`'s `ObservationPatch`) get a
    distinct GraphQL name such as `FhirObservationPatchInput` while sharing every nested type.
    """
    return _INPUT.build(model, name=name)


def input_to_dict(value: Any) -> Any:
    """
    Turn a Strawberry input object back into the FHIR JSON it stands for.

    Keys are the FHIR element names; fields the caller did not supply (`UNSET`) or sent as null are
    left out, so the result can be validated and sent as a FHIR document or a merge-patch.
    """
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        names = _INPUT.fhir_names.get(type(value), {})
        out: dict[str, Any] = {}
        for field in dataclasses.fields(value):
            item = getattr(value, field.name)
            if item is strawberry.UNSET or item is None:
                continue
            out[names.get(field.name, field.name)] = input_to_dict(item)
        return out
    if isinstance(value, list):
        return [input_to_dict(v) for v in value]
    return value


def is_object_type(cls: type) -> bool:
    """True when `cls` is a Strawberry object/input type (used by the self-check tests)."""
    return isinstance(
        getattr(cls, "__strawberry_definition__", None), StrawberryObjectDefinition
    )
