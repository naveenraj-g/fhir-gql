"""
FastAPI dependency factory for PractitionerService.

Bridges the dependency-injector container with FastAPI's Depends() system.
Route handlers use `Depends(get_practitioner_service)` to receive a
fully-wired PractitionerService instance without knowing how it is
constructed. Identical shape to app/di/dependencies/patient.py.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from app.di.container import Container
from app.services.practitioner_service import PractitionerService


@inject
def get_practitioner_service(
    service: PractitionerService = Depends(Provide[Container.practitioner.practitioner_service]),
) -> PractitionerService:
    """
    Resolve PractitionerService from the DI container for use in route handlers.

    Returns:
        A fully-wired PractitionerService ready for use in a route handler.
    """
    return service
