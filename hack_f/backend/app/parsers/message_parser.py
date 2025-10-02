"""
Парсер стандартных сообщений о движении воздушных судов
В соответствии с «Табелем сообщений о движении воздушных судов в Российской Федерации»,
утвержденным приказом Минтранса России от 24 января 2013 года №13
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Типы сообщений согласно Табелю"""
    FPL = "FPL"  # План полета
    DEP = "DEP"  # Вылет
    ARR = "ARR"  # Прилет
    CHG = "CHG"  # Изменение плана полета
    CNL = "CNL"  # Отмена плана полета
    DLA = "DLA"  # Задержка
    RQS = "RQS"  # Запрос статуса
    RQP = "RQP"  # Запрос плана полета


@dataclass
class ParsedMessage:
    """Структура распарсенного сообщения"""
    message_type: MessageType
    flight_id: str
    aircraft_type: Optional[str] = None
    aircraft_registration: Optional[str] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    departure_coordinates: Optional[Tuple[float, float]] = None
    arrival_coordinates: Optional[Tuple[float, float]] = None
    departure_aerodrome: Optional[str] = None
    arrival_aerodrome: Optional[str] = None
    altitude: Optional[int] = None
    route: Optional[str] = None
    operator_info: Optional[str] = None
    raw_message: str = ""
    parsing_errors: List[str] = None
    
    def __post_init__(self):
        if self.parsing_errors is None:
            self.parsing_errors = []


