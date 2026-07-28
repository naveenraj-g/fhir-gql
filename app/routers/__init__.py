from fastapi import APIRouter

from app.routers.healthcare_service import router as healthcare_service_router
from app.routers.location import router as location_router
from app.routers.organization import router as organization_router
from app.routers.patient import router as patients_router
from app.routers.practitioner import router as practitioner_router
from app.routers.practitioner_role import router as practitioner_role_router
from app.routers.schedule import router as schedule_router
from app.routers.slot import router as slot_router
from app.routers.terminology import router as terminology_router

api_router = APIRouter()

api_router.include_router(patients_router)
api_router.include_router(terminology_router)
api_router.include_router(organization_router)
api_router.include_router(location_router)
api_router.include_router(healthcare_service_router)
api_router.include_router(practitioner_router)
api_router.include_router(practitioner_role_router)
api_router.include_router(schedule_router)
api_router.include_router(slot_router)
