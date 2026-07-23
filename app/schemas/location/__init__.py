from app.schemas.enums import DayOfWeek
from app.schemas.location.enums import LocationMode, LocationStatus
from app.schemas.location.fhir_schemas import FhirBundleResponse, FhirLocationResponse
from app.schemas.location.input import (
    ListLocationsSchema,
    LocationCreateSchema,
    LocationEndpointInput,
    LocationHoursOfOperationInput,
    LocationIdentifierInput,
    LocationPatchSchema,
    LocationTelecomInput,
    LocationTypeInput,
)
from app.schemas.location.response import (
    LocationEndpointResponse,
    LocationHoursOfOperationResponse,
    LocationIdentifierResponse,
    LocationResponse,
    LocationTelecomResponse,
    LocationTypeResponse,
    PaginatedLocationResponse,
)

__all__ = [
    # Enums
    "LocationStatus",
    "LocationMode",
    "DayOfWeek",
    # Input — top-level
    "LocationCreateSchema",
    "LocationPatchSchema",
    "ListLocationsSchema",
    # Input — sub-resources
    "LocationIdentifierInput",
    "LocationTypeInput",
    "LocationTelecomInput",
    "LocationHoursOfOperationInput",
    "LocationEndpointInput",
    # Response — top-level
    "LocationResponse",
    "PaginatedLocationResponse",
    # Response — sub-resources
    "LocationIdentifierResponse",
    "LocationTypeResponse",
    "LocationTelecomResponse",
    "LocationHoursOfOperationResponse",
    "LocationEndpointResponse",
    # FHIR
    "FhirLocationResponse",
    "FhirBundleResponse",
]
