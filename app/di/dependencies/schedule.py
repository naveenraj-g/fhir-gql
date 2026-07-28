"""
FastAPI dependency factory for ScheduleService.

Bridges the dependency-injector container with FastAPI's Depends() system.
Route handlers use `Depends(get_schedule_service)` to receive a fully-wired
ScheduleService instance without knowing how it is constructed. Identical
shape to app/di/dependencies/healthcare_service.py.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from app.di.container import Container
from app.services.schedule_service import ScheduleService


@inject
def get_schedule_service(
    service: ScheduleService = Depends(Provide[Container.schedule.schedule_service]),
) -> ScheduleService:
    """
    Resolve ScheduleService from the DI container for use in route handlers.

    Returns:
        A fully-wired ScheduleService ready for use in a route handler.
    """
    return service
