from app.schemas.schedule.fhir_schemas import FhirBundleResponse, FhirScheduleResponse
from app.schemas.schedule.input import (
    ListSchedulesSchema,
    ScheduleActorInput,
    ScheduleCreateSchema,
    ScheduleIdentifierInput,
    SchedulePatchSchema,
)
from app.schemas.schedule.response import (
    PaginatedScheduleResponse,
    ScheduleActorResponse,
    ScheduleIdentifierResponse,
    ScheduleResponse,
    ScheduleServiceCategoryResponse,
    ScheduleServiceTypeResponse,
    ScheduleSpecialtyResponse,
)

__all__ = [
    # Input — top-level
    "ScheduleCreateSchema",
    "SchedulePatchSchema",
    "ListSchedulesSchema",
    # Input — sub-resources
    "ScheduleIdentifierInput",
    "ScheduleActorInput",
    # Response — top-level
    "ScheduleResponse",
    "PaginatedScheduleResponse",
    # Response — sub-resources
    "ScheduleIdentifierResponse",
    "ScheduleServiceCategoryResponse",
    "ScheduleServiceTypeResponse",
    "ScheduleSpecialtyResponse",
    "ScheduleActorResponse",
    # FHIR
    "FhirScheduleResponse",
    "FhirBundleResponse",
]
