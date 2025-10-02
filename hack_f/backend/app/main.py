"""
Главный файл FastAPI приложения для системы отслеживания полетов БПЛА
В соответствии с техническим заданием
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from app.core.config import settings
from app.db.database import init_db, close_db
from app.api.api_v1.api import api_router

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Метрики Prometheus
REQUEST_COUNT = Counter(
    'flight_api_requests_total',
    'Общее количество HTTP запросов',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'flight_api_request_duration_seconds',
    'Время выполнения HTTP запросов',
    ['method', 'endpoint']
)

FLIGHT_PROCESSING_COUNT = Counter(
    'flight_processing_total',
    'Количество обработанных полетов',
    ['status']
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Инициализация при запуске
    logger.info("Запуск системы отслеживания полетов БПЛА...")
    try:
        await init_db()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        raise
    
    yield
    
    # Очистка при завершении
    logger.info("Завершение работы системы...")
    try:
        await close_db()
        logger.info("Соединение с базой данных закрыто")
    except Exception as e:
        logger.error(f"Ошибка при закрытии базы данных: {e}")


# Создание приложения FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware для доверенных хостов
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # В продакшене следует ограничить
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware для измерения времени выполнения запросов и метрик"""
    start_time = time.time()
    
    # Выполнение запроса
    response = await call_next(request)
    
    # Расчет времени выполнения
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Обновление метрик
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений"""
    logger.error(f"Необработанная ошибка в {request.url}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Внутренняя ошибка сервера",
            "message": "Произошла непредвиденная ошибка. Обратитесь к администратору.",
            "request_id": getattr(request.state, 'request_id', None)
        }
    )


# Подключение маршрутов API
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Общее"])
async def root():
    """Корневой endpoint с информацией о системе"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "description": settings.PROJECT_DESCRIPTION,
        "status": "running",
        "docs_url": "/api/docs",
        "api_version": "v1",
        "features": [
            "Парсинг сообщений согласно Табелю Минтранса РФ",
            "Геопривязка по официальным шейп-файлам Росреестра",
            "Аналитика и метрики полетов БПЛА",
            "Генерация отчетов и графиков",
            "REST API с полной документацией"
        ]
    }


@app.get("/health", tags=["Мониторинг"])
async def health_check():
    """Проверка состояния системы"""
    try:
        # Проверка подключения к базе данных
        from app.db.database import engine
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "database": "connected",
            "version": settings.PROJECT_VERSION
        }
    except Exception as e:
        logger.error(f"Ошибка проверки здоровья системы: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
        )


@app.get("/metrics", tags=["Мониторинг"])
async def metrics():
    """Endpoint для Prometheus метрик"""
    if not settings.PROMETHEUS_ENABLED:
        return JSONResponse(
            status_code=404,
            content={"error": "Метрики отключены"}
        )
    
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/info", tags=["Общее"])
async def system_info():
    """Информация о системе и конфигурации"""
    return {
        "system": {
            "name": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
            "environment": "production" if not settings.API_DEBUG else "development"
        },
        "features": {
            "prometheus_enabled": settings.PROMETHEUS_ENABLED,
            "jaeger_enabled": settings.JAEGER_ENABLED,
            "debug_mode": settings.API_DEBUG
        },
        "limits": {
            "max_flight_duration_hours": settings.MAX_FLIGHT_DURATION_HOURS,
            "min_flight_duration_minutes": settings.MIN_FLIGHT_DURATION_MINUTES,
            "batch_size": settings.BATCH_SIZE,
            "processing_timeout": settings.PROCESSING_TIMEOUT
        },
        "supported_formats": {
            "reports": settings.REPORT_FORMATS,
            "message_types": ["FPL", "DEP", "ARR", "CHG", "CNL", "DLA", "RQS", "RQP"]
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )

