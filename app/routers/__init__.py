from fastapi import APIRouter

from app.routers.patient import router as patients_router
from app.routers.terminology import router as terminology_router

api_router = APIRouter()

api_router.include_router(patients_router)
api_router.include_router(terminology_router)
