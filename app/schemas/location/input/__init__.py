from .alias import LocationAliasInput
from .core import ListLocationsSchema, LocationCreateSchema, LocationPatchSchema
from .endpoint import LocationEndpointInput
from .hours_of_operation import LocationHoursOfOperationInput
from .identifier import LocationIdentifierInput
from .telecom import LocationTelecomInput
from .type import LocationTypeInput

__all__ = [
    "LocationCreateSchema",
    "LocationPatchSchema",
    "ListLocationsSchema",
    "LocationIdentifierInput",
    "LocationTypeInput",
    "LocationAliasInput",
    "LocationTelecomInput",
    "LocationHoursOfOperationInput",
    "LocationEndpointInput",
]
