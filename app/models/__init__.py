# Импорт всех моделей в одном месте, чтобы Alembic видел их при автогенерации
from app.models.booking import Booking, BookingStatus, RateType
from app.models.category import Category
from app.models.equipment import Equipment, EquipmentStatus
from app.models.photo import EquipmentPhoto
from app.models.user import User, UserRole

__all__ = [
    "Booking",
    "BookingStatus",
    "RateType",
    "Category",
    "Equipment",
    "EquipmentPhoto",
    "EquipmentStatus",
    "User",
    "UserRole",
]
