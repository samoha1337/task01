"""
Endpoints для загрузки и обработки данных о полетах БПЛА
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import logging
import json
from datetime import datetime
import uuid

from app.db.database import get_db_session
from app.models.flight import FlightBatch
from app.parsers.message_parser import parse_flight_messages
from app.services.validation import validate_and_clean_flight_data
from app.services.geocoding import geocoding_service

logger = logging.getLogger(__name__)

router = APIRouter()


class MessageUploadRequest(BaseModel):
    """Модель для загрузки сообщений через JSON"""
    messages: List[str]
    source: Optional[str] = "api"
    batch_name: Optional[str] = None


class UploadResponse(BaseModel):
    """Ответ на загрузку данных"""
    batch_id: str
    status: str
    message: str
    total_messages: int
    processing_started: bool = False


class BatchStatusResponse(BaseModel):
    """Статус обработки пакета"""
    batch_id: str
    status: str
    filename: str
    total_records: int
    processed_records: int
    valid_records: int
    invalid_records: int
    upload_time: datetime
    processing_start_time: Optional[datetime]
    processing_end_time: Optional[datetime]
    error_message: Optional[str]


@router.post("/messages", response_model=UploadResponse, 
             summary="Загрузка сообщений через JSON",
             description="Загрузка пакета сообщений о полетах в формате JSON для обработки")
async def upload_messages(
    request: MessageUploadRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Загрузка сообщений о полетах через JSON API
    
    Принимает список строк сообщений в формате согласно Табелю сообщений Минтранса РФ
    """
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="Список сообщений не может быть пустым")
        
        if len(request.messages) > 10000:  # Ограничение на размер пакета
            raise HTTPException(
                status_code=400, 
                detail="Размер пакета превышает максимально допустимый (10000 сообщений)"
            )
        
        # Создание записи о пакете
        batch_id = str(uuid.uuid4())
        batch_name = request.batch_name or f"api_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        flight_batch = FlightBatch(
            id=uuid.UUID(batch_id),
            filename=batch_name,
            total_records=len(request.messages),
            status='uploading'
        )
        
        db.add(flight_batch)
        await db.commit()
        
        # Запуск фоновой обработки
        background_tasks.add_task(
            process_messages_batch,
            batch_id,
            request.messages,
            request.source
        )
        
        logger.info(f"Создан пакет {batch_id} с {len(request.messages)} сообщениями")
        
        return UploadResponse(
            batch_id=batch_id,
            status="accepted",
            message="Пакет принят к обработке",
            total_messages=len(request.messages),
            processing_started=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка загрузки сообщений: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обработки запроса")


@router.post("/file", response_model=UploadResponse,
             summary="Загрузка файла с сообщениями",
             description="Загрузка файла с сообщениями о полетах (TXT, JSON, CSV, XLSX)")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Загрузка файла с сообщениями о полетах
    
    Поддерживаемые форматы:
    - TXT: одно сообщение на строку
    - JSON: массив строк сообщений
    - CSV: столбец messages или первая колонка со строками сообщений
    - XLS/XLSX: столбец messages или первая колонка со строками сообщений
    """
    try:
        # Проверка типа файла
        if not file.filename:
            raise HTTPException(status_code=400, detail="Имя файла не указано")
        
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in ['txt', 'json', 'csv', 'xlsx', 'xls']:
            raise HTTPException(
                status_code=400,
                detail="Неподдерживаемый формат файла. Поддерживаются: TXT, JSON, CSV, XLSX, XLS"
            )
        
        # Чтение содержимого файла
        content = await file.read()
        
        # Ограничение размера файла (10 МБ)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Файл слишком большой (максимум 10 МБ)")
        
        # Парсинг содержимого
        messages = []
        if file_extension in ['txt', 'json']:
            try:
                content_str = content.decode('utf-8')
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Ошибка кодировки файла. Используйте UTF-8")

            if file_extension == 'txt':
                messages = [line.strip() for line in content_str.split('\n') if line.strip()]
            elif file_extension == 'json':
                try:
                    data = json.loads(content_str)
                    if isinstance(data, list):
                        messages = [str(msg) for msg in data if msg]
                    else:
                        raise HTTPException(status_code=400, detail="JSON должен содержать массив сообщений")
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Некорректный формат JSON")
        else:
            # CSV / Excel
            try:
                import io
                import pandas as pd

                buffer = io.BytesIO(content)
                if file_extension == 'csv':
                    df = pd.read_csv(buffer)
                else:
                    df = pd.read_excel(buffer)

                if df.empty:
                    raise HTTPException(status_code=400, detail="Файл не содержит данных")

                # Ищем столбец messages, иначе берем первую колонку
                col = None
                for candidate in ['messages', 'message', 'msg', 'text']:
                    if candidate in df.columns:
                        col = candidate
                        break
                if col is None:
                    col = df.columns[0]

                messages = [str(x).strip() for x in df[col].astype(str).tolist() if str(x).strip()]
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Ошибка чтения таблицы: {str(e)}")
        
        if not messages:
            raise HTTPException(status_code=400, detail="Файл не содержит сообщений")
        
        if len(messages) > 10000:
            raise HTTPException(
                status_code=400,
                detail="Файл содержит слишком много сообщений (максимум 10000)"
            )
        
        # Создание записи о пакете
        batch_id = str(uuid.uuid4())
        
        flight_batch = FlightBatch(
            id=uuid.UUID(batch_id),
            filename=file.filename,
            file_size=len(content),
            total_records=len(messages),
            status='uploading'
        )
        
        db.add(flight_batch)
        await db.commit()
        
        # Запуск фоновой обработки
        background_tasks.add_task(
            process_messages_batch,
            batch_id,
            messages,
            f"file:{file.filename}"
        )
        
        logger.info(f"Загружен файл {file.filename}, создан пакет {batch_id} с {len(messages)} сообщениями")
        
        return UploadResponse(
            batch_id=batch_id,
            status="accepted",
            message=f"Файл {file.filename} принят к обработке",
            total_messages=len(messages),
            processing_started=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обработки файла")


@router.get("/batch/{batch_id}/status", response_model=BatchStatusResponse,
            summary="Статус обработки пакета",
            description="Получение текущего статуса обработки загруженного пакета")
async def get_batch_status(
    batch_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Получение статуса обработки пакета"""
    try:
        from sqlalchemy import select
        
        query = select(FlightBatch).where(FlightBatch.id == uuid.UUID(batch_id))
        result = await db.execute(query)
        batch = result.scalar_one_or_none()
        
        if not batch:
            raise HTTPException(status_code=404, detail="Пакет не найден")
        
        return BatchStatusResponse(
            batch_id=str(batch.id),
            status=batch.status,
            filename=batch.filename,
            total_records=batch.total_records,
            processed_records=batch.processed_records,
            valid_records=batch.valid_records,
            invalid_records=batch.invalid_records,
            upload_time=batch.upload_time,
            processing_start_time=batch.processing_start_time,
            processing_end_time=batch.processing_end_time,
            error_message=batch.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения статуса пакета {batch_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статуса")


@router.get("/batches", 
            summary="Список пакетов",
            description="Получение списка всех загруженных пакетов с их статусами")
async def get_batches(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Получение списка пакетов"""
    try:
        from sqlalchemy import select, desc
        
        query = select(FlightBatch).order_by(desc(FlightBatch.upload_time))
        
        if status:
            query = query.where(FlightBatch.status == status)
        
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        batches = result.scalars().all()
        
        return {
            "batches": [
                {
                    "batch_id": str(batch.id),
                    "filename": batch.filename,
                    "status": batch.status,
                    "total_records": batch.total_records,
                    "processed_records": batch.processed_records,
                    "valid_records": batch.valid_records,
                    "invalid_records": batch.invalid_records,
                    "upload_time": batch.upload_time,
                    "processing_end_time": batch.processing_end_time
                }
                for batch in batches
            ],
            "total": len(batches),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения списка пакетов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")


async def process_messages_batch(batch_id: str, messages: List[str], source: str):
    """
    Фоновая обработка пакета сообщений
    """
    from app.db.database import async_session_maker
    from app.models.flight import Flight
    from geoalchemy2 import WKTElement
    
    async with async_session_maker() as db:
        try:
            # Обновление статуса на "обработка"
            from sqlalchemy import select, update
            
            await db.execute(
                update(FlightBatch)
                .where(FlightBatch.id == uuid.UUID(batch_id))
                .values(
                    status='processing',
                    processing_start_time=datetime.utcnow()
                )
            )
            await db.commit()
            
            logger.info(f"Начата обработка пакета {batch_id} с {len(messages)} сообщениями")
            
            # Парсинг сообщений
            parsed_messages = parse_flight_messages(messages)
            
            # Валидация и очистка
            validated_messages, processing_stats = validate_and_clean_flight_data(parsed_messages)
            
            # Сохранение в базу данных
            saved_count = 0
            for parsed_msg in validated_messages:
                try:
                    # Геопривязка
                    departure_region = None
                    arrival_region = None
                    
                    if parsed_msg.departure_coordinates:
                        lon, lat = parsed_msg.departure_coordinates
                        departure_region = await geocoding_service.geocode_point(lon, lat)
                    
                    if parsed_msg.arrival_coordinates:
                        lon, lat = parsed_msg.arrival_coordinates
                        arrival_region = await geocoding_service.geocode_point(lon, lat)
                    
                    # Создание записи полета
                    flight = Flight(
                        flight_id=parsed_msg.flight_id,
                        aircraft_type=parsed_msg.aircraft_type,
                        aircraft_registration=parsed_msg.aircraft_registration,
                        departure_time=parsed_msg.departure_time,
                        arrival_time=parsed_msg.arrival_time,
                        duration_minutes=parsed_msg.calculate_duration(),
                        raw_message=parsed_msg.raw_message,
                        message_type=parsed_msg.message_type.value,
                        message_source=source,
                        is_processed=True,
                        is_valid=len(parsed_msg.parsing_errors) == 0,
                        validation_errors='; '.join(parsed_msg.parsing_errors) if parsed_msg.parsing_errors else None,
                        processed_at=datetime.utcnow()
                    )
                    
                    # Добавление координат
                    if parsed_msg.departure_coordinates:
                        lon, lat = parsed_msg.departure_coordinates
                        flight.departure_point = WKTElement(f'POINT({lon} {lat})', srid=4326)
                    
                    if parsed_msg.arrival_coordinates:
                        lon, lat = parsed_msg.arrival_coordinates
                        flight.arrival_point = WKTElement(f'POINT({lon} {lat})', srid=4326)
                    
                    # Добавление информации о регионах
                    if departure_region:
                        flight.region_departure = departure_region['region_name']
                        flight.region_departure_code = departure_region['region_code']
                    
                    if arrival_region:
                        flight.region_arrival = arrival_region['region_name']
                        flight.region_arrival_code = arrival_region['region_code']
                    
                    db.add(flight)
                    saved_count += 1
                    
                except Exception as e:
                    logger.error(f"Ошибка сохранения полета {parsed_msg.flight_id}: {e}")
            
            # Сохранение всех полетов
            await db.commit()
            
            # Обновление статистики пакета
            await db.execute(
                update(FlightBatch)
                .where(FlightBatch.id == uuid.UUID(batch_id))
                .values(
                    status='completed',
                    processed_records=len(validated_messages),
                    valid_records=processing_stats['valid_count'],
                    invalid_records=processing_stats['invalid_count'],
                    processing_end_time=datetime.utcnow()
                )
            )
            await db.commit()
            
            logger.info(f"Обработка пакета {batch_id} завершена: сохранено {saved_count} полетов")
            
        except Exception as e:
            logger.error(f"Ошибка обработки пакета {batch_id}: {e}")
            
            # Обновление статуса на "ошибка"
            try:
                await db.execute(
                    update(FlightBatch)
                    .where(FlightBatch.id == uuid.UUID(batch_id))
                    .values(
                        status='failed',
                        error_message=str(e),
                        processing_end_time=datetime.utcnow()
                    )
                )
                await db.commit()
            except Exception as update_error:
                logger.error(f"Ошибка обновления статуса пакета {batch_id}: {update_error}")