class FlightMessageParser:
    """
    Парсер сообщений о полетах БПЛА
    Поддерживает основные типы сообщений согласно Табелю
    """
    
    def __init__(self):
        # Регулярные выражения для парсинга различных элементов сообщений
        self.patterns = {
            # Основные элементы сообщения
            'message_type': r'^(FPL|DEP|ARR|CHG|CNL|DLA|RQS|RQP)',
            'flight_id': r'-([A-Z0-9]{1,7})',
            'aircraft_type': r'-([A-Z0-9]{2,4})',
            'aircraft_registration': r'-([A-Z]{1,2}[A-Z0-9]{1,5})',
            
            # Время в формате HHMM или HHMMSS
            'time': r'(\d{4}|\d{6})',
            'date_time': r'(\d{6}\d{4})',  # DDHHMMSS
            
            # Координаты в различных форматах
            'coordinates_dms': r'(\d{2,3})(\d{2})([NS])(\d{3})(\d{2})([EW])',  # DDMM[N|S]DDDMM[E|W]
            'coordinates_decimal': r'([+-]?\d{1,3}\.\d{1,6})\s*([+-]?\d{1,3}\.\d{1,6})',
            
            # Аэродромы (4-буквенные коды ICAO)
            'aerodrome': r'([A-Z]{4})',
            
            # Высота
            'altitude': r'F(\d{3})|A(\d{3})|FL(\d{3})',
            
            # Маршрут
            'route': r'-N([A-Z0-9\s/]+)',
            
            # Дополнительная информация
            'remarks': r'-RMK/(.+?)(?=-|$)',
            'operator': r'-OPR/(.+?)(?=-|$)',
        }
        
        # Компиляция регулярных выражений
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.patterns.items()
        }
    
    def parse_message(self, message: str) -> ParsedMessage:
        """
        Основной метод парсинга сообщения
        
        Args:
            message: Строка сообщения для парсинга
            
        Returns:
            ParsedMessage: Структура с распарсенными данными
        """
        logger.debug(f"Парсинг сообщения: {message[:100]}...")
        
        parsed = ParsedMessage(
            message_type=MessageType.FPL,  # По умолчанию
            flight_id="",
            raw_message=message.strip()
        )
        
        try:
            # Нормализация сообщения
            normalized_message = self._normalize_message(message)
            
            # Определение типа сообщения
            parsed.message_type = self._parse_message_type(normalized_message)
            
            # Парсинг основных элементов
            parsed.flight_id = self._parse_flight_id(normalized_message)
            parsed.aircraft_type = self._parse_aircraft_type(normalized_message)
            parsed.aircraft_registration = self._parse_aircraft_registration(normalized_message)
            
            # Парсинг времени
            parsed.departure_time, parsed.arrival_time = self._parse_times(normalized_message)
            
            # Парсинг координат
            parsed.departure_coordinates = self._parse_departure_coordinates(normalized_message)
            parsed.arrival_coordinates = self._parse_arrival_coordinates(normalized_message)
            
            # Парсинг аэродромов
            parsed.departure_aerodrome, parsed.arrival_aerodrome = self._parse_aerodromes(normalized_message)
            
            # Парсинг высоты
            parsed.altitude = self._parse_altitude(normalized_message)
            
            # Парсинг маршрута
            parsed.route = self._parse_route(normalized_message)
            
            # Парсинг информации об операторе
            parsed.operator_info = self._parse_operator_info(normalized_message)
            
            # Валидация обязательных полей
            self._validate_parsed_data(parsed)
            
        except Exception as e:
            error_msg = f"Ошибка парсинга сообщения: {str(e)}"
            logger.error(error_msg)
            parsed.parsing_errors.append(error_msg)
        
        return parsed
    
    def _normalize_message(self, message: str) -> str:
        """Нормализация сообщения для парсинга"""
        # Удаление лишних пробелов и символов
        normalized = re.sub(r'\s+', ' ', message.strip())
        # Приведение к верхнему регистру
        normalized = normalized.upper()
        return normalized
    
    def _parse_message_type(self, message: str) -> MessageType:
        """Определение типа сообщения"""
        match = self.compiled_patterns['message_type'].search(message)
        if match:
            try:
                return MessageType(match.group(1))
            except ValueError:
                return MessageType.FPL
        return MessageType.FPL
    
    def _parse_flight_id(self, message: str) -> str:
        """Парсинг идентификатора полета"""
        match = self.compiled_patterns['flight_id'].search(message)
        return match.group(1) if match else ""
    
    def _parse_aircraft_type(self, message: str) -> Optional[str]:
        """Парсинг типа воздушного судна"""
        # Ищем тип ВС после идентификатора полета
        match = self.compiled_patterns['aircraft_type'].search(message)
        return match.group(1) if match else None
    
    def _parse_aircraft_registration(self, message: str) -> Optional[str]:
        """Парсинг регистрационного номера"""
        match = self.compiled_patterns['aircraft_registration'].search(message)
        return match.group(1) if match else None
    
    def _parse_times(self, message: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Парсинг времени вылета и прилета
        Поддерживает различные форматы времени
        """
        departure_time = None
        arrival_time = None
        
        # Поиск времени в формате DDHHMMSS (дата + время)
        date_time_matches = self.compiled_patterns['date_time'].findall(message)
        if date_time_matches:
            try:
                # Первое время - вылет, второе - прилет (если есть)
                departure_time = self._parse_datetime_string(date_time_matches[0])
                if len(date_time_matches) > 1:
                    arrival_time = self._parse_datetime_string(date_time_matches[1])
            except ValueError as e:
                logger.warning(f"Ошибка парсинга времени: {e}")
        
        # Поиск времени в формате HHMM
        time_matches = self.compiled_patterns['time'].findall(message)
        if time_matches and not departure_time:
            try:
                departure_time = self._parse_time_string(time_matches[0])
                if len(time_matches) > 1:
                    arrival_time = self._parse_time_string(time_matches[1])
            except ValueError as e:
                logger.warning(f"Ошибка парсинга времени: {e}")
        
        return departure_time, arrival_time
    
    def _parse_datetime_string(self, datetime_str: str) -> datetime:
        """Парсинг строки даты-времени в формате DDHHMMSS"""
        if len(datetime_str) == 10:  # DDHHMMSS
            day = int(datetime_str[:2])
            hour = int(datetime_str[2:4])
            minute = int(datetime_str[4:6])
            second = int(datetime_str[6:8])
            
            # Используем текущий месяц и год, но проверяем корректность дня
            now = datetime.now()
            try:
                return datetime(now.year, now.month, day, hour, minute, second)
            except ValueError:
                # Если день не существует в текущем месяце, используем предыдущий месяц
                if now.month == 1:
                    return datetime(now.year - 1, 12, day, hour, minute, second)
                else:
                    return datetime(now.year, now.month - 1, day, hour, minute, second)
        
        raise ValueError(f"Неподдерживаемый формат даты-времени: {datetime_str}")
    
    def _parse_time_string(self, time_str: str) -> datetime:
        """Парсинг строки времени в формате HHMM или HHMMSS"""
        now = datetime.now()
        
        if len(time_str) == 4:  # HHMM
            hour = int(time_str[:2])
            minute = int(time_str[2:4])
            # Проверяем, не в будущем ли время
            parsed_time = datetime(now.year, now.month, now.day, hour, minute)
            if parsed_time > now:
                # Если время в будущем, используем предыдущий день
                parsed_time = parsed_time - timedelta(days=1)
            return parsed_time
        elif len(time_str) == 6:  # HHMMSS
            hour = int(time_str[:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])
            # Проверяем, не в будущем ли время
            parsed_time = datetime(now.year, now.month, now.day, hour, minute, second)
            if parsed_time > now:
                # Если время в будущем, используем предыдущий день
                parsed_time = parsed_time - timedelta(days=1)
            return parsed_time
        
        raise ValueError(f"Неподдерживаемый формат времени: {time_str}")
    
    def _parse_departure_coordinates(self, message: str) -> Optional[Tuple[float, float]]:
        """Парсинг координат вылета"""
        return self._parse_coordinates(message, 0)  # Первые координаты
    
    def _parse_arrival_coordinates(self, message: str) -> Optional[Tuple[float, float]]:
        """Парсинг координат прилета"""
        return self._parse_coordinates(message, 1)  # Вторые координаты
    
    def _parse_coordinates(self, message: str, index: int = 0) -> Optional[Tuple[float, float]]:
        """
        Парсинг координат в различных форматах
        
        Args:
            message: Сообщение для парсинга
            index: Индекс координат (0 - первые, 1 - вторые)
        """
        # Сначала ищем десятичные координаты
        decimal_matches = self.compiled_patterns['coordinates_decimal'].findall(message)
        if decimal_matches and len(decimal_matches) > index:
            try:
                lat, lon = decimal_matches[index]
                # Проверяем, что координаты в правильном порядке (широта, долгота)
                # Широта должна быть в диапазоне -90 до 90, долгота -180 до 180
                lat_val, lon_val = float(lat), float(lon)
                if -90 <= lat_val <= 90 and -180 <= lon_val <= 180:
                    return (lon_val, lat_val)  # Возвращаем в формате (longitude, latitude)
                else:
                    # Если порядок перепутан, меняем местами
                    return (lat_val, lon_val)
            except (ValueError, IndexError):
                pass
        
        # Затем ищем координаты в формате градусы-минуты
        dms_matches = self.compiled_patterns['coordinates_dms'].findall(message)
        if dms_matches and len(dms_matches) > index:
            try:
                lat_deg, lat_min, lat_dir, lon_deg, lon_min, lon_dir = dms_matches[index]
                
                # Конвертация в десятичные градусы
                latitude = int(lat_deg) + int(lat_min) / 60.0
                longitude = int(lon_deg) + int(lon_min) / 60.0
                
                # Учет направления
                if lat_dir == 'S':
                    latitude = -latitude
                if lon_dir == 'W':
                    longitude = -longitude
                
                return (longitude, latitude)
            except (ValueError, IndexError):
                pass
        
        return None
    
    def _parse_aerodromes(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """Парсинг кодов аэродромов вылета и прилета"""
        aerodrome_matches = self.compiled_patterns['aerodrome'].findall(message)
        
        departure_aerodrome = aerodrome_matches[0] if len(aerodrome_matches) > 0 else None
        arrival_aerodrome = aerodrome_matches[1] if len(aerodrome_matches) > 1 else None
        
        return departure_aerodrome, arrival_aerodrome
    
    def _parse_altitude(self, message: str) -> Optional[int]:
        """Парсинг высоты полета"""
        match = self.compiled_patterns['altitude'].search(message)
        if match:
            # Извлекаем числовое значение высоты
            for group in match.groups():
                if group:
                    return int(group) * 100  # Конвертация в футы
        return None
    
    def _parse_route(self, message: str) -> Optional[str]:
        """Парсинг маршрута полета"""
        match = self.compiled_patterns['route'].search(message)
        return match.group(1).strip() if match else None
    
    def _parse_operator_info(self, message: str) -> Optional[str]:
        """Парсинг информации об операторе"""
        match = self.compiled_patterns['operator'].search(message)
        return match.group(1).strip() if match else None
    
    def _validate_parsed_data(self, parsed: ParsedMessage) -> None:
        """Валидация обязательных полей"""
        if not parsed.flight_id:
            parsed.parsing_errors.append("Не найден идентификатор полета")
        
        if not parsed.departure_time and not parsed.departure_coordinates:
            parsed.parsing_errors.append("Не найдены данные о вылете (время или координаты)")
        
        # Валидация координат (должны быть в пределах России)
        if parsed.departure_coordinates:
            lon, lat = parsed.departure_coordinates
            if not (19.0 <= lon <= 180.0 and 41.0 <= lat <= 82.0):
                parsed.parsing_errors.append(f"Координаты вылета вне территории РФ: {lat}, {lon}")
        
        if parsed.arrival_coordinates:
            lon, lat = parsed.arrival_coordinates
            if not (19.0 <= lon <= 180.0 and 41.0 <= lat <= 82.0):
                parsed.parsing_errors.append(f"Координаты прилета вне территории РФ: {lat}, {lon}")


def parse_flight_messages(messages: List[str]) -> List[ParsedMessage]:
    """
    Парсинг списка сообщений о полетах
    
    Args:
        messages: Список строк сообщений
        
    Returns:
        List[ParsedMessage]: Список распарсенных сообщений
    """
    parser = FlightMessageParser()
    parsed_messages = []
    
    for message in messages:
        try:
            parsed = parser.parse_message(message)
            parsed_messages.append(parsed)
        except Exception as e:
            logger.error(f"Критическая ошибка парсинга сообщения: {e}")
            # Создаем объект с ошибкой
            error_parsed = ParsedMessage(
                message_type=MessageType.FPL,
                flight_id="UNKNOWN",
                raw_message=message,
                parsing_errors=[f"Критическая ошибка парсинга: {str(e)}"]
            )
            parsed_messages.append(error_parsed)
    
    return parsed_messages

