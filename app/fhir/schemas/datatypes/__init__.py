"""
Re-exports every FHIR R4 non-primitive datatype as `app.fhir.schemas.datatypes.*`
so callers don't need to know which file a given type lives in.

Each datatype gets its own module (one class per file) so a resource that
needs a field description tweaked, or a stricter validator, can subclass
the specific type it needs without touching the others — see
app.fhir.schemas.organization for the pattern.
"""

from app.fhir.schemas.datatypes.address import FhirAddress
from app.fhir.schemas.datatypes.attachment import FhirAttachment
from app.fhir.schemas.datatypes.codeable_concept import FhirCodeableConcept
from app.fhir.schemas.datatypes.coding import FhirCoding
from app.fhir.schemas.datatypes.contact_point import FhirContactPoint
from app.fhir.schemas.datatypes.human_name import FhirHumanName
from app.fhir.schemas.datatypes.identifier import FhirIdentifier
from app.fhir.schemas.datatypes.meta import FhirMeta
from app.fhir.schemas.datatypes.period import FhirPeriod
from app.fhir.schemas.datatypes.reference import FhirReference

__all__ = [
    "FhirAddress",
    "FhirAttachment",
    "FhirCodeableConcept",
    "FhirCoding",
    "FhirContactPoint",
    "FhirHumanName",
    "FhirIdentifier",
    "FhirMeta",
    "FhirPeriod",
    "FhirReference",
]
