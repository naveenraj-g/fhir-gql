"""
FastAPI dependency factory for LocationService.

Bridges the dependency-injector container with FastAPI's Depends() system.
Route handlers use `Depends(get_location_service)` to receive a fully-wired
LocationService instance without knowing how it is constructed. Identical
shape to app/di/dependencies/organization.py.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from app.di.container import Container
from app.services.location_service import LocationService


@inject
def get_location_service(
    service: LocationService = Depends(Provide[Container.location.location_service]),
) -> LocationService:
    """
    Resolve LocationService from the DI container for use in route handlers.

    Returns:
        A fully-wired LocationService ready for use in a route handler.
    """
    return service
