"""
Модели данных для аналитики и метрик полетов БПЛА
Включает базовые и расширенные метрики согласно техническому заданию
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.db.database import Base


class FlightMetrics(Base):
    """
    Модель для хранения предрасчитанных метрик по полетам
    Обновляется периодически для быстрого доступа к аналитике
    """
    __tablename__ = "flight_metrics"
    __table_args__ = (
        Index('ix_metrics_region_period', 'region_code', 'period_type', 'period_start'),
        Index('ix_metrics_period', 'period_type', 'period_start'),
        Index('ix_metrics_region', 'region_code'),
        {'schema': 'analytics'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Период и регион
    region_code = Column(String(10), comment="Код субъекта РФ")
    region_name = Column(String(200), comment="Название субъекта РФ")
    period_type = Column(String(20), nullable=False, comment="Тип периода: hour, day, week, month, year")
    period_start = Column(DateTime(timezone=True), nullable=False, comment="Начало периода")
    period_end = Column(DateTime(timezone=True), nullable=False, comment="Конец периода")
    
    # Базовые метрики
    total_flights = Column(Integer, default=0, comment="Общее количество полетов")
    avg_duration_minutes = Column(Float, comment="Средняя продолжительность полета (мин)")
    median_duration_minutes = Column(Float, comment="Медианная продолжительность полета (мин)")
    total_flight_time_hours = Column(Float, comment="Общее время полетов (часы)")
    
    # Расширенные метрики
    peak_hour_flights = Column(Integer, comment="Максимальное число полетов за час")
    peak_hour = Column(Integer, comment="Час пиковой нагрузки (0-23)")
    daily_avg_flights = Column(Float, comment="Среднесуточное число полетов")
    daily_median_flights = Column(Float, comment="Медианное суточное число полетов")
    
    # Рост/падение (в процентах к предыдущему периоду)
    growth_percent = Column(Float, comment="Процентное изменение к предыдущему периоду")
    
    # Flight Density (полеты на 1000 км²)
    flight_density_per_1000km2 = Column(Float, comment="Количество полетов на 1000 км²")
    
    # Распределение по времени суток
    morning_flights = Column(Integer, default=0, comment="Полеты утром (6-12)")
    day_flights = Column(Integer, default=0, comment="Полеты днем (12-18)")
    evening_flights = Column(Integer, default=0, comment="Полеты вечером (18-24)")
    night_flights = Column(Integer, default=0, comment="Полеты ночью (0-6)")
    
    # Дни без полетов
    zero_flight_days = Column(Integer, default=0, comment="Количество дней без полетов")
    
    # Типы БПЛА
    aircraft_types = Column(JSON, comment="Распределение по типам БПЛА")
    
    # Метаданные
    calculated_at = Column(DateTime(timezone=True), default=datetime.utcnow, comment="Время расчета")
    data_source_start = Column(DateTime(timezone=True), comment="Начало периода исходных данных")
    data_source_end = Column(DateTime(timezone=True), comment="Конец периода исходных данных")
    
    def __repr__(self):
        return f"<FlightMetrics(region='{self.region_code}', period='{self.period_type}', flights={self.total_flights})>"


class RegionRanking(Base):
    """
    Модель для хранения рейтингов регионов по активности БПЛА
    """
    __tablename__ = "region_rankings"
    __table_args__ = (
        Index('ix_rankings_period', 'period_type', 'period_start'),
        Index('ix_rankings_rank', 'ranking_position'),
        {'schema': 'analytics'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Период рейтинга
    period_type = Column(String(20), nullable=False, comment="Тип периода: month, quarter, year")
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Регион
    region_code = Column(String(10), nullable=False)
    region_name = Column(String(200), nullable=False)
    
    # Позиция в рейтинге
    ranking_position = Column(Integer, nullable=False, comment="Позиция в рейтинге")
    total_flights = Column(Integer, nullable=False, comment="Общее количество полетов")
    flight_density = Column(Float, comment="Плотность полетов")
    
    # Изменение позиции
    previous_position = Column(Integer, comment="Предыдущая позиция")
    position_change = Column(Integer, comment="Изменение позиции (+/- места)")
    
    # Метаданные
    calculated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    def __repr__(self):
        return f"<RegionRanking(region='{self.region_name}', position={self.ranking_position}, flights={self.total_flights})>"


class ReportGeneration(Base):
    """
    Модель для отслеживания генерации отчетов
    """
    __tablename__ = "report_generations"
    __table_args__ = (
        Index('ix_reports_created', 'created_at'),
        Index('ix_reports_status', 'status'),
        Index('ix_reports_type', 'report_type'),
        {'schema': 'analytics'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Параметры отчета
    report_type = Column(String(50), nullable=False, comment="Тип отчета")
    report_format = Column(String(10), nullable=False, comment="Формат: json, csv, xlsx, png, jpeg")
    parameters = Column(JSON, comment="Параметры генерации отчета")
    
    # Период данных
    data_period_start = Column(DateTime(timezone=True), comment="Начало периода данных")
    data_period_end = Column(DateTime(timezone=True), comment="Конец периода данных")
    
    # Фильтры
    region_filter = Column(String(500), comment="Фильтр по регионам")
    aircraft_type_filter = Column(String(200), comment="Фильтр по типам БПЛА")
    
    # Статус генерации
    status = Column(String(20), default='pending', comment="Статус: pending, generating, completed, failed")
    progress_percent = Column(Integer, default=0, comment="Процент выполнения")
    error_message = Column(Text, comment="Сообщение об ошибке")
    
    # Результат
    file_path = Column(String(500), comment="Путь к сгенерированному файлу")
    file_size = Column(Integer, comment="Размер файла")
    download_url = Column(String(500), comment="URL для скачивания")
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    generation_start = Column(DateTime(timezone=True), comment="Начало генерации")
    generation_end = Column(DateTime(timezone=True), comment="Окончание генерации")
    expires_at = Column(DateTime(timezone=True), comment="Время истечения доступности файла")
    
    def __repr__(self):
        return f"<ReportGeneration(type='{self.report_type}', format='{self.report_format}', status='{self.status}')>"


class SystemMetrics(Base):
    """
    Модель для хранения системных метрик производительности
    """
    __tablename__ = "system_metrics"
    __table_args__ = (
        Index('ix_system_metrics_timestamp', 'timestamp'),
        Index('ix_system_metrics_metric_name', 'metric_name'),
        {'schema': 'analytics'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Метрика
    metric_name = Column(String(100), nullable=False, comment="Название метрики")
    metric_value = Column(Float, nullable=False, comment="Значение метрики")
    metric_unit = Column(String(20), comment="Единица измерения")
    
    # Контекст
    component = Column(String(50), comment="Компонент системы")
    tags = Column(JSON, comment="Дополнительные теги")
    
    # Время
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, comment="Время измерения")
    
    def __repr__(self):
        return f"<SystemMetrics(name='{self.metric_name}', value={self.metric_value}, time='{self.timestamp}')>"

