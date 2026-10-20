"""
FastAPI dependency factory for OrganizationsService.

Bridges the dependency-injector container with FastAPI's Depends() system.
Route handlers use `Depends(get_organization_service)` to receive a
fully-wired OrganizationsService instance without knowing how it is
constructed. Identical shape to app/di/dependencies/patient.py.

The OrganizationsService type hint below comes from
app.connectors.resource_registry.CONNECTOR_RESOURCES (keyed off
`settings.connectors.active`), not a fixed connector-specific import — see
app/di/modules/organization.py's module docstring for the full rationale.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from app.connectors.resource_registry import CONNECTOR_RESOURCES
from app.core.config import settings
from app.di.container import Container

OrganizationsService = CONNECTOR_RESOURCES[settings.connectors.active]["organization"][
    "service"
]


@inject
def get_organization_service(
    service: OrganizationsService = Depends(
        Provide[Container.organization.organization_service]
    ),
) -> OrganizationsService:
    """
    Resolve OrganizationsService from the DI container for use in route handlers.

    The @inject decorator tells dependency-injector to replace the Provide[]
    sentinel with the actual OrganizationsService instance from the container
    at call time. FastAPI's Depends() wraps this function so each request
    gets a fresh Factory-created instance.

    Returns:
        A fully-wired OrganizationsService ready for use in a route handler.
    """
    return service
