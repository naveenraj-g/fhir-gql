from .alias import LocationAliasResponse
from .core import LocationResponse, PaginatedLocationResponse
from .endpoint import LocationEndpointResponse
from .hours_of_operation import LocationHoursOfOperationResponse
from .identifier import LocationIdentifierResponse
from .telecom import LocationTelecomResponse
from .type import LocationTypeResponse

__all__ = [
    "LocationResponse",
    "PaginatedLocationResponse",
    "LocationIdentifierResponse",
    "LocationTypeResponse",
    "LocationAliasResponse",
    "LocationTelecomResponse",
    "LocationHoursOfOperationResponse",
    "LocationEndpointResponse",
]
