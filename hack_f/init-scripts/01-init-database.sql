-- Создание базы данных для системы отслеживания полетов БПЛА
-- В соответствии с техническим заданием

-- Включение расширения PostGIS для работы с геопространственными данными
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_raster;

-- Создание схемы для данных о полетах
CREATE SCHEMA IF NOT EXISTS flights;
CREATE SCHEMA IF NOT EXISTS geo;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Создание пользователя для приложения
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'flight_app') THEN

      CREATE ROLE flight_app LOGIN PASSWORD 'flight_app_password';
   END IF;
END
$do$;

-- Предоставление прав доступа
GRANT USAGE ON SCHEMA flights TO flight_app;
GRANT USAGE ON SCHEMA geo TO flight_app;
GRANT USAGE ON SCHEMA analytics TO flight_app;
GRANT CREATE ON SCHEMA flights TO flight_app;
GRANT CREATE ON SCHEMA geo TO flight_app;
GRANT CREATE ON SCHEMA analytics TO flight_app;

-- Создание индексов для оптимизации пространственных запросов
-- Будут созданы автоматически через SQLAlchemy, но подготавливаем структуру

COMMENT ON SCHEMA flights IS 'Схема для хранения данных о полетах БПЛА';
COMMENT ON SCHEMA geo IS 'Схема для геопространственных данных и границ субъектов РФ';
COMMENT ON SCHEMA analytics IS 'Схема для аналитических данных и метрик';

