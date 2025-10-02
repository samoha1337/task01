"""
Endpoints для генерации отчетов и графиков (JSON, PNG/JPEG)
Соответствует требованиям ТЗ по отчетам и визуализации.
"""

from typing import List, Optional, Dict
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from pydantic import BaseModel
import logging
import io

import matplotlib

# Используем безголовый backend для серверной генерации
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from app.db.database import get_db_session
from app.models.flight import Flight

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_dates(df: Optional[str], dt: Optional[str]) -> (Optional[datetime], Optional[datetime]):
    d_from = None
    d_to = None
    try:
        if df:
            # Поддержка различных форматов дат
            if len(df) == 10 and df.count('-') == 2:  # YYYY-MM-DD
                d_from = datetime.fromisoformat(df + "T00:00:00")
            elif len(df) == 19 and df.count('-') == 2 and df.count(':') == 2:  # YYYY-MM-DDTHH:MM:SS
                d_from = datetime.fromisoformat(df)
            else:
                d_from = datetime.fromisoformat(df)
        if dt:
            # Поддержка различных форматов дат
            if len(dt) == 10 and dt.count('-') == 2:  # YYYY-MM-DD
                d_to = datetime.fromisoformat(dt + "T23:59:59")
            elif len(dt) == 19 and dt.count('-') == 2 and dt.count(':') == 2:  # YYYY-MM-DDTHH:MM:SS
                d_to = datetime.fromisoformat(dt)
            else:
                d_to = datetime.fromisoformat(dt)
    except Exception as e:
        logger.warning(f"Ошибка парсинга дат: {e}, df={df}, dt={dt}")
    return d_from, d_to


