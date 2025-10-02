"""
Сервис валидации и очистки данных о полетах БПЛА
Проверка форматов даты, времени, координат и удаление дубликатов
"""

from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import logging
import hashlib
from shapely.geometry import Point
from shapely import wkt

from app.parsers.message_parser import ParsedMessage
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Результат валидации данных"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    normalized_data: Optional[Dict] = None


@dataclass
class DeduplicationResult:
    """Результат дедупликации"""
    original_count: int
    unique_count: int
    duplicates_removed: int
    duplicate_groups: List[List[str]]


class FlightDataValidator:
    """
    Валидатор данных о полетах БПЛА
    Выполняет проверку корректности и нормализацию данных
    """
    
    def __init__(self):
        # Границы территории РФ для валидации координат
        self.russia_bounds = {
            'lat_min': 41.0,
            'lat_max': 82.0,
            'lon_min': 19.0,
            'lon_max': 180.0
        }
        
        # Допустимые типы БПЛА (расширяемый список)
        self.valid_aircraft_types = {
            'QUAD', 'HEXA', 'OCTO',  # Мультикоптеры
            'FIXW', 'HELI', 'GYRO',  # Самолеты, вертолеты, автожиры
            'BALL', 'GLID', 'PARA',  # Аэростаты, планеры, парапланы
            'UNKN'  # Неизвестный тип
        }
        
        # Максимальные и минимальные значения для валидации
        self.validation_limits = {
            'max_flight_duration_hours': settings.MAX_FLIGHT_DURATION_HOURS,
            'min_flight_duration_minutes': settings.MIN_FLIGHT_DURATION_MINUTES,
            'max_altitude_meters': 10000,  # 10 км
            'min_altitude_meters': 0,
            'max_speed_kmh': 500,  # 500 км/ч
        }
    
    def validate_flight_data(self, parsed_message: ParsedMessage) -> ValidationResult:
        """
        Основной метод валидации данных полета
        
        Args:
            parsed_message: Распарсенное сообщение о полете
            
        Returns:
            ValidationResult: Результат валидации
        """
        errors = []
        warnings = []
        normalized_data = {}
        
        try:
            # Валидация идентификатора полета
            flight_id_result = self._validate_flight_id(parsed_message.flight_id)
            if not flight_id_result.is_valid:
                errors.extend(flight_id_result.errors)
            else:
                normalized_data['flight_id'] = flight_id_result.normalized_data['flight_id']
            
            # Валидация типа воздушного судна
            aircraft_result = self._validate_aircraft_type(parsed_message.aircraft_type)
            if not aircraft_result.is_valid:
                warnings.extend(aircraft_result.warnings)
            normalized_data['aircraft_type'] = aircraft_result.normalized_data['aircraft_type']
            
            # Валидация времени
            time_result = self._validate_times(
                parsed_message.departure_time,
                parsed_message.arrival_time
            )
            if not time_result.is_valid:
                errors.extend(time_result.errors)
            warnings.extend(time_result.warnings)
            normalized_data.update(time_result.normalized_data)
            
            # Валидация координат
            coord_result = self._validate_coordinates(
                parsed_message.departure_coordinates,
                parsed_message.arrival_coordinates
            )
            if not coord_result.is_valid:
                errors.extend(coord_result.errors)
            warnings.extend(coord_result.warnings)
            normalized_data.update(coord_result.normalized_data)
            
            # Валидация высоты
            if parsed_message.altitude:
                altitude_result = self._validate_altitude(parsed_message.altitude)
                if not altitude_result.is_valid:
                    warnings.extend(altitude_result.warnings)
                normalized_data['altitude'] = altitude_result.normalized_data['altitude']
            
            # Валидация маршрута и расстояния
            if parsed_message.departure_coordinates and parsed_message.arrival_coordinates:
                distance_result = self._validate_flight_distance(
                    parsed_message.departure_coordinates,
                    parsed_message.arrival_coordinates,
                    parsed_message.departure_time,
                    parsed_message.arrival_time
                )
                if not distance_result.is_valid:
                    warnings.extend(distance_result.warnings)
                normalized_data.update(distance_result.normalized_data)
            
        except Exception as e:
            logger.error(f"Ошибка валидации данных полета: {e}")
            errors.append(f"Критическая ошибка валидации: {str(e)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            normalized_data=normalized_data
        )
    
    def _validate_flight_id(self, flight_id: str) -> ValidationResult:
        """Валидация идентификатора полета"""
        errors = []
        warnings = []
        
        if not flight_id:
            errors.append("Отсутствует идентификатор полета")
            return ValidationResult(False, errors, warnings)
        
        # Нормализация: удаление лишних символов и приведение к верхнему регистру
        normalized_id = flight_id.strip().upper()
        
        # Проверка длины (обычно 3-7 символов)
        if len(normalized_id) < 3 or len(normalized_id) > 7:
            warnings.append(f"Нестандартная длина идентификатора полета: {len(normalized_id)}")
        
        # Проверка на допустимые символы (буквы и цифры)
        if not normalized_id.replace('-', '').isalnum():
            warnings.append("Идентификатор полета содержит недопустимые символы")
        
        return ValidationResult(
            True, errors, warnings,
            {'flight_id': normalized_id}
        )
    
    def _validate_aircraft_type(self, aircraft_type: Optional[str]) -> ValidationResult:
        """Валидация типа воздушного судна"""
        warnings = []
        
        if not aircraft_type:
            normalized_type = 'UNKN'
            warnings.append("Тип воздушного судна не указан, установлен как UNKN")
        else:
            normalized_type = aircraft_type.strip().upper()
            
            # Проверка на известные типы
            if normalized_type not in self.valid_aircraft_types:
                warnings.append(f"Неизвестный тип БПЛА: {normalized_type}")
                # Попытка определить тип по названию
                if 'QUAD' in normalized_type or 'MULTI' in normalized_type:
                    normalized_type = 'QUAD'
                elif 'HELI' in normalized_type:
                    normalized_type = 'HELI'
                elif 'FIXED' in normalized_type or 'WING' in normalized_type:
                    normalized_type = 'FIXW'
                else:
                    normalized_type = 'UNKN'
                warnings.append(f"Тип автоматически определен как: {normalized_type}")
        
        return ValidationResult(
            True, [], warnings,
            {'aircraft_type': normalized_type}
        )
    
    def _validate_times(self, departure_time: Optional[datetime], 
                       arrival_time: Optional[datetime]) -> ValidationResult:
        """Валидация времени вылета и прилета"""
        errors = []
        warnings = []
        normalized_data = {}
        
        # Проверка времени вылета
        if not departure_time:
            errors.append("Отсутствует время вылета")
            return ValidationResult(False, errors, warnings, normalized_data)
        
        # Проверка на разумность времени (не в далеком прошлом или будущем)
        now = datetime.now()
        if departure_time < now - timedelta(days=365):
            warnings.append("Время вылета более года назад")
        elif departure_time > now + timedelta(days=30):
            warnings.append("Время вылета более чем на месяц вперед")
        
        normalized_data['departure_time'] = departure_time
        
        # Валидация времени прилета
        if arrival_time:
            # Проверка логической последовательности
            if arrival_time <= departure_time:
                errors.append("Время прилета должно быть позже времени вылета")
            
            # Проверка продолжительности полета
            duration = arrival_time - departure_time
            duration_hours = duration.total_seconds() / 3600
            
            if duration_hours > self.validation_limits['max_flight_duration_hours']:
                warnings.append(f"Очень длительный полет: {duration_hours:.1f} часов")
            elif duration.total_seconds() / 60 < self.validation_limits['min_flight_duration_minutes']:
                warnings.append(f"Очень короткий полет: {duration.total_seconds()/60:.1f} минут")
            
            normalized_data['arrival_time'] = arrival_time
            normalized_data['duration_minutes'] = int(duration.total_seconds() / 60)
        
        return ValidationResult(
            len(errors) == 0, errors, warnings, normalized_data
        )
    
    def _validate_coordinates(self, departure_coords: Optional[Tuple[float, float]],
                            arrival_coords: Optional[Tuple[float, float]]) -> ValidationResult:
        """Валидация координат"""
        errors = []
        warnings = []
        normalized_data = {}
        
        # Проверка координат вылета
        if not departure_coords:
            errors.append("Отсутствуют координаты места вылета")
            return ValidationResult(False, errors, warnings, normalized_data)
        
        dep_lon, dep_lat = departure_coords
        
        # Проверка на валидность координат
        if not (-180 <= dep_lon <= 180):
            errors.append(f"Недопустимая долгота места вылета: {dep_lon}")
        if not (-90 <= dep_lat <= 90):
            errors.append(f"Недопустимая широта места вылета: {dep_lat}")
        
        # Проверка на территории РФ
        if not (self.russia_bounds['lon_min'] <= dep_lon <= self.russia_bounds['lon_max'] and
                self.russia_bounds['lat_min'] <= dep_lat <= self.russia_bounds['lat_max']):
            warnings.append("Координаты вылета могут быть вне территории РФ")
        
        normalized_data['departure_coordinates'] = (dep_lon, dep_lat)
        
        # Проверка координат прилета
        if arrival_coords:
            arr_lon, arr_lat = arrival_coords
            
            if not (-180 <= arr_lon <= 180):
                errors.append(f"Недопустимая долгота места прилета: {arr_lon}")
            if not (-90 <= arr_lat <= 90):
                errors.append(f"Недопустимая широта места прилета: {arr_lat}")
            
            if not (self.russia_bounds['lon_min'] <= arr_lon <= self.russia_bounds['lon_max'] and
                    self.russia_bounds['lat_min'] <= arr_lat <= self.russia_bounds['lat_max']):
                warnings.append("Координаты прилета могут быть вне территории РФ")
            
            normalized_data['arrival_coordinates'] = (arr_lon, arr_lat)
        
        return ValidationResult(
            len(errors) == 0, errors, warnings, normalized_data
        )
    
    def _validate_altitude(self, altitude: int) -> ValidationResult:
        """Валидация высоты полета"""
        warnings = []
        
        if altitude < self.validation_limits['min_altitude_meters']:
            warnings.append(f"Отрицательная высота: {altitude} м")
        elif altitude > self.validation_limits['max_altitude_meters']:
            warnings.append(f"Очень большая высота: {altitude} м")
        
        return ValidationResult(
            True, [], warnings,
            {'altitude': altitude}
        )
    
    def _validate_flight_distance(self, departure_coords: Tuple[float, float],
                                arrival_coords: Tuple[float, float],
                                departure_time: Optional[datetime],
                                arrival_time: Optional[datetime]) -> ValidationResult:
        """Валидация расстояния и скорости полета"""
        warnings = []
        normalized_data = {}
        
        try:
            # Расчет расстояния между точками
            dep_point = Point(departure_coords)
            arr_point = Point(arrival_coords)
            
            # Приблизительный расчет расстояния в км (для WGS84)
            distance_degrees = dep_point.distance(arr_point)
            distance_km = distance_degrees * 111  # Приблизительно 111 км на градус
            
            normalized_data['distance_km'] = round(distance_km, 2)
            
            # Проверка скорости, если есть время
            if departure_time and arrival_time and distance_km > 0:
                duration_hours = (arrival_time - departure_time).total_seconds() / 3600
                if duration_hours > 0:
                    speed_kmh = distance_km / duration_hours
                    
                    if speed_kmh > self.validation_limits['max_speed_kmh']:
                        warnings.append(f"Очень высокая скорость: {speed_kmh:.1f} км/ч")
                    
                    normalized_data['average_speed_kmh'] = round(speed_kmh, 2)
            
        except Exception as e:
            warnings.append(f"Ошибка расчета расстояния: {str(e)}")
        
        return ValidationResult(
            True, [], warnings, normalized_data
        )


