from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    rating: int = Field(ge=1, le=5)
    text: str | None = Field(default=None, max_length=2000)


class ReviewRead(BaseModel):
    id: int
    direction: str = Field(description="about_owner — отзыв о владельце, about_renter — об арендаторе")
    rating: int
    text: str | None
    created_at: datetime
    author_name: str = Field(description="Имя и первая буква фамилии: «Анна К.»")
    equipment_name: str


class UserReviewsSummary(BaseModel):
    rating: float | None
    count: int


class UserReviews(BaseModel):
    rating: float | None
    count: int
    items: list[ReviewRead]


class MyRatings(BaseModel):
    as_owner: UserReviewsSummary
    as_renter: UserReviewsSummary
