from app.schemas.slot.enums import SlotStatus
from app.schemas.slot.fhir_schemas import FhirBundleResponse, FhirSlotResponse
from app.schemas.slot.input import (
    ListSlotsSchema,
    SlotCreateSchema,
    SlotGenerateSchema,
    SlotIdentifierInput,
    SlotPatchSchema,
    SlotServiceCategoryInput,
    SlotServiceTypeInput,
    SlotSpecialtyInput,
)
from app.schemas.slot.response import (
    PaginatedSlotResponse,
    SlotGenerateResponse,
    SlotIdentifierResponse,
    SlotResponse,
    SlotServiceCategoryResponse,
    SlotServiceTypeResponse,
    SlotSpecialtyResponse,
)

__all__ = [
    # Enums
    "SlotStatus",
    # Input — top-level
    "SlotCreateSchema",
    "SlotGenerateSchema",
    "SlotPatchSchema",
    "ListSlotsSchema",
    # Input — sub-resources
    "SlotIdentifierInput",
    "SlotServiceCategoryInput",
    "SlotServiceTypeInput",
    "SlotSpecialtyInput",
    # Response — top-level
    "SlotResponse",
    "PaginatedSlotResponse",
    "SlotGenerateResponse",
    # Response — sub-resources
    "SlotIdentifierResponse",
    "SlotServiceCategoryResponse",
    "SlotServiceTypeResponse",
    "SlotSpecialtyResponse",
    # FHIR
    "FhirSlotResponse",
    "FhirBundleResponse",
]