class FlightDataDeduplicator:
    """
    Дедупликатор данных о полетах
    Удаляет дубликаты по уникальному сочетанию полей
    """
    
    def __init__(self):
        self.deduplication_fields = [
            'flight_id', 'departure_time', 'departure_coordinates'
        ]
    
    def deduplicate_flights(self, parsed_messages: List[ParsedMessage]) -> DeduplicationResult:
        """
        Удаление дубликатов из списка сообщений
        
        Args:
            parsed_messages: Список распарсенных сообщений
            
        Returns:
            DeduplicationResult: Результат дедупликации
        """
        original_count = len(parsed_messages)
        seen_hashes = set()
        unique_messages = []
        duplicate_groups = []
        
        # Группировка по хешам
        hash_to_messages = {}
        
        for message in parsed_messages:
            message_hash = self._calculate_message_hash(message)
            
            if message_hash in hash_to_messages:
                hash_to_messages[message_hash].append(message)
            else:
                hash_to_messages[message_hash] = [message]
        
        # Выделение уникальных сообщений и групп дубликатов
        for message_hash, messages in hash_to_messages.items():
            if len(messages) == 1:
                unique_messages.extend(messages)
            else:
                # Берем первое сообщение как основное
                unique_messages.append(messages[0])
                # Остальные считаем дубликатами
                duplicate_group = [msg.flight_id for msg in messages[1:]]
                duplicate_groups.append(duplicate_group)
        
        unique_count = len(unique_messages)
        duplicates_removed = original_count - unique_count
        
        logger.info(f"Дедупликация завершена: {original_count} -> {unique_count} сообщений, удалено {duplicates_removed} дубликатов")
        
        return DeduplicationResult(
            original_count=original_count,
            unique_count=unique_count,
            duplicates_removed=duplicates_removed,
            duplicate_groups=duplicate_groups
        )
    
    def _calculate_message_hash(self, message: ParsedMessage) -> str:
        """
        Расчет хеша сообщения для определения дубликатов
        
        Args:
            message: Сообщение для хеширования
            
        Returns:
            str: MD5 хеш ключевых полей
        """
        # Формирование строки из ключевых полей
        hash_parts = []
        
        # Идентификатор полета
        hash_parts.append(message.flight_id or "")
        
        # Время вылета
        if message.departure_time:
            hash_parts.append(message.departure_time.isoformat())
        else:
            hash_parts.append("")
        
        # Координаты вылета
        if message.departure_coordinates:
            lon, lat = message.departure_coordinates
            # Округляем до 6 знаков после запятой для устранения погрешностей
            hash_parts.append(f"{lat:.6f},{lon:.6f}")
        else:
            hash_parts.append("")
        
        # Тип воздушного судна
        hash_parts.append(message.aircraft_type or "")
        
        # Создание хеша
        hash_string = "|".join(hash_parts)
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()


