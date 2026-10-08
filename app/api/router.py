from fastapi import APIRouter

from app.api.routes import admin, auth, availability, bookings, equipment, favorites, geo, reviews, service, telegram

api_router = APIRouter(prefix="/api")
api_router.include_router(service.router)
api_router.include_router(auth.router)
api_router.include_router(equipment.router)
api_router.include_router(bookings.router)
api_router.include_router(telegram.router)
api_router.include_router(geo.router)
api_router.include_router(reviews.router)
api_router.include_router(admin.router)
api_router.include_router(availability.router)
api_router.include_router(favorites.router)
