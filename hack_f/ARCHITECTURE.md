# Архитектура системы отслеживания полетов БПЛА

## Обзор архитектуры

Система построена по микросервисной архитектуре с разделением на слои представления, бизнес-логики и данных. Архитектура обеспечивает масштабируемость, надежность и соответствие требованиям государственных стандартов.

## Компонентная архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │   React Web     │    │   Swagger UI    │               │
│  │   Frontend      │    │   Documentation │               │
│  │                 │    │                 │               │
│  │ • Dashboard     │    │ • API Docs      │               │
│  │ • Flight List   │    │ • OpenAPI Spec  │               │
│  │ • Analytics     │    │ • Postman       │               │
│  │ • Upload        │    │   Collection    │               │
│  │ • Reports       │    │                 │               │
│  └─────────────────┘    └─────────────────┘               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                FastAPI Backend                          │ │
│  │                                                         │ │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │ │   API       │ │  Services   │ │      Parsers        │ │ │
│  │ │             │ │             │ │                     │ │ │
│  │ │ • Flights   │ │ • Validation│ │ • Message Parser    │ │ │
│  │ │ • Upload    │ │ • Geocoding │ │ • Data Normalizer   │ │ │
│  │ │ • Analytics │ │ • Analytics │ │ • Format Converter  │ │ │
│  │ │ • Reports   │ │ • Reports   │ │                     │ │ │
│  │ │ • Regions   │ │             │ │                     │ │ │
│  │ └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐  │
│  │  PostgreSQL     │ │     Redis       │ │  File Storage │  │
│  │  + PostGIS      │ │                 │ │               │  │
│  │                 │ │ • Cache         │ │ • Uploads     │  │
│  │ • Flights       │ │ • Sessions      │ │ • Shapefiles  │  │
│  │ • Regions       │ │ • Temp Data     │ │ • Reports     │  │
│  │ • Analytics     │ │                 │ │ • Logs        │  │
│  │ • Batches       │ │                 │ │               │  │
│  └─────────────────┘ └─────────────────┘ └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               INFRASTRUCTURE LAYER                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐  │
│  │   Monitoring    │ │    Security     │ │   DevOps      │  │
│  │                 │ │                 │ │               │  │
│  │ • Prometheus    │ │ • TLS/HTTPS     │ │ • Docker      │  │
│  │ • Grafana       │ │ • CORS          │ │ • Compose     │  │
│  │ • Jaeger        │ │ • Validation    │ │ • Nginx       │  │
│  │ • Logging       │ │ • Rate Limiting │ │ • Systemd     │  │
│  └─────────────────┘ └─────────────────┘ └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Детальная архитектура компонентов

### 1. Frontend (React + TypeScript)

#### Структура компонентов
```
src/
├── components/          # Переиспользуемые компоненты
│   └── Layout.tsx      # Основной layout приложения
├── pages/              # Страницы приложения
│   ├── Dashboard.tsx   # Главная панель
│   ├── FlightsList.tsx # Список полетов
│   ├── Upload.tsx      # Загрузка данных
│   ├── Analytics.tsx   # Аналитика
│   ├── Reports.tsx     # Отчеты
│   └── Regions.tsx     # Регионы
├── services/           # API сервисы
│   └── api.ts         # HTTP клиент
└── utils/             # Утилиты
```

#### Технологический стек
- **React 18** - UI фреймворк
- **TypeScript** - типизация
- **Ant Design** - UI компоненты
- **React Router** - маршрутизация
- **Axios** - HTTP клиент
- **Recharts** - графики
- **Leaflet** - карты

### 2. Backend (FastAPI + Python)

#### Структура модулей
```
app/
├── api/                # API endpoints
│   └── api_v1/
│       ├── api.py     # Главный роутер
│       └── endpoints/ # Отдельные endpoints
├── core/              # Конфигурация
│   └── config.py     # Настройки приложения
├── db/                # База данных
│   └── database.py   # Подключение и сессии
├── models/            # Модели данных
│   ├── flight.py     # Модели полетов
│   ├── region.py     # Модели регионов
│   └── analytics.py  # Модели аналитики
├── services/          # Бизнес-логика
│   ├── validation.py # Валидация данных
│   ├── geocoding.py  # Геопривязка
│   └── analytics.py  # Аналитические сервисы
├── parsers/           # Парсеры данных
│   └── message_parser.py # Парсер телеграмм
└── utils/             # Утилиты
```

#### Технологический стек
- **Python 3.11** - язык программирования
- **FastAPI** - веб-фреймворк
- **SQLAlchemy** - ORM
- **AsyncPG** - асинхронный драйвер PostgreSQL
- **Pydantic** - валидация данных
- **Geopandas** - обработка геоданных
- **Shapely** - геометрические операции

### 3. База данных (PostgreSQL + PostGIS)