def validate_and_clean_flight_data(parsed_messages: List[ParsedMessage]) -> Tuple[List[ParsedMessage], Dict]:
    """
    Комплексная валидация и очистка данных о полетах
    
    Args:
        parsed_messages: Список распарсенных сообщений
        
    Returns:
        Tuple[List[ParsedMessage], Dict]: Очищенные данные и статистика обработки
    """
    validator = FlightDataValidator()
    deduplicator = FlightDataDeduplicator()
    
    # Статистика обработки
    processing_stats = {
        'original_count': len(parsed_messages),
        'valid_count': 0,
        'invalid_count': 0,
        'warning_count': 0,
        'duplicates_removed': 0,
        'validation_errors': [],
        'processing_warnings': []
    }
    
    # Валидация каждого сообщения
    validated_messages = []
    for message in parsed_messages:
        validation_result = validator.validate_flight_data(message)
        
        if validation_result.is_valid:
            processing_stats['valid_count'] += 1
            # Применение нормализованных данных
            if validation_result.normalized_data:
                # Обновление полей сообщения нормализованными данными
                for field, value in validation_result.normalized_data.items():
                    setattr(message, field, value)
            validated_messages.append(message)
        else:
            processing_stats['invalid_count'] += 1
            processing_stats['validation_errors'].extend(validation_result.errors)
        
        if validation_result.warnings:
            processing_stats['warning_count'] += 1
            processing_stats['processing_warnings'].extend(validation_result.warnings)
    
    # Дедупликация
    dedup_result = deduplicator.deduplicate_flights(validated_messages)
    processing_stats['duplicates_removed'] = dedup_result.duplicates_removed
    
    logger.info(f"Обработка данных завершена: {processing_stats}")
    
    return validated_messages, processing_stats

