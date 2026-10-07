from fastapi import APIRouter

from app.api.routes import auth, bookings, equipment, service

api_router = APIRouter(prefix="/api")
api_router.include_router(service.router)
api_router.include_router(auth.router)
api_router.include_router(equipment.router)
api_router.include_router(bookings.router)
