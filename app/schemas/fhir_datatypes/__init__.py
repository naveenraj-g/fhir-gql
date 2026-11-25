"""FHIR R4 datatypes as Pydantic models, generated from HL7's own schema.

Public (request/response) field names are FHIR camelCase; Python modules are snake_case.
Regenerate with `uv run python scripts/generate_fhir_datatypes.py`. Categories follow
https://hl7.org/fhir/R4/datatypes.html (primitive / general / metadata / special).
"""

from pydantic import BaseModel

from app.schemas.fhir_datatypes.base import BackboneElement, Element
from app.schemas.fhir_datatypes.general.address import (
    Address,
)
from app.schemas.fhir_datatypes.general.age import (
    Age,
)
from app.schemas.fhir_datatypes.general.annotation import (
    Annotation,
)
from app.schemas.fhir_datatypes.general.attachment import (
    Attachment,
)
from app.schemas.fhir_datatypes.general.codeable_concept import (
    CodeableConcept,
)
from app.schemas.fhir_datatypes.general.coding import (
    Coding,
)
from app.schemas.fhir_datatypes.general.contact_point import (
    ContactPoint,
)
from app.schemas.fhir_datatypes.general.count import (
    Count,
)
from app.schemas.fhir_datatypes.general.distance import (
    Distance,
)
from app.schemas.fhir_datatypes.general.duration import (
    Duration,
)
from app.schemas.fhir_datatypes.general.human_name import (
    HumanName,
)
from app.schemas.fhir_datatypes.general.identifier import (
    Identifier,
)
from app.schemas.fhir_datatypes.general.money import (
    Money,
)
from app.schemas.fhir_datatypes.general.money_quantity import (
    MoneyQuantity,
)
from app.schemas.fhir_datatypes.general.period import (
    Period,
)
from app.schemas.fhir_datatypes.general.quantity import (
    Quantity,
)
from app.schemas.fhir_datatypes.general.range import (
    Range,
)
from app.schemas.fhir_datatypes.general.ratio import (
    Ratio,
)
from app.schemas.fhir_datatypes.general.reference import (
    Reference,
)
from app.schemas.fhir_datatypes.general.sampled_data import (
    SampledData,
)
from app.schemas.fhir_datatypes.general.signature import (
    Signature,
)
from app.schemas.fhir_datatypes.general.simple_quantity import (
    SimpleQuantity,
)
from app.schemas.fhir_datatypes.general.timing import (
    Timing,
    TimingRepeat,
)
from app.schemas.fhir_datatypes.metadata.contact_detail import (
    ContactDetail,
)
from app.schemas.fhir_datatypes.metadata.contributor import (
    Contributor,
)
from app.schemas.fhir_datatypes.metadata.data_requirement import (
    DataRequirement,
    DataRequirementCodeFilter,
    DataRequirementDateFilter,
    DataRequirementSort,
)
from app.schemas.fhir_datatypes.metadata.expression import (
    Expression,
)
from app.schemas.fhir_datatypes.metadata.parameter_definition import (
    ParameterDefinition,
)
from app.schemas.fhir_datatypes.metadata.related_artifact import (
    RelatedArtifact,
)
from app.schemas.fhir_datatypes.metadata.trigger_definition import (
    TriggerDefinition,
)
from app.schemas.fhir_datatypes.metadata.usage_context import (
    UsageContext,
)
from app.schemas.fhir_datatypes.primitive.primitives import (
    Base64Binary,
    Boolean,
    Canonical,
    Code,
    Date,
    DateTime,
    Decimal,
    Id,
    Instant,
    Integer,
    Markdown,
    Oid,
    PositiveInt,
    String,
    Time,
    UnsignedInt,
    Uri,
    Url,
    Uuid,
    Xhtml,
)
from app.schemas.fhir_datatypes.special.dosage import (
    Dosage,
    DosageDoseAndRate,
)
from app.schemas.fhir_datatypes.special.element_definition import (
    ElementDefinition,
    ElementDefinitionBase,
    ElementDefinitionBinding,
    ElementDefinitionConstraint,
    ElementDefinitionDiscriminator,
    ElementDefinitionExample,
    ElementDefinitionMapping,
    ElementDefinitionSlicing,
    ElementDefinitionType,
)
from app.schemas.fhir_datatypes.special.extension import (
    Extension,
)
from app.schemas.fhir_datatypes.special.marketing_status import (
    MarketingStatus,
)
from app.schemas.fhir_datatypes.special.meta import (
    Meta,
)
from app.schemas.fhir_datatypes.special.narrative import (
    Narrative,
)
from app.schemas.fhir_datatypes.special.population import (
    Population,
)
from app.schemas.fhir_datatypes.special.prod_characteristic import (
    ProdCharacteristic,
)
from app.schemas.fhir_datatypes.special.product_shelf_life import (
    ProductShelfLife,
)
from app.schemas.fhir_datatypes.special.substance_amount import (
    SubstanceAmount,
    SubstanceAmountReferenceRange,
)

__all__ = [
    "Address",
    "Age",
    "Annotation",
    "Attachment",
    "BackboneElement",
    "Base64Binary",
    "Boolean",
    "Canonical",
    "Code",
    "CodeableConcept",
    "Coding",
    "ContactDetail",
    "ContactPoint",
    "Contributor",
    "Count",
    "DataRequirement",
    "DataRequirementCodeFilter",
    "DataRequirementDateFilter",
    "DataRequirementSort",
    "Date",
    "DateTime",
    "Decimal",
    "Distance",
    "Dosage",
    "DosageDoseAndRate",
    "Duration",
    "Element",
    "ElementDefinition",
    "ElementDefinitionBase",
    "ElementDefinitionBinding",
    "ElementDefinitionConstraint",
    "ElementDefinitionDiscriminator",
    "ElementDefinitionExample",
    "ElementDefinitionMapping",
    "ElementDefinitionSlicing",
    "ElementDefinitionType",
    "Expression",
    "Extension",
    "HumanName",
    "Id",
    "Identifier",
    "Instant",
    "Integer",
    "Markdown",
    "MarketingStatus",
    "Meta",
    "Money",
    "MoneyQuantity",
    "Narrative",
    "Oid",
    "ParameterDefinition",
    "Period",
    "Population",
    "PositiveInt",
    "ProdCharacteristic",
    "ProductShelfLife",
    "Quantity",
    "Range",
    "Ratio",
    "Reference",
    "RelatedArtifact",
    "SampledData",
    "Signature",
    "SimpleQuantity",
    "String",
    "SubstanceAmount",
    "SubstanceAmountReferenceRange",
    "Time",
    "Timing",
    "TimingRepeat",
    "TriggerDefinition",
    "UnsignedInt",
    "Uri",
    "Url",
    "UsageContext",
    "Uuid",
    "Xhtml",
]

# Models reference one another (Identifier -> Reference -> Identifier, Extension -> everything),
# so every annotation is a string until all modules are loaded; resolve them here.
_NAMESPACE = {name: globals()[name] for name in __all__}
for _name in __all__:
    _obj = globals()[_name]
    if isinstance(_obj, type) and issubclass(_obj, BaseModel):
        _obj.model_rebuild(_types_namespace=_NAMESPACE)
