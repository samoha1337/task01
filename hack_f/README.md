# Система отслеживания полетов БПЛА

Облачная система с REST API для обработки и анализа данных о полетах беспилотных авиационных систем (БАС) на территории Российской Федерации.

## Описание

Система предназначена для:
- Обработки пакетов стандартных сообщений согласно «Табелю сообщений о движении воздушных судов в Российской Федерации» (приказ Минтранса России от 24.01.2013 №13)
- Парсинга ID полета, типа БПЛА, координат взлета/посадки, даты/времени и продолжительности
- Геопривязки каждого плана строго по границам субъектов РФ
- Хранения истории по всем загруженным периодам (глубина до года и более)
- Расчета базовых и расширенных метрик по полетам
- Предоставления данных операторам и аналитикам через REST API
- Экспорта отчетов и генерации графиков в PNG/JPEG

## Архитектура

### Технический стек

**Backend:**
- Python 3.11
- FastAPI (веб-фреймворк)
- SQLAlchemy + AsyncPG (ORM и драйвер БД)
- PostgreSQL 15 + PostGIS (база данных с геопространственными расширениями)
- Redis (кеширование)
- Geopandas, Shapely (обработка геоданных)

**Frontend:**
- React 18 + TypeScript
- Ant Design (UI компоненты)
- Leaflet (карты)
- Recharts (графики)

**Инфраструктура:**
- Docker + Docker Compose
- Prometheus + Grafana (мониторинг)
- Jaeger (трассировка)

### Компонентная архитектура

```
   ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
   │   React Web     │    │   FastAPI        │    │  PostgreSQL     │
   │   Frontend      │◄──►│   Backend        │◄──►│  + PostGIS      │
   └─────────────────┘    └──────────────────┘    └─────────────────┘
                                 │                         │
                                 ▼                         ▼
                        ┌──────────────┐         ┌─────────────┐
                        │    Redis     │         │  Шейп-файлы │
                        │   (Cache)    │         │  субъектов  │
                        └──────────────┘         │     РФ      │
                                 │                 └─────────────┘
                                 ▼
                     ┌─────────────────────┐
                     │   Prometheus +      │
                     │   Grafana +         │
                     │   Jaeger           │
                     └─────────────────────┘
```

## Быстрый старт

### Предварительные требования

- Docker 20.10+
- Docker Compose 2.0+
- Git
- Минимум 4 ГБ RAM
- 10 ГБ свободного места на диске

### Установка и запуск

1. **Клонирование репозитория:**
   ```bash
   git clone <repository-url>
   cd hack_f
   ```

2. **Настройка переменных окружения:**
   ```bash
   cp env.example .env
   # Отредактируйте .env файл при необходимости
   ```

3. **Запуск системы:**
   ```bash
   docker-compose up -d
   ```

4. **Проверка статуса:**
   ```bash
   docker-compose ps
   ```

5. **Доступ к интерфейсам:**
   - **Веб-интерфейс:** http://localhost:3000
   - **API документация:** http://localhost:8000/api/docs
   - **Grafana:** http://localhost:3001 (admin/admin)
   - **Prometheus:** http://localhost:9090
   - **Jaeger:** http://localhost:16686

### Первичная настройка

1. **Инициализация базы данных:**
   База данных инициализируется автоматически при первом запуске.

2. **Загрузка шейп-файлов регионов РФ:**
   ```bash
   # Поместите шейп-файлы субъектов РФ в директорию data/shapefiles/
   # Или используйте API для автоматической загрузки
   curl -X POST "http://localhost:8000/api/v1/regions/update-shapefiles"
   ```

## Использование системы

### Загрузка данных

#### Через веб-интерфейс
1. Перейдите в раздел "Загрузка данных"
2. Выберите способ загрузки:
   - Загрузка файла (TXT, JSON)
   - Ввод сообщений в текстовом поле
3. Отслеживайте статус обработки

#### Через API
```bash
# Загрузка сообщений через JSON
curl -X POST "http://localhost:8000/api/v1/upload/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      "FPL-UAV001-QUAD-UUDD1200-N0100F050 DCT UUEE-DOF/251015",
      "DEP-UAV001-QUAD-UUDD1205-ACTUAL DEPARTURE TIME"
    ],
    "source": "api",
    "batch_name": "test_batch"
  }'
```

### Поиск полетов

```bash
# Поиск полетов по критериям
curl "http://localhost:8000/api/v1/flights?flight_id=UAV001&limit=10"
```

### Аналитика

```bash
# Получение статистики полетов
curl "http://localhost:8000/api/v1/flights/statistics/summary"

# Региональные метрики
curl "http://localhost:8000/api/v1/analytics/metrics/regions?region_code=77"
```

## Форматы данных

### Поддерживаемые типы сообщений

Система поддерживает следующие типы сообщений согласно Табелю:

- **FPL** - План полета
- **DEP** - Вылет
- **ARR** - Прилет  
- **CHG** - Изменение плана полета
- **CNL** - Отмена плана полета
- **DLA** - Задержка
- **RQS** - Запрос статуса
- **RQP** - Запрос плана полета

### Примеры сообщений

```
FPL-UAV001-QUAD-UUDD1200-N0100F050 DCT UUEE-DOF/251015
DEP-UAV002-HELI-UUDD1205-ACTUAL DEPARTURE TIME
ARR-UAV001-QUAD-UUEE1245-ARRIVAL COMPLETED
CHG-UAV003-FIXW-UUDD1300-ROUTE CHANGE DCT UUWW
```

### Структура полей