#### Схема данных
```sql
-- Схема flights: данные о полетах
flights.flights            -- Основная таблица полетов
flights.flight_batches      -- Пакеты загруженных данных

-- Схема geo: геопространственные данные
geo.russian_regions         -- Регионы РФ с границами
geo.geocode_cache          -- Кеш геопривязки
geo.shapefile_updates      -- История обновлений шейп-файлов

-- Схема analytics: аналитические данные
analytics.flight_metrics    -- Предрасчитанные метрики
analytics.region_rankings   -- Рейтинги регионов
analytics.report_generations -- История генерации отчетов
analytics.system_metrics    -- Системные метрики
```

#### Индексы и оптимизация
- **GiST индексы** для геопространственных запросов
- **B-tree индексы** для временных данных
- **Композитные индексы** для поиска дубликатов
- **Партиционирование** по времени (планируется)

## Паттерны проектирования

### 1. Repository Pattern
Используется для абстракции доступа к данным:
```python
class FlightRepository:
    async def create(self, flight_data: FlightCreate) -> Flight
    async def get_by_id(self, flight_id: str) -> Optional[Flight]
    async def search(self, criteria: SearchCriteria) -> List[Flight]
```

### 2. Service Layer Pattern
Бизнес-логика выделена в отдельные сервисы:
```python
class ValidationService:
    def validate_flight_data(self, data: ParsedMessage) -> ValidationResult
    
class GeocodingService:
    async def geocode_point(self, lat: float, lon: float) -> Optional[Region]
```

### 3. Factory Pattern
Для создания парсеров различных типов сообщений:
```python
class MessageParserFactory:
    @staticmethod
    def create_parser(message_type: MessageType) -> MessageParser
```

### 4. Observer Pattern
Для отслеживания статуса обработки пакетов:
```python
class BatchProcessor:
    def add_observer(self, observer: BatchObserver)
    def notify_observers(self, event: ProcessingEvent)
```

## Потоки данных

### 1. Поток загрузки данных
```
User Input → API Validation → Message Parsing → Data Validation → 
Geocoding → Database Storage → Status Update → Notification
```

### 2. Поток поиска полетов
```
Search Request → Parameter Validation → Database Query → 
Result Formatting → Response Caching → API Response
```

### 3. Поток аналитики
```
Raw Data → Aggregation → Metric Calculation → 
Cache Storage → API Response → Frontend Visualization
```

## Безопасность

### 1. Уровни безопасности
- **Network Level**: TLS/HTTPS, Firewall rules
- **Application Level**: Input validation, CORS, Rate limiting
- **Data Level**: SQL injection prevention, Data encryption

### 2. Валидация данных
```python
class FlightDataValidator:
    def validate_coordinates(self, lat: float, lon: float) -> bool
    def validate_time_format(self, time_str: str) -> bool
    def validate_aircraft_type(self, aircraft_type: str) -> bool
```

### 3. Аудит и логирование
- Все API запросы логируются
- Изменения данных отслеживаются
- Ошибки обработки записываются в лог

## Производительность

### 1. Кеширование
- **Redis** для кеширования API ответов
- **Application cache** для геопривязки
- **Database query cache** для часто используемых запросов

### 2. Асинхронная обработка
```python
async def process_flight_batch(batch_id: str, messages: List[str]):
    # Асинхронная обработка больших пакетов данных
    tasks = [process_single_message(msg) for msg in messages]
    results = await asyncio.gather(*tasks)
```

### 3. Пагинация и ограничения
- Пагинация для всех списочных API
- Ограничения на размер загружаемых файлов
- Таймауты для длительных операций

## Мониторинг и наблюдаемость

### 1. Метрики (Prometheus)
```python
REQUEST_COUNT = Counter('flight_api_requests_total')
REQUEST_DURATION = Histogram('flight_api_request_duration_seconds')
FLIGHT_PROCESSING_COUNT = Counter('flight_processing_total')
```

### 2. Трассировка (Jaeger)
- Распределенная трассировка HTTP запросов
- Отслеживание времени обработки
- Анализ узких мест

### 3. Логирование (Structured Logging)
```python
logger.info(
    "Flight processed",
    flight_id=flight.flight_id,
    processing_time=duration,
    region=flight.region_departure
)
```

## Масштабируемость

### 1. Горизонтальное масштабирование
- Stateless backend сервисы
- Load balancer (Nginx)
- Database connection pooling

### 2. Вертикальное масштабирование
- Настройка ресурсов контейнеров
- Оптимизация запросов к БД
- Индексирование больших таблиц

### 3. Микросервисная архитектура (будущее)
```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Flight    │ │  Analytics  │ │   Reports   │
│   Service   │ │   Service   │ │   Service   │
└─────────────┘ └─────────────┘ └─────────────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
              ┌─────────────┐
              │   Gateway   │
              │   Service   │
              └─────────────┘
```

## Развертывание

### 1. Контейнеризация
```dockerfile
# Multi-stage build для оптимизации размера образов
FROM python:3.11-slim as builder
# ... build dependencies

FROM python:3.11-slim as runtime
# ... runtime dependencies
```

### 2. Оркестрация
```yaml
# docker-compose.yml для локальной разработки
# Kubernetes для продакшена (планируется)
```

### 3. CI/CD Pipeline
```yaml
stages:
  - test
  - build
  - security_scan
  - deploy
```
