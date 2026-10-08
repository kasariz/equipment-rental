# Импорт всех моделей в одном месте, чтобы Alembic видел их при автогенерации
from app.models.booking import Booking, BookingStatus, RateType
from app.models.category import Category
from app.models.equipment import Equipment, EquipmentStatus
from app.models.favorite import Favorite
from app.models.photo import EquipmentPhoto
from app.models.review import Review, ReviewDirection
from app.models.user import User, UserRole

__all__ = [
    "Booking",
    "BookingStatus",
    "Category",
    "Equipment",
    "EquipmentPhoto",
    "EquipmentStatus",
    "Favorite",
    "RateType",
    "Review",
    "ReviewDirection",
    "User",
    "UserRole",
]
