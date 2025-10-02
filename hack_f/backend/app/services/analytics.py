"""
Сервис аналитики и расчета метрик полетов БПЛА
Реализует базовые и расширенные метрики согласно техническому заданию
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
import logging
from dataclasses import dataclass

from app.db.database import async_session_maker
from app.models.flight import Flight
from app.models.analytics import FlightMetrics, RegionRanking, SystemMetrics
from app.models.region import RussianRegion

logger = logging.getLogger(__name__)


@dataclass
class BaseMetrics:
    """Базовые метрики полетов"""
    total_flights: int
    avg_duration_minutes: float
    median_duration_minutes: float
    total_flight_time_hours: float


@dataclass
class ExtendedMetrics:
    """Расширенные метрики полетов"""
    peak_hour_flights: int
    peak_hour: int
    daily_avg_flights: float
    daily_median_flights: float
    growth_percent: float
    flight_density_per_1000km2: float
    morning_flights: int
    day_flights: int
    evening_flights: int
    night_flights: int
    zero_flight_days: int


class AnalyticsService:
    """
    Сервис аналитики полетов БПЛА
    Предоставляет методы для расчета различных метрик и показателей
    """
    
    def __init__(self):
        self.time_periods = {
            'hour': timedelta(hours=1),
            'day': timedelta(days=1),
            'week': timedelta(weeks=1),
            'month': timedelta(days=30),
            'quarter': timedelta(days=90),
            'year': timedelta(days=365)
        }
    
    async def calculate_base_metrics(
        self,
        region_code: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> BaseMetrics:
        """
        Расчет базовых метрик полетов
        
        Args:
            region_code: Код региона для фильтрации
            date_from: Начало периода
            date_to: Конец периода
            
        Returns:
            BaseMetrics: Базовые метрики
        """
        async with async_session_maker() as db:
            try:
                # Базовый запрос
                query = select(Flight).where(Flight.is_valid == True)
                
                # Применение фильтров
                if region_code:
                    query = query.where(
                        or_(
                            Flight.region_departure_code == region_code,
                            Flight.region_arrival_code == region_code
                        )
                    )
                
                if date_from:
                    query = query.where(Flight.departure_time >= date_from)
                
                if date_to:
                    query = query.where(Flight.departure_time <= date_to)
                
                # Общее количество полетов
                count_query = select(func.count()).select_from(query.subquery())
                total_result = await db.execute(count_query)
                total_flights = total_result.scalar() or 0
                
                if total_flights == 0:
                    return BaseMetrics(0, 0.0, 0.0, 0.0)
                
                # Средняя продолжительность
                avg_query = select(func.avg(Flight.duration_minutes)).select_from(
                    query.where(Flight.duration_minutes.is_not(None)).subquery()
                )
                avg_result = await db.execute(avg_query)
                avg_duration = avg_result.scalar() or 0.0
                
                # Медианная продолжительность (приблизительная)
                median_query = select(func.percentile_cont(0.5).within_group(Flight.duration_minutes)).select_from(
                    query.where(Flight.duration_minutes.is_not(None)).subquery()
                )
                median_result = await db.execute(median_query)
                median_duration = median_result.scalar() or 0.0
                
                # Общее время полетов
                total_time_query = select(func.sum(Flight.duration_minutes)).select_from(
                    query.where(Flight.duration_minutes.is_not(None)).subquery()
                )
                total_time_result = await db.execute(total_time_query)
                total_time_minutes = total_time_result.scalar() or 0
                total_time_hours = total_time_minutes / 60.0
                
                return BaseMetrics(
                    total_flights=total_flights,
                    avg_duration_minutes=round(avg_duration, 2),
                    median_duration_minutes=round(median_duration, 2),
                    total_flight_time_hours=round(total_time_hours, 2)
                )
                
            except Exception as e:
                logger.error(f"Ошибка расчета базовых метрик: {e}")
                return BaseMetrics(0, 0.0, 0.0, 0.0)
    
    async def calculate_extended_metrics(
        self,
        region_code: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> ExtendedMetrics:
        """
        Расчет расширенных метрик полетов
        
        Args:
            region_code: Код региона
            date_from: Начало периода
            date_to: Конец периода
            
        Returns:
            ExtendedMetrics: Расширенные метрики
        """
        async with async_session_maker() as db:
            try:
                # Базовый запрос
                query = select(Flight).where(Flight.is_valid == True)
                
                # Применение фильтров
                if region_code:
                    query = query.where(
                        or_(
                            Flight.region_departure_code == region_code,
                            Flight.region_arrival_code == region_code
                        )
                    )
                
                if date_from:
                    query = query.where(Flight.departure_time >= date_from)
                
                if date_to:
                    query = query.where(Flight.departure_time <= date_to)
                
                # Пиковая нагрузка по часам
                hourly_query = select(
                    func.extract('hour', Flight.departure_time).label('hour'),
                    func.count(Flight.id).label('flights_count')
                ).select_from(query.subquery()).group_by('hour').order_by(desc('flights_count'))
                
                hourly_result = await db.execute(hourly_query)
                hourly_stats = hourly_result.all()
                
                peak_hour_flights = hourly_stats[0].flights_count if hourly_stats else 0
                peak_hour = int(hourly_stats[0].hour) if hourly_stats else 0
                
                # Среднесуточная динамика
                daily_query = select(
                    func.date(Flight.departure_time).label('flight_date'),
                    func.count(Flight.id).label('daily_flights')
                ).select_from(query.subquery()).group_by('flight_date')
                
                daily_result = await db.execute(daily_query)
                daily_stats = daily_result.all()
                
                daily_flights = [row.daily_flights for row in daily_stats]
                daily_avg = sum(daily_flights) / len(daily_flights) if daily_flights else 0.0
                daily_median = sorted(daily_flights)[len(daily_flights) // 2] if daily_flights else 0.0
                
                # Распределение по времени суток
                time_distribution = await self._calculate_time_distribution(query, db)
                
                # Дни без полетов
                if date_from and date_to:
                    total_days = (date_to - date_from).days + 1
                    flight_days = len(daily_stats)
                    zero_flight_days = max(0, total_days - flight_days)
                else:
                    zero_flight_days = 0
                
                # Рост/падение (заглушка - требует сравнения с предыдущим периодом)
                growth_percent = 0.0
                
                # Flight Density (заглушка - требует данных о площади региона)
                flight_density = 0.0
                
                return ExtendedMetrics(
                    peak_hour_flights=peak_hour_flights,
                    peak_hour=peak_hour,
                    daily_avg_flights=round(daily_avg, 2),
                    daily_median_flights=round(daily_median, 2),
                    growth_percent=growth_percent,
                    flight_density_per_1000km2=flight_density,
                    morning_flights=time_distribution['morning'],
                    day_flights=time_distribution['day'],
                    evening_flights=time_distribution['evening'],
                    night_flights=time_distribution['night'],
                    zero_flight_days=zero_flight_days
                )
                
            except Exception as e:
                logger.error(f"Ошибка расчета расширенных метрик: {e}")
                return ExtendedMetrics(0, 0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, 0)
    
    async def _calculate_time_distribution(self, base_query, db: AsyncSession) -> Dict[str, int]:
        """Расчет распределения полетов по времени суток"""
        try:
            # Утро (6-12)
            morning_query = select(func.count()).select_from(
                base_query.where(
                    and_(
                        func.extract('hour', Flight.departure_time) >= 6,
                        func.extract('hour', Flight.departure_time) < 12
                    )
                ).subquery()
            )
            morning_result = await db.execute(morning_query)
            morning_flights = morning_result.scalar() or 0
            
            # День (12-18)
            day_query = select(func.count()).select_from(
                base_query.where(
                    and_(
                        func.extract('hour', Flight.departure_time) >= 12,
                        func.extract('hour', Flight.departure_time) < 18
                    )
                ).subquery()
            )
            day_result = await db.execute(day_query)
            day_flights = day_result.scalar() or 0
            
            # Вечер (18-24)
            evening_query = select(func.count()).select_from(
                base_query.where(
                    and_(
                        func.extract('hour', Flight.departure_time) >= 18,
                        func.extract('hour', Flight.departure_time) < 24
                    )
                ).subquery()
            )
            evening_result = await db.execute(evening_query)
            evening_flights = evening_result.scalar() or 0
            
            # Ночь (0-6)
            night_query = select(func.count()).select_from(
                base_query.where(
                    and_(
                        func.extract('hour', Flight.departure_time) >= 0,
                        func.extract('hour', Flight.departure_time) < 6
                    )
                ).subquery()
            )
            night_result = await db.execute(night_query)
            night_flights = night_result.scalar() or 0
            
            return {
                'morning': morning_flights,
                'day': day_flights,
                'evening': evening_flights,
                'night': night_flights
            }
            
        except Exception as e:
            logger.error(f"Ошибка расчета распределения по времени суток: {e}")
            return {'morning': 0, 'day': 0, 'evening': 0, 'night': 0}
    
    async def calculate_regional_ranking(
        self,
        period_type: str = 'month',
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Расчет рейтинга регионов по активности полетов
        
        Args:
            period_type: Тип периода (month, quarter, year)
            date_from: Начало периода
            date_to: Конец периода
            limit: Количество регионов в рейтинге
            
        Returns:
            List[Dict]: Рейтинг регионов
        """
        async with async_session_maker() as db:
            try:
                # Запрос для подсчета полетов по регионам отправления
                departure_query = select(
                    Flight.region_departure_code.label('region_code'),
                    Flight.region_departure.label('region_name'),
                    func.count(Flight.id).label('flights_count')
                ).where(
                    and_(
                        Flight.is_valid == True,
                        Flight.region_departure_code.is_not(None)
                    )
                )
                
                # Применение фильтров по дате
                if date_from:
                    departure_query = departure_query.where(Flight.departure_time >= date_from)
                if date_to:
                    departure_query = departure_query.where(Flight.departure_time <= date_to)
                
                departure_query = departure_query.group_by(
                    Flight.region_departure_code,
                    Flight.region_departure
                ).order_by(desc('flights_count')).limit(limit)
                
                result = await db.execute(departure_query)
                rankings = result.all()
                
                # Формирование результата
                ranking_list = []
                for i, row in enumerate(rankings, 1):
                    ranking_list.append({
                        'position': i,
                        'region_code': row.region_code,
                        'region_name': row.region_name,
                        'flights_count': row.flights_count,
                        'change': 0  # Заглушка для изменения позиции
                    })
                
                return ranking_list
                
            except Exception as e:
                logger.error(f"Ошибка расчета рейтинга регионов: {e}")
                return []
    
    async def get_aircraft_type_statistics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Статистика по типам БПЛА
        
        Args:
            date_from: Начало периода
            date_to: Конец периода
            
        Returns:
            Dict[str, int]: Статистика по типам
        """
        async with async_session_maker() as db:
            try:
                query = select(
                    Flight.aircraft_type,
                    func.count(Flight.id).label('count')
                ).where(Flight.is_valid == True)
                
                if date_from:
                    query = query.where(Flight.departure_time >= date_from)
                if date_to:
                    query = query.where(Flight.departure_time <= date_to)
                
                query = query.group_by(Flight.aircraft_type).order_by(desc('count'))
                
                result = await db.execute(query)
                stats = result.all()
                
                return {row.aircraft_type or 'UNKNOWN': row.count for row in stats}
                
            except Exception as e:
                logger.error(f"Ошибка получения статистики по типам БПЛА: {e}")
                return {}
    
    async def save_calculated_metrics(
        self,
        region_code: Optional[str],
        period_type: str,
        period_start: datetime,
        period_end: datetime,
        base_metrics: BaseMetrics,
        extended_metrics: ExtendedMetrics
    ):
        """
        Сохранение рассчитанных метрик в базу данных
        
        Args:
            region_code: Код региона
            period_type: Тип периода
            period_start: Начало периода
            period_end: Конец периода
            base_metrics: Базовые метрики
            extended_metrics: Расширенные метрики
        """
        async with async_session_maker() as db:
            try:
                # Получение названия региона
                region_name = None
                if region_code:
                    region_query = select(RussianRegion.name).where(
                        RussianRegion.region_code == region_code
                    )
                    region_result = await db.execute(region_query)
                    region_name = region_result.scalar()
                
                # Создание записи метрик
                metrics = FlightMetrics(
                    region_code=region_code,
                    region_name=region_name,
                    period_type=period_type,
                    period_start=period_start,
                    period_end=period_end,
                    total_flights=base_metrics.total_flights,
                    avg_duration_minutes=base_metrics.avg_duration_minutes,
                    median_duration_minutes=base_metrics.median_duration_minutes,
                    total_flight_time_hours=base_metrics.total_flight_time_hours,
                    peak_hour_flights=extended_metrics.peak_hour_flights,
                    peak_hour=extended_metrics.peak_hour,
                    daily_avg_flights=extended_metrics.daily_avg_flights,
                    daily_median_flights=extended_metrics.daily_median_flights,
                    growth_percent=extended_metrics.growth_percent,
                    flight_density_per_1000km2=extended_metrics.flight_density_per_1000km2,
                    morning_flights=extended_metrics.morning_flights,
                    day_flights=extended_metrics.day_flights,
                    evening_flights=extended_metrics.evening_flights,
                    night_flights=extended_metrics.night_flights,
                    zero_flight_days=extended_metrics.zero_flight_days
                )
                
                db.add(metrics)
                await db.commit()
                
                logger.info(f"Метрики сохранены для региона {region_code}, период {period_type}")
                
            except Exception as e:
                logger.error(f"Ошибка сохранения метрик: {e}")
                await db.rollback()


# Глобальный экземпляр сервиса
analytics_service = AnalyticsService()

