"""
Сервис геопривязки к субъектам Российской Федерации
Использует официальные шейп-файлы Росреестра для точной привязки координат
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict
import logging
import os
import zipfile
import requests
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from geoalchemy2.functions import ST_Contains, ST_Intersects
from geoalchemy2 import WKTElement

from app.models.region import RussianRegion, GeocodeCache, ShapefileUpdate
from app.core.config import settings
from app.db.database import async_session_maker

logger = logging.getLogger(__name__)


class GeocodingService:
    """
    Сервис геопривязки координат к субъектам РФ
    Обеспечивает быструю и точную привязку с кешированием результатов
    """
    
    def __init__(self):
        self.shapefile_dir = Path(settings.SHAPEFILE_DIR)
        self.shapefile_dir.mkdir(parents=True, exist_ok=True)
        
        # URLs для загрузки шейп-файлов (примерные, нужно уточнить актуальные)
        self.shapefile_sources = {
            'rosreestr_regions': 'https://data.gov.ru/opendata/7708660670-rosreestr-regions/data.zip',
            # Добавить другие источники по мере необходимости
        }
        
        # Кеш загруженных регионов в памяти для быстрого доступа
        self._regions_cache = None
        self._cache_updated = None
    
    async def geocode_point(self, longitude: float, latitude: float, 
                           use_cache: bool = True) -> Optional[Dict[str, str]]:
        """
        Определение субъекта РФ по координатам точки
        
        Args:
            longitude: Долгота (WGS84)
            latitude: Широта (WGS84)
            use_cache: Использовать кеш результатов
            
        Returns:
            Dict с информацией о регионе или None если не найден
        """
        try:
            # Проверка кеша
            if use_cache:
                cached_result = await self._get_from_cache(longitude, latitude)
                if cached_result:
                    return cached_result
            
            # Поиск региона в базе данных
            region_info = await self._find_region_by_coordinates(longitude, latitude)
            
            if region_info:
                # Сохранение в кеш
                if use_cache:
                    await self._save_to_cache(longitude, latitude, region_info)
                
                return {
                    'region_code': region_info['region_code'],
                    'region_name': region_info['name'],
                    'federal_district': region_info['federal_district'],
                    'region_type': region_info['region_type']
                }
            
            logger.warning(f"Регион не найден для координат: {latitude}, {longitude}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка геопривязки для координат {latitude}, {longitude}: {e}")
            return None
    
    async def geocode_multiple_points(self, coordinates: List[Tuple[float, float]]) -> List[Optional[Dict[str, str]]]:
        """
        Массовая геопривязка координат
        
        Args:
            coordinates: Список кортежей (longitude, latitude)
            
        Returns:
            Список результатов геопривязки
        """
        tasks = [
            self.geocode_point(lon, lat)
            for lon, lat in coordinates
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обработка исключений
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Ошибка в массовой геопривязке: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _find_region_by_coordinates(self, longitude: float, latitude: float) -> Optional[Dict]:
        """Поиск региона по координатам в базе данных"""
        async with async_session_maker() as session:
            try:
                # Создание точки в формате WKT
                point_wkt = f"POINT({longitude} {latitude})"
                point = WKTElement(point_wkt, srid=4326)
                
                # Запрос к базе данных с использованием пространственного индекса
                query = select(RussianRegion).where(
                    ST_Contains(RussianRegion.geometry, point)
                )
                
                result = await session.execute(query)
                region = result.scalar_one_or_none()
                
                if region:
                    return {
                        'region_code': region.region_code,
                        'name': region.name,
                        'federal_district': region.federal_district,
                        'region_type': region.region_type
                    }
                
                return None
                
            except Exception as e:
                logger.error(f"Ошибка запроса к базе данных для геопривязки: {e}")
                return None
    
    async def _get_from_cache(self, longitude: float, latitude: float) -> Optional[Dict[str, str]]:
        """Получение результата из кеша"""
        async with async_session_maker() as session:
            try:
                # Поиск в кеше с небольшим радиусом допуска (для учета округления)
                tolerance = 0.0001  # Примерно 10 метров
                
                query = select(GeocodeCache).where(
                    and_(
                        GeocodeCache.longitude.between(longitude - tolerance, longitude + tolerance),
                        GeocodeCache.latitude.between(latitude - tolerance, latitude + tolerance)
                    )
                )
                
                result = await session.execute(query)
                cache_entry = result.scalar_one_or_none()
                
                if cache_entry:
                    # Обновление статистики использования
                    cache_entry.last_used = datetime.utcnow()
                    cache_entry.use_count += 1
                    await session.commit()
                    
                    return {
                        'region_code': cache_entry.region_code,
                        'region_name': cache_entry.region_name,
                        'federal_district': None,  # Не храним в кеше для экономии места
                        'region_type': None
                    }
                
                return None
                
            except Exception as e:
                logger.error(f"Ошибка чтения кеша геопривязки: {e}")
                return None
    
    async def _save_to_cache(self, longitude: float, latitude: float, region_info: Dict):
        """Сохранение результата в кеш"""
        async with async_session_maker() as session:
            try:
                # Создание новой записи в кеше
                point_wkt = f"POINT({longitude} {latitude})"
                
                cache_entry = GeocodeCache(
                    longitude=longitude,
                    latitude=latitude,
                    point=WKTElement(point_wkt, srid=4326),
                    region_code=region_info['region_code'],
                    region_name=region_info['region_name']
                )
                
                session.add(cache_entry)
                await session.commit()
                
            except Exception as e:
                logger.error(f"Ошибка сохранения в кеш геопривязки: {e}")
    
    async def update_regions_from_shapefile(self, shapefile_path: str) -> Dict[str, int]:
        """
        Обновление данных о регионах из шейп-файла
        
        Args:
            shapefile_path: Путь к шейп-файлу
            
        Returns:
            Статистика обновления
        """
        stats = {
            'regions_added': 0,
            'regions_updated': 0,
            'regions_deleted': 0,
            'errors': 0
        }
        
        try:
            # Загрузка шейп-файла
            gdf = gpd.read_file(shapefile_path)
            
            # Приведение к нужной проекции (WGS84)
            if gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            
            async with async_session_maker() as session:
                # Получение существующих регионов
                existing_regions = await session.execute(select(RussianRegion))
                existing_codes = {region.region_code for region in existing_regions.scalars()}
                
                processed_codes = set()
                
                for idx, row in gdf.iterrows():
                    try:
                        # Извлечение данных из шейп-файла
                        region_data = self._extract_region_data(row)
                        
                        if not region_data:
                            continue
                        
                        processed_codes.add(region_data['region_code'])
                        
                        if region_data['region_code'] in existing_codes:
                            # Обновление существующего региона
                            await self._update_existing_region(session, region_data)
                            stats['regions_updated'] += 1
                        else:
                            # Добавление нового региона
                            await self._add_new_region(session, region_data)
                            stats['regions_added'] += 1
                            
                    except Exception as e:
                        logger.error(f"Ошибка обработки региона {idx}: {e}")
                        stats['errors'] += 1
                
                # Удаление регионов, которых нет в новом шейп-файле
                regions_to_delete = existing_codes - processed_codes
                for region_code in regions_to_delete:
                    await self._delete_region(session, region_code)
                    stats['regions_deleted'] += 1
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Ошибка обновления регионов из шейп-файла: {e}")
            stats['errors'] += 1
        
        logger.info(f"Обновление регионов завершено: {stats}")
        return stats
    
    def _extract_region_data(self, row) -> Optional[Dict]:
        """Извлечение данных региона из строки шейп-файла"""
        try:
            # Адаптация под структуру конкретного шейп-файла
            # Названия полей могут отличаться в зависимости от источника
            
            region_data = {
                'name': self._get_field_value(row, ['NAME', 'REGION_NAME', 'НАЗВАНИЕ']),
                'region_code': self._get_field_value(row, ['CODE', 'REGION_CODE', 'КОД']),
                'federal_district': self._get_field_value(row, ['FED_DIST', 'FEDERAL_DISTRICT', 'ФО']),
                'region_type': self._get_field_value(row, ['TYPE', 'REGION_TYPE', 'ТИП']),
                'geometry': row.geometry,
                'area_sq_km': row.geometry.area * 111.32 ** 2 if hasattr(row.geometry, 'area') else None  # Приблизительно
            }
            
            # Проверка обязательных полей
            if not region_data['name'] or not region_data['region_code']:
                logger.warning(f"Пропуск региона из-за отсутствия обязательных полей: {row}")
                return None
            
            return region_data
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных региона: {e}")
            return None
    
    def _get_field_value(self, row, field_names: List[str]) -> Optional[str]:
        """Получение значения поля по списку возможных названий"""
        for field_name in field_names:
            if field_name in row.index and row[field_name] is not None:
                return str(row[field_name]).strip()
        return None
    
    async def _update_existing_region(self, session: AsyncSession, region_data: Dict):
        """Обновление существующего региона"""
        query = select(RussianRegion).where(RussianRegion.region_code == region_data['region_code'])
        result = await session.execute(query)
        region = result.scalar_one_or_none()
        
        if region:
            region.name = region_data['name']
            region.federal_district = region_data['federal_district']
            region.region_type = region_data['region_type']
            region.geometry = WKTElement(region_data['geometry'].wkt, srid=4326)
            region.area_sq_km = region_data['area_sq_km']
            region.updated_at = datetime.utcnow()
    
    async def _add_new_region(self, session: AsyncSession, region_data: Dict):
        """Добавление нового региона"""
        region = RussianRegion(
            name=region_data['name'],
            region_code=region_data['region_code'],
            federal_district=region_data['federal_district'],
            region_type=region_data['region_type'],
            geometry=WKTElement(region_data['geometry'].wkt, srid=4326),
            area_sq_km=region_data['area_sq_km']
        )
        
        session.add(region)
    
    async def _delete_region(self, session: AsyncSession, region_code: str):
        """Удаление региона"""
        query = select(RussianRegion).where(RussianRegion.region_code == region_code)
        result = await session.execute(query)
        region = result.scalar_one_or_none()
        
        if region:
            region.is_active = False  # Мягкое удаление
    
    async def download_and_update_shapefiles(self) -> Dict[str, Dict]:
        """
        Загрузка и обновление шейп-файлов согласно регламенту
        Должно выполняться ежемесячно
        """
        results = {}
        
        for source_name, source_url in self.shapefile_sources.items():
            try:
                logger.info(f"Начало обновления шейп-файлов из источника: {source_name}")
                
                # Создание записи об обновлении
                update_record = await self._create_update_record(source_name, source_url)
                
                # Загрузка файла
                downloaded_path = await self._download_shapefile(source_url, source_name)
                
                if downloaded_path:
                    # Обновление данных
                    update_stats = await self.update_regions_from_shapefile(downloaded_path)
                    
                    # Обновление записи о результатах
                    await self._complete_update_record(update_record, update_stats, 'completed')
                    
                    results[source_name] = {
                        'status': 'success',
                        'stats': update_stats
                    }
                else:
                    await self._complete_update_record(update_record, {}, 'failed', 'Ошибка загрузки файла')
                    results[source_name] = {
                        'status': 'failed',
                        'error': 'Ошибка загрузки файла'
                    }
                
            except Exception as e:
                logger.error(f"Ошибка обновления шейп-файлов из {source_name}: {e}")
                results[source_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results
    
    async def _create_update_record(self, source_name: str, source_url: str) -> ShapefileUpdate:
        """Создание записи об обновлении"""
        async with async_session_maker() as session:
            update_record = ShapefileUpdate(
                source_url=source_url,
                filename=source_name,
                status='downloading',
                download_start=datetime.utcnow()
            )
            
            session.add(update_record)
            await session.commit()
            await session.refresh(update_record)
            
            return update_record
    
    async def _download_shapefile(self, url: str, filename: str) -> Optional[str]:
        """Загрузка шейп-файла"""
        try:
            response = requests.get(url, timeout=300)  # 5 минут таймаут
            response.raise_for_status()
            
            # Сохранение файла
            file_path = self.shapefile_dir / f"{filename}.zip"
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Распаковка архива
            extract_path = self.shapefile_dir / filename
            extract_path.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            # Поиск .shp файла
            shp_files = list(extract_path.glob('*.shp'))
            if shp_files:
                return str(shp_files[0])
            
            logger.error(f"Не найден .shp файл в архиве {filename}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка загрузки шейп-файла {url}: {e}")
            return None
    
    async def _complete_update_record(self, update_record: ShapefileUpdate, 
                                    stats: Dict, status: str, error_message: str = None):
        """Завершение записи об обновлении"""
        async with async_session_maker() as session:
            # Получение свежей записи
            query = select(ShapefileUpdate).where(ShapefileUpdate.id == update_record.id)
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            
            if record:
                record.status = status
                record.processing_end = datetime.utcnow()
                record.error_message = error_message
                
                if stats:
                    record.regions_added = stats.get('regions_added', 0)
                    record.regions_updated = stats.get('regions_updated', 0)
                    record.regions_deleted = stats.get('regions_deleted', 0)
                
                await session.commit()
    
    async def cleanup_old_cache(self, days_old: int = 30):
        """Очистка старых записей кеша"""
        async with async_session_maker() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                # Удаление записей старше указанного периода
                query = select(GeocodeCache).where(GeocodeCache.last_used < cutoff_date)
                result = await session.execute(query)
                old_entries = result.scalars().all()
                
                for entry in old_entries:
                    await session.delete(entry)
                
                await session.commit()
                
                logger.info(f"Удалено {len(old_entries)} старых записей из кеша геопривязки")
                
            except Exception as e:
                logger.error(f"Ошибка очистки кеша геопривязки: {e}")


# Глобальный экземпляр сервиса
geocoding_service = GeocodingService()