- **Тип сообщения** - FPL/DEP/ARR/CHG/CNL/DLA/RQS/RQP
- **ID полета** - уникальный идентификатор (до 7 символов)
- **Тип БПЛА** - QUAD/HEXA/OCTO/FIXW/HELI/GYRO/BALL/GLID/PARA/UNKN
- **Аэродром и время** - код ICAO + время в формате HHMM
- **Координаты** - в формате WGS84 (десятичные градусы или градусы-минуты)
- **Маршрут** - описание маршрута полета
- **Дополнительные поля** - высота, скорость, оператор, цель полета

## Конфигурация

### Основные настройки (.env)

```bash
# База данных
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/flight_tracking
DATABASE_HOST=postgres
DATABASE_PORT=5432

# Redis
REDIS_URL=redis://redis:6379

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Безопасность
SECRET_KEY=your-super-secret-key-change-this-in-production

# Файловое хранилище
UPLOAD_DIR=./data/uploads
SHAPEFILE_DIR=./data/shapefiles
REPORTS_DIR=./data/reports

# Производительность
MAX_WORKERS=4
BATCH_SIZE=1000
PROCESSING_TIMEOUT=300
```

### Настройки производительности

- **MAX_WORKERS** - количество воркеров для обработки
- **BATCH_SIZE** - размер пакета для обработки (до 10,000)
- **PROCESSING_TIMEOUT** - таймаут обработки пакета (5 минут)

## API документация

### Основные endpoints

- `GET /` - Информация о системе
- `GET /health` - Проверка состояния
- `GET /api/docs` - Swagger UI документация

### Полеты
- `GET /api/v1/flights` - Поиск полетов
- `GET /api/v1/flights/{flight_id}` - Получение полета
- `GET /api/v1/flights/statistics/summary` - Общая статистика

### Загрузка данных
- `POST /api/v1/upload/messages` - Загрузка сообщений
- `POST /api/v1/upload/file` - Загрузка файла
- `GET /api/v1/upload/batch/{batch_id}/status` - Статус пакета

### Регионы
- `GET /api/v1/regions` - Список регионов РФ
- `GET /api/v1/regions/geocode` - Геопривязка координат

### Аналитика
- `GET /api/v1/analytics/metrics/regions` - Региональные метрики
- `GET /api/v1/analytics/ranking` - Рейтинг регионов

## Мониторинг и логирование

### Prometheus метрики

Система экспортирует следующие метрики:

- `flight_api_requests_total` - Общее количество HTTP запросов
- `flight_api_request_duration_seconds` - Время выполнения запросов
- `flight_processing_total` - Количество обработанных полетов

### Grafana дашборды

Доступные дашборды:
- Общая статистика API
- Производительность системы
- Статистика полетов
- Геопространственная аналитика

### Логирование

Логи доступны через Docker:
```bash
# Логи backend
docker-compose logs -f backend

# Логи всех сервисов
docker-compose logs -f
```

## Безопасность

### Текущие меры безопасности

- CORS настройки для веб-интерфейса
- Валидация входных данных
- Ограничения на размер загружаемых файлов
- Таймауты для предотвращения DoS

### Рекомендации для продакшена

1. **Изменить секретные ключи:**
   ```bash
   SECRET_KEY=your-super-secure-random-key
   ```

2. **Настроить HTTPS:**
   - Использовать обратный прокси (nginx)
   - Настроить SSL сертификаты

3. **Ограничить доступ к базе данных:**
   - Создать отдельного пользователя БД
   - Настроить сетевые политики

4. **Настроить аутентификацию:**
   - Интеграция с Keycloak
   - JWT токены

## Развертывание в продакшене

### Системные требования

**Минимальные:**
- CPU: 4 ядра
- RAM: 8 ГБ
- Диск: 50 ГБ SSD
- ОС: Linux (SUSE, CentOS, Ubuntu)

**Рекомендуемые:**
- CPU: 8 ядер
- RAM: 16 ГБ
- Диск: 100 ГБ SSD
- ОС: Linux с Docker поддержкой

### Масштабирование

1. **Горизонтальное масштабирование backend:**
   ```yaml
   backend:
     deploy:
       replicas: 3
   ```

2. **Настройка load balancer:**
   - Nginx или HAProxy
   - Распределение нагрузки между репликами

3. **Кластер PostgreSQL:**
   - Настройка репликации
   - Использование connection pooling

## Обслуживание

### Резервное копирование

```bash
# Резервная копия базы данных
docker-compose exec postgres pg_dump -U postgres flight_tracking > backup.sql

# Резервная копия данных
tar -czf data_backup.tar.gz data/
```

### Обновление системы

```bash
# Остановка системы
docker-compose down

# Обновление кода
git pull

# Пересборка образов
docker-compose build

# Запуск обновленной системы
docker-compose up -d
```

### Очистка данных

```bash
# Очистка старых логов Docker
docker system prune -f

# Очистка кеша геопривязки (через API)
curl -X DELETE "http://localhost:8000/api/v1/regions/cache/cleanup"
```

## Устранение неполадок

### Частые проблемы

1. **Ошибка подключения к базе данных:**
   ```bash
   # Проверить статус контейнера
   docker-compose ps postgres
   
   # Проверить логи
   docker-compose logs postgres
   ```

2. **Медленная обработка данных:**
   - Увеличить `MAX_WORKERS`
   - Проверить использование ресурсов
   - Оптимизировать индексы БД

3. **Ошибки парсинга сообщений:**
   - Проверить формат входных данных
   - Посмотреть логи валидации
   - Использовать примеры сообщений

### Диагностика

```bash
# Проверка состояния системы
curl http://localhost:8000/health

# Проверка метрик
curl http://localhost:8000/metrics

# Информация о системе
curl http://localhost:8000/info
```
