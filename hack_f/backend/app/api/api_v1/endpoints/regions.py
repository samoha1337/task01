"""
Endpoints для работы с регионами РФ
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging

from app.db.database import get_db_session
from app.models.region import RussianRegion
from app.services.geocoding import geocoding_service

logger = logging.getLogger(__name__)

router = APIRouter()


class RegionResponse(BaseModel):
    """Ответ с информацией о регионе"""
    id: str
    name: str
    region_code: str
    federal_district: Optional[str]
    region_type: Optional[str]
    area_sq_km: Optional[float]


class GeocodeResponse(BaseModel):
    """Ответ геопривязки"""
    latitude: float
    longitude: float
    region_code: Optional[str]
    region_name: Optional[str]
    federal_district: Optional[str]
    region_type: Optional[str]


@router.get("/",
           summary="Список регионов РФ",
           description="Получение списка субъектов Российской Федерации")
async def get_regions(
    federal_district: Optional[str] = Query(None, description="Федеральный округ"),
    region_type: Optional[str] = Query(None, description="Тип региона"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение списка регионов"""
    try:
        query = select(RussianRegion).where(RussianRegion.is_active == True)
        
        if federal_district:
            query = query.where(RussianRegion.federal_district.ilike(f"%{federal_district}%"))
        
        if region_type:
            query = query.where(RussianRegion.region_type.ilike(f"%{region_type}%"))
        
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        regions = result.scalars().all()
        
        return {
            "regions": [
                {
                    "id": str(region.id),
                    "name": region.name,
                    "region_code": region.region_code,
                    "federal_district": region.federal_district,
                    "region_type": region.region_type,
                    "area_sq_km": region.area_sq_km
                }
                for region in regions
            ],
            "total": len(regions),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения списка регионов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")


@router.get("/geocode",
           summary="Геопривязка координат",
           description="Определение региона по координатам")
async def geocode_coordinates(
    latitude: float = Query(..., ge=-90, le=90, description="Широта"),
    longitude: float = Query(..., ge=-180, le=180, description="Долгота")
):
    """Геопривязка координат к региону"""
    try:
        region_info = await geocoding_service.geocode_point(longitude, latitude)
        
        if not region_info:
            return {
                "latitude": latitude,
                "longitude": longitude,
                "region_code": None,
                "region_name": None,
                "federal_district": None,
                "region_type": None,
                "message": "Регион не найден для указанных координат"
            }
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "region_code": region_info["region_code"],
            "region_name": region_info["region_name"],
            "federal_district": region_info.get("federal_district"),
            "region_type": region_info.get("region_type")
        }
        
    except Exception as e:
        logger.error(f"Ошибка геопривязки координат {latitude}, {longitude}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка геопривязки")

