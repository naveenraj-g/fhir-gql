from .available_time import PractitionerRoleAvailableTimeInput
from .code import PractitionerRoleCodeInput
from .core import (
    ListPractitionerRolesSchema,
    PractitionerRoleCreateSchema,
    PractitionerRolePatchSchema,
)
from .endpoint import PractitionerRoleEndpointInput
from .healthcare_service import PractitionerRoleHealthcareServiceInput
from .identifier import PractitionerRoleIdentifierInput
from .location import PractitionerRoleLocationInput
from .not_available import PractitionerRoleNotAvailableInput
from .specialty import PractitionerRoleSpecialtyInput
from .telecom import PractitionerRoleTelecomInput

__all__ = [
    "PractitionerRoleCreateSchema",
    "PractitionerRolePatchSchema",
    "ListPractitionerRolesSchema",
    "PractitionerRoleIdentifierInput",
    "PractitionerRoleCodeInput",
    "PractitionerRoleSpecialtyInput",
    "PractitionerRoleLocationInput",
    "PractitionerRoleHealthcareServiceInput",
    "PractitionerRoleTelecomInput",
    "PractitionerRoleAvailableTimeInput",
    "PractitionerRoleNotAvailableInput",
    "PractitionerRoleEndpointInput",
]
