"""
Endpoints для работы с данными полетов БПЛА
"""

from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from pydantic import BaseModel
import logging

from app.db.database import get_db_session
from app.models.flight import Flight

logger = logging.getLogger(__name__)

router = APIRouter()


class FlightResponse(BaseModel):
    """Модель ответа с данными полета"""
    id: str
    flight_id: str
    aircraft_type: Optional[str]
    aircraft_registration: Optional[str]
    departure_time: Optional[datetime]
    arrival_time: Optional[datetime]
    duration_minutes: Optional[int]
    departure_coordinates: Optional[List[float]]
    arrival_coordinates: Optional[List[float]]
    region_departure: Optional[str]
    region_arrival: Optional[str]
    altitude_max: Optional[float]
    distance_km: Optional[float]
    operator_name: Optional[str]
    flight_purpose: Optional[str]
    is_valid: bool
    created_at: datetime


class FlightSearchRequest(BaseModel):
    """Параметры поиска полетов"""
    flight_id: Optional[str] = None
    aircraft_type: Optional[str] = None
    region_departure: Optional[str] = None
    region_arrival: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    limit: int = 50
    offset: int = 0


@router.get("/", 
           summary="Поиск полетов",
           description="Поиск полетов по различным критериям")
async def search_flights(
    flight_id: Optional[str] = Query(None, description="Идентификатор полета"),
    aircraft_type: Optional[str] = Query(None, description="Тип БПЛА"),
    region_departure: Optional[str] = Query(None, description="Регион вылета"),
    region_arrival: Optional[str] = Query(None, description="Регион прилета"),
    date_from: Optional[date] = Query(None, description="Дата начала периода"),
    date_to: Optional[date] = Query(None, description="Дата окончания периода"),
    limit: int = Query(50, ge=1, le=1000, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    db: AsyncSession = Depends(get_db_session)
):
    """Поиск полетов по критериям"""
    try:
        query = select(Flight).where(Flight.is_valid == True)
        
        # Применение фильтров
        if flight_id:
            query = query.where(Flight.flight_id.ilike(f"%{flight_id}%"))
        
        if aircraft_type:
            query = query.where(Flight.aircraft_type == aircraft_type)
        
        if region_departure:
            query = query.where(Flight.region_departure.ilike(f"%{region_departure}%"))
        
        if region_arrival:
            query = query.where(Flight.region_arrival.ilike(f"%{region_arrival}%"))
        
        if date_from:
            query = query.where(Flight.departure_time >= date_from)
        
        if date_to:
            query = query.where(Flight.departure_time <= date_to)
        
        # Подсчет общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Применение пагинации и сортировки
        query = query.order_by(desc(Flight.departure_time)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        flights = result.scalars().all()
        
        # Формирование ответа
        flights_data = []
        for flight in flights:
            flight_data = {
                "id": str(flight.id),
                "flight_id": flight.flight_id,
                "aircraft_type": flight.aircraft_type,
                "aircraft_registration": flight.aircraft_registration,
                "departure_time": flight.departure_time,
                "arrival_time": flight.arrival_time,
                "duration_minutes": flight.duration_minutes,
                "departure_coordinates": list(flight.departure_coordinates) if flight.departure_coordinates else None,
                "arrival_coordinates": list(flight.arrival_coordinates) if flight.arrival_coordinates else None,
                "region_departure": flight.region_departure,
                "region_arrival": flight.region_arrival,
                "altitude_max": flight.altitude_max,
                "distance_km": flight.distance_km,
                "operator_name": flight.operator_name,
                "flight_purpose": flight.flight_purpose,
                "is_valid": flight.is_valid,
                "created_at": flight.created_at
            }
            flights_data.append(flight_data)
        
        return {
            "flights": flights_data,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(flights) < total
        }
        
    except Exception as e:
        logger.error(f"Ошибка поиска полетов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка поиска полетов")


@router.get("/{flight_id}",
           summary="Получение полета по ID",
           description="Получение подробной информации о конкретном полете")
async def get_flight(
    flight_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Получение полета по идентификатору"""
    try:
        query = select(Flight).where(Flight.flight_id == flight_id)
        result = await db.execute(query)
        flight = result.scalar_one_or_none()
        
        if not flight:
            raise HTTPException(status_code=404, detail="Полет не найден")
        
        return {
            "id": str(flight.id),
            "flight_id": flight.flight_id,
            "aircraft_type": flight.aircraft_type,
            "aircraft_registration": flight.aircraft_registration,
            "departure_time": flight.departure_time,
            "arrival_time": flight.arrival_time,
            "duration_minutes": flight.duration_minutes,
            "departure_coordinates": list(flight.departure_coordinates) if flight.departure_coordinates else None,
            "arrival_coordinates": list(flight.arrival_coordinates) if flight.arrival_coordinates else None,
            "region_departure": flight.region_departure,
            "region_arrival": flight.region_arrival,
            "region_departure_code": flight.region_departure_code,
            "region_arrival_code": flight.region_arrival_code,
            "altitude_max": flight.altitude_max,
            "altitude_min": flight.altitude_min,
            "distance_km": flight.distance_km,
            "operator_name": flight.operator_name,
            "operator_license": flight.operator_license,
            "flight_purpose": flight.flight_purpose,
            "raw_message": flight.raw_message,
            "message_type": flight.message_type,
            "message_source": flight.message_source,
            "is_processed": flight.is_processed,
            "is_valid": flight.is_valid,
            "validation_errors": flight.validation_errors,
            "created_at": flight.created_at,
            "updated_at": flight.updated_at,
            "processed_at": flight.processed_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения полета {flight_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных полета")


@router.get("/statistics/summary",
           summary="Общая статистика полетов",
           description="Получение общей статистики по всем полетам")
async def get_flights_summary(
    date_from: Optional[date] = Query(None, description="Дата начала периода"),
    date_to: Optional[date] = Query(None, description="Дата окончания периода"),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение общей статистики полетов"""
    try:
        query = select(Flight).where(Flight.is_valid == True)
        
        # Применение фильтра по дате
        if date_from:
            query = query.where(Flight.departure_time >= date_from)
        if date_to:
            query = query.where(Flight.departure_time <= date_to)
        
        # Общее количество полетов
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total_flights = total_result.scalar()
        
        # Средняя продолжительность
        avg_duration_query = select(func.avg(Flight.duration_minutes)).select_from(query.subquery())
        avg_duration_result = await db.execute(avg_duration_query)
        avg_duration = avg_duration_result.scalar()
        
        # Статистика по типам БПЛА
        aircraft_stats_query = select(
            Flight.aircraft_type,
            func.count(Flight.id).label('count')
        ).select_from(query.subquery()).group_by(Flight.aircraft_type)
        
        aircraft_stats_result = await db.execute(aircraft_stats_query)
        aircraft_stats = {row.aircraft_type: row.count for row in aircraft_stats_result}
        
        # Топ регионов по количеству полетов
        region_stats_query = select(
            Flight.region_departure,
            func.count(Flight.id).label('count')
        ).select_from(query.subquery()).where(
            Flight.region_departure.is_not(None)
        ).group_by(Flight.region_departure).order_by(desc('count')).limit(10)
        
        region_stats_result = await db.execute(region_stats_query)
        top_regions = [
            {"region": row.region_departure, "flights": row.count}
            for row in region_stats_result
        ]
        
        return {
            "total_flights": total_flights,
            "average_duration_minutes": round(avg_duration, 2) if avg_duration else None,
            "aircraft_types": aircraft_stats,
            "top_regions": top_regions,
            "period": {
                "from": date_from,
                "to": date_to
            }
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики полетов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")

