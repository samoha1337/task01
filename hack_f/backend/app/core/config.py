"""
Конфигурация приложения для системы отслеживания полетов БПЛА
В соответствии с техническим заданием
"""

from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = False
    API_RELOAD: bool = False
    PROJECT_NAME: str = "Система отслеживания полетов БПЛА"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = "REST API для обработки данных о полетах БПЛА согласно Табелю сообщений Минтранса РФ"
    
    # Настройки базы данных
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/flight_tracking"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "flight_tracking"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    
    # Настройки Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Настройки безопасности
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Настройки Keycloak (если используется)
    KEYCLOAK_SERVER_URL: Optional[str] = None
    KEYCLOAK_REALM: Optional[str] = None
    KEYCLOAK_CLIENT_ID: Optional[str] = None
    KEYCLOAK_CLIENT_SECRET: Optional[str] = None
    
    # Настройки файлового хранилища
    UPLOAD_DIR: str = "./data/uploads"
    SHAPEFILE_DIR: str = "./data/shapefiles"
    REPORTS_DIR: str = "./data/reports"
    
    # Настройки мониторинга
    PROMETHEUS_ENABLED: bool = True
    JAEGER_ENABLED: bool = True
    
    # Настройки логирования
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Настройки производительности
    MAX_WORKERS: int = 4
    BATCH_SIZE: int = 1000
    PROCESSING_TIMEOUT: int = 300  # 5 минут
    
    # Настройки для обработки полетов
    MAX_FLIGHT_DURATION_HOURS: int = 24
    MIN_FLIGHT_DURATION_MINUTES: int = 1
    
    # Настройки CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Настройки для генерации отчетов
    REPORT_FORMATS: List[str] = ["json", "csv", "xlsx", "png", "jpeg"]
    CHART_DPI: int = 300
    CHART_WIDTH: int = 1920
    CHART_HEIGHT: int = 1080
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Создание глобального объекта настроек
settings = Settings()

