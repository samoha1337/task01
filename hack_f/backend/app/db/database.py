"""
Конфигурация базы данных для системы отслеживания полетов БПЛА
Использует PostgreSQL с расширением PostGIS
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Создание асинхронного движка базы данных
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.API_DEBUG,  # Логирование SQL-запросов в режиме отладки
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_recycle=3600,  # Переподключение каждый час
)

# Создание фабрики сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Метаданные для таблиц
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    metadata = metadata


# Dependency для получения сессии базы данных
async def get_db_session() -> AsyncSession:
    """
    Dependency для получения сессии базы данных
    Используется в FastAPI endpoints
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Инициализация базы данных
    Создание всех таблиц
    """
    try:
        async with engine.begin() as conn:
            # Создание всех таблиц
            await conn.run_sync(Base.metadata.create_all)
            logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        raise


async def close_db():
    """
    Закрытие соединения с базой данных
    """
    await engine.dispose()
    logger.info("Соединение с базой данных закрыто")

