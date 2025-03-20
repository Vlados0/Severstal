from datetime import datetime, timezone
from typing import List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter(prefix="/rolls", tags=["rolls"])


@router.post("/", response_model=schemas.RollResponse)
def create_roll(roll: schemas.RollCreate, db: Session = Depends(get_db)) -> models.Roll:
    try:
        if roll.length <= 0 or roll.weight <= 0:
            raise HTTPException(
                status_code=400, detail="Length and weight must be positive"
            )
        db_roll = models.Roll(**roll.dict())
        db.add(db_roll)
        db.commit()
        db.refresh(db_roll)
        return db_roll
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.delete("/{roll_id}", response_model=schemas.RollResponse)
def delete_roll(roll_id: int, db: Session = Depends(get_db)) -> models.Roll:
    try:
        db_roll = db.query(models.Roll).get(roll_id)
        if not db_roll:
            raise HTTPException(status_code=404, detail="Roll not found")
        if db_roll.removed_date is not None:
            raise HTTPException(status_code=400, detail="Roll already removed")

        db_roll.removed_date = datetime.now(timezone.utc).replace(microsecond=0)

        db.commit()
        db.refresh(db_roll)
        return cast(models.Roll, db_roll)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/", response_model=List[schemas.RollResponse])
def get_rolls(
    id_start: Optional[int] = Query(None),
    id_end: Optional[int] = Query(None),
    length_start: Optional[float] = Query(None),
    length_end: Optional[float] = Query(None),
    weight_start: Optional[float] = Query(None),
    weight_end: Optional[float] = Query(None),
    added_start: Optional[datetime] = Query(None),
    added_end: Optional[datetime] = Query(None),
    removed_start: Optional[datetime] = Query(None),
    removed_end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
) -> List[models.Roll]:
    try:
        filters = []

        if id_start is not None:
            filters.append(models.Roll.id >= id_start)
        if id_end is not None:
            filters.append(models.Roll.id <= id_end)

        if length_start is not None:
            filters.append(models.Roll.length >= length_start)
        if length_end is not None:
            filters.append(models.Roll.length <= length_end)

        if weight_start is not None:
            filters.append(models.Roll.weight >= weight_start)
        if weight_end is not None:
            filters.append(models.Roll.weight <= weight_end)

        if added_start is not None:
            filters.append(models.Roll.added_date >= added_start)
        if added_end is not None:
            filters.append(models.Roll.added_date <= added_end)

        if removed_start is not None:
            filters.append(models.Roll.removed_date >= removed_start)
        if removed_end is not None:
            filters.append(models.Roll.removed_date <= removed_end)

        rolls = db.query(models.Roll).filter(*filters).all()
        return rolls
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/statistics", response_model=schemas.StatisticsResponse)
def get_statistics(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    try:
        if start_date > end_date:
            raise HTTPException(
                status_code=400, detail="Start date must be before end date"
            )

        presence_condition = and_(
            models.Roll.added_date <= end_date,
            or_(
                models.Roll.removed_date >= start_date,
                models.Roll.removed_date.is_(None),
            ),
        )

        added_count = (
            db.query(func.count(models.Roll.id))
            .filter(models.Roll.added_date.between(start_date, end_date))
            .scalar()
        )

        removed_count = (
            db.query(func.count(models.Roll.id))
            .filter(models.Roll.removed_date.between(start_date, end_date))
            .scalar()
        )

        stats = (
            db.query(
                func.avg(models.Roll.length).label("avg_length"),
                func.avg(models.Roll.weight).label("avg_weight"),
                func.min(models.Roll.length).label("min_length"),
                func.max(models.Roll.length).label("max_length"),
                func.min(models.Roll.weight).label("min_weight"),
                func.max(models.Roll.weight).label("max_weight"),
                func.sum(models.Roll.weight).label("total_weight"),
            )
            .filter(presence_condition)
            .first()
        )

        interval_query = (
            db.query(
                (
                    func.extract(
                        "epoch",
                        func.max(models.Roll.removed_date - models.Roll.added_date),
                    )
                    / 86400
                ).label("max_days"),
                (
                    func.extract(
                        "epoch",
                        func.min(models.Roll.removed_date - models.Roll.added_date),
                    )
                    / 86400
                ).label("min_days"),
            )
            .filter(models.Roll.removed_date.isnot(None), presence_condition)
            .first()
        )

        max_interval = (
            round(interval_query.max_days, 2)
            if interval_query and interval_query.max_days
            else None
        )

        min_interval = (
            round(interval_query.min_days, 2)
            if interval_query and interval_query.min_days
            else None
        )

        start_date_utc = start_date.astimezone(timezone.utc).date()
        end_date_utc = end_date.astimezone(timezone.utc).date()

        sql = """
        SELECT
            day::date AS day,
            COUNT(rolls.id) AS rolls_count,
            COALESCE(SUM(rolls.weight), 0) AS total_weight
        FROM
            generate_series(:start_date, :end_date, interval '1 day') AS day
        LEFT JOIN rolls
            ON rolls.added_date < (day + interval '1 day')
            AND (rolls.removed_date >= day OR rolls.removed_date IS NULL)
        GROUP BY day
        ORDER BY day;
        """

        result = db.execute(
            text(sql), {"start_date": start_date_utc, "end_date": end_date_utc}
        )
        rows = result.fetchall()

        min_count_days = []
        max_count_days = []
        min_weight_days = []
        max_weight_days = []
        min_count = max_count = min_weight = max_weight = None

        for row in rows:
            current_day = row.day
            count = row.rolls_count
            weight = row.total_weight

            if min_count is None or count < min_count:
                min_count = count
                min_count_days = [current_day]
            elif count == min_count:
                min_count_days.append(current_day)

            if max_count is None or count > max_count:
                max_count = count
                max_count_days = [current_day]
            elif count == max_count:
                max_count_days.append(current_day)

            if min_weight is None or weight < min_weight:
                min_weight = weight
                min_weight_days = [current_day]
            elif weight == min_weight:
                min_weight_days.append(current_day)

            if max_weight is None or weight > max_weight:
                max_weight = weight
                max_weight_days = [current_day]
            elif weight == max_weight:
                max_weight_days.append(current_day)

        day_min_count = min(min_count_days) if min_count_days else None
        day_max_count = min(max_count_days) if max_count_days else None
        day_min_weight = min(min_weight_days) if min_weight_days else None
        day_max_weight = min(max_weight_days) if max_weight_days else None

        return {
            "added_count": added_count,
            "removed_count": removed_count,
            "avg_length": stats.avg_length,
            "avg_weight": stats.avg_weight,
            "min_length": stats.min_length,
            "max_length": stats.max_length,
            "min_weight": stats.min_weight,
            "max_weight": stats.max_weight,
            "total_weight": stats.total_weight,
            "max_interval": max_interval,
            "min_interval": min_interval,
            "day_min_count": day_min_count,
            "day_max_count": day_max_count,
            "day_min_weight": day_min_weight,
            "day_max_weight": day_max_weight,
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
