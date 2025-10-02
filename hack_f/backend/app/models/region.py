"""
Модели данных для геопространственной привязки к субъектам РФ
Используются официальные шейп-файлы Росреестра
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from datetime import datetime
import uuid

from app.db.database import Base


class RussianRegion(Base):
    """
    Модель субъектов Российской Федерации
    Содержит границы регионов из официальных шейп-файлов Росреестра
    """
    __tablename__ = "russian_regions"
    __table_args__ = (
        # Пространственные индексы для быстрого поиска
        Index('ix_regions_geometry', 'geometry', postgresql_using='gist'),
        Index('ix_regions_code', 'region_code'),
        Index('ix_regions_name', 'name'),
        {'schema': 'geo'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Основные данные региона
    name = Column(String(200), nullable=False, comment="Наименование субъекта РФ")
    region_code = Column(String(10), nullable=False, unique=True, comment="Код субъекта РФ")
    federal_district = Column(String(100), comment="Федеральный округ")
    region_type = Column(String(50), comment="Тип субъекта (область, республика, край и т.д.)")
    
    # Геометрия границ региона (в проекции WGS84)
    geometry = Column(
        Geometry('MULTIPOLYGON', srid=4326), 
        nullable=False, 
        comment="Границы субъекта РФ"
    )
    
    # Дополнительные данные
    area_sq_km = Column(Float, comment="Площадь в квадратных километрах")
    population = Column(Integer, comment="Население")
    administrative_center = Column(String(100), comment="Административный центр")
    
    # Метаданные шейп-файла
    shapefile_source = Column(String(200), comment="Источник шейп-файла")
    shapefile_date = Column(DateTime(timezone=True), comment="Дата шейп-файла")
    rosreestr_id = Column(String(50), comment="Идентификатор Росреестра")
    
    # Служебные поля
    is_active = Column(Boolean, default=True, comment="Активность региона")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<RussianRegion(name='{self.name}', code='{self.region_code}')>"


class GeocodeCache(Base):
    """
    Кеш результатов геопривязки
    Для оптимизации повторных запросов геопривязки
    """
    __tablename__ = "geocode_cache"
    __table_args__ = (
        Index('ix_geocode_point', 'point', postgresql_using='gist'),
        Index('ix_geocode_coordinates', 'longitude', 'latitude'),
        {'schema': 'geo'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Координаты точки
    longitude = Column(Float, nullable=False, comment="Долгота")
    latitude = Column(Float, nullable=False, comment="Широта")
    point = Column(Geometry('POINT', srid=4326), nullable=False, comment="Геометрическая точка")
    
    # Результат геопривязки
    region_id = Column(UUID(as_uuid=True), comment="ID региона")
    region_name = Column(String(200), comment="Название региона")
    region_code = Column(String(10), comment="Код региона")
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_used = Column(DateTime(timezone=True), default=datetime.utcnow)
    use_count = Column(Integer, default=1, comment="Количество использований")
    
    def __repr__(self):
        return f"<GeocodeCache(lat={self.latitude}, lon={self.longitude}, region='{self.region_name}')>"


class ShapefileUpdate(Base):
    """
    Модель для отслеживания обновлений шейп-файлов
    Согласно требованию ежемесячного обновления
    """
    __tablename__ = "shapefile_updates"
    __table_args__ = (
        Index('ix_shapefile_updates_date', 'update_date'),
        Index('ix_shapefile_updates_status', 'status'),
        {'schema': 'geo'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Информация об обновлении
    source_url = Column(String(500), comment="URL источника шейп-файла")
    filename = Column(String(255), comment="Имя файла")
    file_hash = Column(String(64), comment="MD5 хеш файла")
    file_size = Column(Integer, comment="Размер файла")
    
    # Статус обновления
    status = Column(String(20), default='pending', comment="Статус: pending, downloading, processing, completed, failed")
    error_message = Column(Text, comment="Сообщение об ошибке")
    
    # Результаты обновления
    regions_added = Column(Integer, default=0, comment="Количество добавленных регионов")
    regions_updated = Column(Integer, default=0, comment="Количество обновленных регионов")
    regions_deleted = Column(Integer, default=0, comment="Количество удаленных регионов")
    
    # Временные метки
    update_date = Column(DateTime(timezone=True), default=datetime.utcnow, comment="Дата обновления")
    download_start = Column(DateTime(timezone=True), comment="Начало загрузки")
    download_end = Column(DateTime(timezone=True), comment="Окончание загрузки")
    processing_start = Column(DateTime(timezone=True), comment="Начало обработки")
    processing_end = Column(DateTime(timezone=True), comment="Окончание обработки")
    
    def __repr__(self):
        return f"<ShapefileUpdate(filename='{self.filename}', status='{self.status}', date='{self.update_date}')>"

