from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer

from database import Base


def get_utc_time() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class Roll(Base):
    __tablename__ = "rolls"

    id = Column(Integer, primary_key=True)
    length = Column(Float, nullable=False)
    weight = Column(Float, nullable=False)
    added_date = Column(DateTime(timezone=True), default=get_utc_time)
    removed_date = Column(DateTime(timezone=True), nullable=True)
