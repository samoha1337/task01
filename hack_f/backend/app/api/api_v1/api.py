"""
Главный роутер API v1 для системы отслеживания полетов БПЛА
"""

from fastapi import APIRouter

from app.api.api_v1.endpoints import flights, analytics, regions, reports, upload

api_router = APIRouter()

# Подключение всех endpoint'ов
api_router.include_router(
    flights.router,
    prefix="/flights",
    tags=["Полеты"]
)

api_router.include_router(
    upload.router,
    prefix="/upload",
    tags=["Загрузка данных"]
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Аналитика"]
)

api_router.include_router(
    regions.router,
    prefix="/regions",
    tags=["Регионы"]
)

api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Отчеты"]
)

