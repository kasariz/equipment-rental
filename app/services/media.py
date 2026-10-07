import io
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings

EQUIPMENT_DIR = Path(settings.media_dir) / "equipment"
MAX_SIDE = 1600  # больше на сайте не нужно, а файлы получаются в разы легче

# Защита от «декомпрессионной бомбы»: крошечный файл, который разворачивается в гигапиксели
Image.MAX_IMAGE_PIXELS = 50_000_000


def ensure_media_dirs() -> None:
    EQUIPMENT_DIR.mkdir(parents=True, exist_ok=True)


async def save_equipment_photo(upload: UploadFile) -> str:
    """Проверяет, что файл — настоящая картинка, уменьшает и сохраняет в WebP.

    Расширению и Content-Type не доверяем: открываем файл через Pillow.
    Перекодирование заодно убирает EXIF с геолокацией телефона владельца.
    """
    limit = settings.max_photo_size_mb * 1024 * 1024
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Файл {upload.filename} больше {settings.max_photo_size_mb} МБ",
        )
    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format not in {"JPEG", "PNG", "WEBP", "MPO"}:
                raise UnidentifiedImageError
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.thumbnail((MAX_SIDE, MAX_SIDE))
            filename = f"{uuid.uuid4().hex}.webp"
            ensure_media_dirs()
            img.save(EQUIPMENT_DIR / filename, "WEBP", quality=82)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Файл {upload.filename} не похож на фото. Подойдут JPG, PNG или WebP",
        ) from e
    return filename


def delete_equipment_photo_file(filename: str) -> None:
    (EQUIPMENT_DIR / filename).unlink(missing_ok=True)
