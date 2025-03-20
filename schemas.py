from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict


class RollCreate(BaseModel):
    length: float
    weight: float


class RollResponse(BaseModel):
    id: int
    length: float
    weight: float
    added_date: datetime
    removed_date: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: (
                v.astimezone(ZoneInfo("Europe/Moscow"))
                .replace(microsecond=0)
                .isoformat()
            )
        },
    )


class StatisticsResponse(BaseModel):
    added_count: int
    removed_count: int
    avg_length: Optional[float]
    avg_weight: Optional[float]
    min_length: Optional[float]
    max_length: Optional[float]
    min_weight: Optional[float]
    max_weight: Optional[float]
    total_weight: Optional[float]
    max_interval: Optional[float]
    min_interval: Optional[float]
    day_min_count: Optional[date]
    day_max_count: Optional[date]
    day_min_weight: Optional[date]
    day_max_weight: Optional[date]
