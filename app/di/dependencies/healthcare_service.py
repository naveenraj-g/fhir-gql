"""
FastAPI dependency factory for HealthcareServiceService.

Bridges the dependency-injector container with FastAPI's Depends() system.
Route handlers use `Depends(get_healthcare_service_service)` to receive a
fully-wired HealthcareServiceService instance without knowing how it is
constructed. Identical shape to app/di/dependencies/location.py.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from app.di.container import Container
from app.services.healthcare_service_service import HealthcareServiceService


@inject
def get_healthcare_service_service(
    service: HealthcareServiceService = Depends(
        Provide[Container.healthcare_service.healthcare_service_service]
    ),
) -> HealthcareServiceService:
    """
    Resolve HealthcareServiceService from the DI container for use in route handlers.

    Returns:
        A fully-wired HealthcareServiceService ready for use in a route handler.
    """
    return service