@router.get(
    "/summary.json",
    summary="JSON-отчет: сводка по полетам",
    description="Общие метрики: количество полетов, суммарное время, средняя/медианная продолжительность"
)
async def summary_json(
    date_from: Optional[str] = Query(None, description="Дата начала периода ISO, напр. 2025-10-01"),
    date_to: Optional[str] = Query(None, description="Дата окончания периода ISO, напр. 2025-10-31"),
    region_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    d_from, d_to = _parse_dates(date_from, date_to)

    # Создаем базовый запрос с фильтрами
    base_query = select(Flight).where(Flight.is_valid == True)
    if region_code:
        base_query = base_query.where(or_(Flight.region_departure_code == region_code, Flight.region_arrival_code == region_code))
    if d_from:
        base_query = base_query.where(Flight.departure_time >= d_from)
    if d_to:
        base_query = base_query.where(Flight.departure_time <= d_to)

    # counts
    total = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total_flights = total.scalar() or 0

    # Создаем запросы для агрегации с теми же фильтрами
    avg_q = select(func.avg(Flight.duration_minutes)).select_from(
        base_query.where(Flight.duration_minutes.is_not(None)).subquery()
    )
    median_q = select(func.percentile_cont(0.5).within_group(Flight.duration_minutes)).select_from(
        base_query.where(Flight.duration_minutes.is_not(None)).subquery()
    )
    sum_q = select(func.sum(Flight.duration_minutes)).select_from(
        base_query.where(Flight.duration_minutes.is_not(None)).subquery()
    )

    avg_val = (await db.execute(avg_q)).scalar() or 0.0
    median_val = (await db.execute(median_q)).scalar() or 0.0
    total_minutes = (await db.execute(sum_q)).scalar() or 0

    return {
        "total_flights": total_flights,
        "total_flight_time_hours": round((total_minutes or 0) / 60.0, 2),
        "avg_duration_minutes": round(avg_val, 2),
        "median_duration_minutes": round(median_val, 2),
    }


@router.get(
    "/regions.json",
    summary="JSON-отчет: распределение полетов по регионам",
    description="Агрегация количества полетов по субъектам РФ"
)
async def regions_json(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 30,
    db: AsyncSession = Depends(get_db_session)
):
    d_from, d_to = _parse_dates(date_from, date_to)

    q = select(
        Flight.region_departure_code.label("region_code"),
        Flight.region_departure.label("region_name"),
        func.count(Flight.id).label("flights_count"),
    ).where(and_(Flight.is_valid == True, Flight.region_departure_code.is_not(None)))

    if d_from:
        q = q.where(Flight.departure_time >= d_from)
    if d_to:
        q = q.where(Flight.departure_time <= d_to)

    q = q.group_by(Flight.region_departure_code, Flight.region_departure).order_by(desc("flights_count")).limit(limit)
    rows = (await db.execute(q)).all()
    return {"items": [dict(region_code=r.region_code, region_name=r.region_name, flights_count=r.flights_count) for r in rows]}


@router.get(
    "/regions/chart.png",
    summary="PNG-график: распределение полетов по регионам",
    description="Столбчатая диаграмма топ-N регионов по количеству полетов"
)
async def regions_chart_png(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 15,
    db: AsyncSession = Depends(get_db_session)
):
    data = await regions_json(date_from=date_from, date_to=date_to, limit=limit, db=db)  # reuse aggregation
    items = data["items"]
    if not items:
        raise HTTPException(status_code=404, detail="Нет данных для построения графика")

    regions = [i["region_name"] or i["region_code"] for i in items]
    counts = [i["flights_count"] for i in items]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(regions, counts, color="#1890ff")
    plt.title("Распределение количества полетов по регионам РФ")
    plt.ylabel("Кол-во полетов")
    plt.xticks(rotation=45, ha="right")
    for b, v in zip(bars, counts):
        plt.text(b.get_x() + b.get_width() / 2, b.get_height(), str(v), ha="center", va="bottom", fontsize=8)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get(
    "/trends.json",
    summary="JSON-отчет: временные ряды",
    description="Количество полетов по дням"
)
async def trends_json(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    d_from, d_to = _parse_dates(date_from, date_to)

    base = select(
        func.date(Flight.departure_time).label("flight_date"),
        func.count(Flight.id).label("count"),
    ).where(Flight.is_valid == True)

    if d_from:
        base = base.where(Flight.departure_time >= d_from)
    if d_to:
        base = base.where(Flight.departure_time <= d_to)

    base = base.group_by("flight_date").order_by("flight_date")
    rows = (await db.execute(base)).all()
    return {"items": [dict(date=str(r.flight_date), count=r.count) for r in rows]}


@router.get(
    "/trends/chart.png",
    summary="PNG-график: временные ряды",
    description="Линейный график количества полетов по датам"
)
async def trends_chart_png(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    data = await trends_json(date_from=date_from, date_to=date_to, db=db)
    items = data["items"]
    if not items:
        raise HTTPException(status_code=404, detail="Нет данных для построения графика")

    x = [i["date"] for i in items]
    y = [i["count"] for i in items]

    plt.figure(figsize=(10, 5))
    plt.plot(x, y, marker="o", color="#52c41a")
    plt.title("Временной ряд количества полетов")
    plt.ylabel("Кол-во полетов")
    plt.xlabel("Дата")
    plt.xticks(rotation=45, ha="right")
    plt.grid(alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get(
    "/flights.json",
    summary="JSON-отчет: перечень полетов",
    description="Экспорт списка полетов с ключевыми атрибутами"
)
async def flights_list_json(
    limit: int = 1000,
    offset: int = 0,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    d_from, d_to = _parse_dates(date_from, date_to)

    q = select(Flight).where(Flight.is_valid == True)
    if d_from:
        q = q.where(Flight.departure_time >= d_from)
    if d_to:
        q = q.where(Flight.departure_time <= d_to)
    
    q = q.order_by(desc(Flight.departure_time)).offset(offset).limit(limit)

    rows = (await db.execute(q)).scalars().all()
    def to_dict(f: Flight) -> Dict:
        return {
            "flight_id": f.flight_id,
            "aircraft_type": f.aircraft_type,
            "departure_time": f.departure_time.isoformat() if f.departure_time else None,
            "arrival_time": f.arrival_time.isoformat() if f.arrival_time else None,
            "duration_minutes": f.duration_minutes,
            "region_departure": f.region_departure,
            "region_arrival": f.region_arrival,
        }

    return {"items": [to_dict(f) for f in rows], "limit": limit, "offset": offset}

