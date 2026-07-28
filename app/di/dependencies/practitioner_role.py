"""
FastAPI dependency factory for PractitionerRoleService.

Bridges the dependency-injector container with FastAPI's Depends() system.
Route handlers use `Depends(get_practitioner_role_service)` to receive a
fully-wired PractitionerRoleService instance without knowing how it is
constructed. Identical shape to app/di/dependencies/healthcare_service.py.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from app.di.container import Container
from app.services.practitioner_role_service import PractitionerRoleService


@inject
def get_practitioner_role_service(
    service: PractitionerRoleService = Depends(
        Provide[Container.practitioner_role.practitioner_role_service]
    ),
) -> PractitionerRoleService:
    """
    Resolve PractitionerRoleService from the DI container for use in route handlers.

    Returns:
        A fully-wired PractitionerRoleService ready for use in a route handler.
    """
    return service
