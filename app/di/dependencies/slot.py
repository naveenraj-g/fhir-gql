"""
FastAPI dependency factory for SlotService.

Bridges the dependency-injector container with FastAPI's Depends() system.
Route handlers use `Depends(get_slot_service)` to receive a fully-wired
SlotService instance without knowing how it is constructed. Identical
shape to app/di/dependencies/schedule.py.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from app.di.container import Container
from app.services.slot_service import SlotService


@inject
def get_slot_service(
    service: SlotService = Depends(Provide[Container.slot.slot_service]),
) -> SlotService:
    """
    Resolve SlotService from the DI container for use in route handlers.

    Returns:
        A fully-wired SlotService ready for use in a route handler.
    """
    return service
