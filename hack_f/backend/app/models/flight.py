"""
Модели данных для полетов БПЛА
В соответствии с Табелем сообщений Минтранса России от 24.01.2013 №13
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from datetime import datetime
from typing import Optional
import uuid

from app.db.database import Base


class Flight(Base):
    """
    Модель полета БПЛА
    Содержит основную информацию о полете согласно стандартным сообщениям
    """
    __tablename__ = "flights"
    __table_args__ = (
        # Индексы для оптимизации запросов
        Index('ix_flights_flight_id', 'flight_id'),
        Index('ix_flights_departure_time', 'departure_time'),
        Index('ix_flights_arrival_time', 'arrival_time'),
        Index('ix_flights_aircraft_type', 'aircraft_type'),
        Index('ix_flights_region_departure', 'region_departure'),
        Index('ix_flights_region_arrival', 'region_arrival'),
        # Пространственные индексы (GiST)
        Index('ix_flights_departure_point', 'departure_point', postgresql_using='gist'),
        Index('ix_flights_arrival_point', 'arrival_point', postgresql_using='gist'),
        # Композитный индекс для поиска дубликатов
        Index('ix_flights_unique', 'flight_id', 'departure_time', 'departure_point'),
        {'schema': 'flights'}
    )
    
    # Первичный ключ
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Основные данные полета
    flight_id = Column(String(50), nullable=False, comment="ID полета из телеграммы")
    aircraft_type = Column(String(20), nullable=False, comment="Тип БПЛА")
    aircraft_registration = Column(String(20), comment="Регистрационный номер")
    
    # Временные данные
    departure_time = Column(DateTime(timezone=True), nullable=False, comment="Время взлета")
    arrival_time = Column(DateTime(timezone=True), comment="Время посадки")
    duration_minutes = Column(Integer, comment="Продолжительность полета в минутах")
    
    # Пространственные данные (координаты в WGS84)
    departure_point = Column(
        Geometry('POINT', srid=4326), 
        nullable=False, 
        comment="Точка взлета"
    )
    arrival_point = Column(
        Geometry('POINT', srid=4326), 
        comment="Точка посадки"
    )
    
    # Геопривязка к субъектам РФ
    region_departure = Column(String(100), comment="Субъект РФ места взлета")
    region_arrival = Column(String(100), comment="Субъект РФ места посадки")
    region_departure_code = Column(String(10), comment="Код субъекта РФ места взлета")
    region_arrival_code = Column(String(10), comment="Код субъекта РФ места посадки")
    
    # Дополнительные данные
    altitude_max = Column(Float, comment="Максимальная высота полета (м)")
    altitude_min = Column(Float, comment="Минимальная высота полета (м)")
    distance_km = Column(Float, comment="Расстояние полета (км)")
    
    # Данные о операторе и цели полета
    operator_name = Column(String(200), comment="Наименование оператора")
    operator_license = Column(String(50), comment="Номер лицензии оператора")
    flight_purpose = Column(String(200), comment="Цель полета")
    
    # Технические данные
    raw_message = Column(Text, comment="Исходное сообщение")
    message_type = Column(String(10), comment="Тип сообщения (FPL, DEP, ARR и т.д.)")
    message_source = Column(String(100), comment="Источник сообщения")
    
    # Статус обработки
    is_processed = Column(Boolean, default=False, comment="Флаг обработки")
    is_valid = Column(Boolean, default=True, comment="Флаг валидности данных")
    validation_errors = Column(Text, comment="Ошибки валидации")
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, comment="Время создания записи")
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, comment="Время обновления записи")
    processed_at = Column(DateTime(timezone=True), comment="Время обработки")
    
    def __repr__(self):
        return f"<Flight(flight_id='{self.flight_id}', aircraft_type='{self.aircraft_type}', departure_time='{self.departure_time}')>"
    
    @property
    def departure_coordinates(self) -> Optional[tuple]:
        """Возвращает координаты взлета в формате (longitude, latitude)"""
        if self.departure_point:
            # Извлечение координат из геометрии PostGIS
            return (self.departure_point.x, self.departure_point.y)
        return None
    
    @property
    def arrival_coordinates(self) -> Optional[tuple]:
        """Возвращает координаты посадки в формате (longitude, latitude)"""
        if self.arrival_point:
            return (self.arrival_point.x, self.arrival_point.y)
        return None
    
    def calculate_duration(self) -> Optional[int]:
        """Вычисляет продолжительность полета в минутах"""
        if self.departure_time and self.arrival_time:
            delta = self.arrival_time - self.departure_time
            return int(delta.total_seconds() / 60)
        return None


class FlightBatch(Base):
    """
    Модель пакета полетов
    Для отслеживания загруженных пакетов данных
    """
    __tablename__ = "flight_batches"
    __table_args__ = (
        Index('ix_flight_batches_upload_time', 'upload_time'),
        Index('ix_flight_batches_status', 'status'),
        {'schema': 'flights'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False, comment="Имя файла")
    file_size = Column(Integer, comment="Размер файла в байтах")
    total_records = Column(Integer, default=0, comment="Общее количество записей")
    processed_records = Column(Integer, default=0, comment="Количество обработанных записей")
    valid_records = Column(Integer, default=0, comment="Количество валидных записей")
    invalid_records = Column(Integer, default=0, comment="Количество невалидных записей")
    
    status = Column(String(20), default='uploading', comment="Статус обработки")  # uploading, processing, completed, failed
    error_message = Column(Text, comment="Сообщение об ошибке")
    
    upload_time = Column(DateTime(timezone=True), default=datetime.utcnow, comment="Время загрузки")
    processing_start_time = Column(DateTime(timezone=True), comment="Время начала обработки")
    processing_end_time = Column(DateTime(timezone=True), comment="Время окончания обработки")
    
    def __repr__(self):
        return f"<FlightBatch(filename='{self.filename}', status='{self.status}', total_records={self.total_records})>"

