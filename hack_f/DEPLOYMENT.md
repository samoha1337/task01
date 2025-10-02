# Инструкция по развертыванию системы отслеживания полетов БПЛА

## Подготовка к развертыванию

### 1. Системные требования

#### Минимальные требования
- **ОС:** Linux (SUSE Linux Enterprise Server, CentOS 7+, Ubuntu 20.04+)
- **CPU:** 4 ядра x86_64
- **RAM:** 8 ГБ
- **Диск:** 50 ГБ свободного места (SSD рекомендуется)
- **Сеть:** Доступ к интернету для загрузки зависимостей

#### Рекомендуемые требования
- **ОС:** SUSE Linux Enterprise Server 15+ или CentOS 8+
- **CPU:** 8 ядер x86_64
- **RAM:** 16 ГБ
- **Диск:** 100 ГБ SSD
- **Сеть:** Выделенный сетевой интерфейс

### 2. Предустановленное ПО

#### Обязательные компоненты
```bash
# Docker Engine (20.10+)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose (2.0+)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Git
sudo yum install git -y  # CentOS/RHEL
sudo zypper install git  # SUSE
sudo apt install git -y  # Ubuntu/Debian
```

#### Проверка установки
```bash
docker --version
docker-compose --version
git --version
```

### 3. Настройка системы

#### Настройка пользователей
```bash
# Создание пользователя для системы
sudo useradd -m -s /bin/bash flighttracking
sudo usermod -aG docker flighttracking

# Переключение на пользователя
sudo su - flighttracking
```

#### Настройка файрвола
```bash
# Открытие необходимых портов
sudo firewall-cmd --permanent --add-port=3000/tcp  # Frontend
sudo firewall-cmd --permanent --add-port=8000/tcp  # Backend API
sudo firewall-cmd --permanent --add-port=5432/tcp  # PostgreSQL (если внешний доступ)
sudo firewall-cmd --permanent --add-port=3001/tcp  # Grafana
sudo firewall-cmd --permanent --add-port=9090/tcp  # Prometheus
sudo firewall-cmd --reload
```

## Процедура развертывания

### Шаг 1: Получение исходного кода

```bash
# Клонирование репозитория
cd /opt
sudo git clone <repository-url> flight-tracking-system
sudo chown -R flighttracking:flighttracking flight-tracking-system
cd flight-tracking-system
```

### Шаг 2: Настройка конфигурации

```bash
# Копирование файла конфигурации
cp env.example .env

# Редактирование конфигурации
nano .env
```

#### Основные параметры конфигурации

```bash
# Базовые настройки
PROJECT_NAME="Система отслеживания полетов БПЛА"
PROJECT_VERSION="1.0.0"
API_DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000

# База данных
DATABASE_URL=postgresql+asyncpg://flight_user:secure_password@postgres:5432/flight_tracking
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=flight_tracking
DATABASE_USER=flight_user
DATABASE_PASSWORD=secure_password

# Redis
REDIS_URL=redis://redis:6379
REDIS_HOST=redis
REDIS_PORT=6379

# Безопасность (ОБЯЗАТЕЛЬНО ИЗМЕНИТЬ)
SECRET_KEY=your-super-secure-random-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Файловые пути
UPLOAD_DIR=/app/data/uploads
SHAPEFILE_DIR=/app/data/shapefiles
REPORTS_DIR=/app/data/reports

# Производительность
MAX_WORKERS=4
BATCH_SIZE=1000
PROCESSING_TIMEOUT=300

# Мониторинг
PROMETHEUS_ENABLED=true
JAEGER_ENABLED=true
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Шаг 3: Подготовка директорий

```bash
# Создание директорий для данных
sudo mkdir -p /opt/flight-tracking-system/data/{uploads,shapefiles,reports}
sudo mkdir -p /opt/flight-tracking-system/logs
sudo mkdir -p /opt/flight-tracking-system/monitoring/grafana
sudo mkdir -p /opt/flight-tracking-system/backups

# Установка прав доступа
sudo chown -R flighttracking:flighttracking /opt/flight-tracking-system/data
sudo chown -R flighttracking:flighttracking /opt/flight-tracking-system/logs
sudo chmod -R 755 /opt/flight-tracking-system/data
```

### Шаг 4: Настройка мониторинга

#### Конфигурация Grafana
```bash
# Создание конфигурации Grafana
mkdir -p monitoring/grafana/provisioning/{dashboards,datasources}

# Настройка источника данных Prometheus
cat > monitoring/grafana/provisioning/datasources/prometheus.yml << EOF
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF
```

### Шаг 5: Загрузка шейп-файлов регионов РФ

```bash
# Создание директории для шейп-файлов
mkdir -p data/shapefiles/regions




### Шаг 6: Сборка и запуск системы

```bash
# Сборка образов
docker-compose build --no-cache

# Запуск системы
docker-compose up -d

# Проверка статуса
docker-compose ps
```

### Шаг 7: Инициализация базы данных

```bash
# Ожидание готовности базы данных
sleep 30

# Проверка подключения к БД
docker-compose exec backend python -c "
from app.db.database import engine
import asyncio
async def test_connection():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT 1')
        print('Database connection: OK')
asyncio.run(test_connection())
"
```

### Шаг 8: Проверка развертывания

#### Проверка доступности сервисов
```bash
# Проверка API
curl -f http://localhost:8000/health || echo "API недоступен"

# Проверка веб-интерфейса
curl -f http://localhost:3000 || echo "Frontend недоступен"

# Проверка мониторинга
curl -f http://localhost:9090/-/healthy || echo "Prometheus недоступен"
curl -f http://localhost:3001/api/health || echo "Grafana недоступен"
```

#### Проверка логов
```bash
# Просмотр логов всех сервисов
docker-compose logs --tail=100

# Логи конкретного сервиса
docker-compose logs backend
docker-compose logs postgres
```

## Настройка системного сервиса

### Создание systemd сервиса

```bash
# Создание файла сервиса
sudo tee /etc/systemd/system/flight-tracking.service << EOF
[Unit]
Description=Flight Tracking System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/flight-tracking-system
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0
User=flighttracking
Group=flighttracking

[Install]
WantedBy=multi-user.target
EOF

# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable flight-tracking.service
sudo systemctl start flight-tracking.service

# Проверка статуса
sudo systemctl status flight-tracking.service
```

## Настройка обратного прокси (Nginx)

### Установка Nginx

```bash
# CentOS/RHEL
sudo yum install nginx -y

# SUSE
sudo zypper install nginx

# Ubuntu/Debian
sudo apt install nginx -y
```

### Конфигурация Nginx

```bash
# Создание конфигурации сайта
sudo tee /etc/nginx/conf.d/flight-tracking.conf << EOF
upstream backend {
    server 127.0.0.1:8000;
}

upstream frontend {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.ru;
    
    # Редирект на HTTPS (после настройки SSL)
    # return 301 https://\$server_name\$request_uri;

    # API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Документация API
    location /docs {
        proxy_pass http://backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # Веб-интерфейс
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Мониторинг (доступ только с внутренних сетей)
    location /monitoring/ {
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        
        rewrite ^/monitoring/(.*)$ /\$1 break;
        proxy_pass http://127.0.0.1:3001;
        proxy_set_header Host \$host;
    }
}
EOF

# Проверка конфигурации
sudo nginx -t

# Запуск Nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

## Настройка SSL/TLS (рекомендуется)

### Получение сертификата Let's Encrypt

```bash
# Установка certbot
sudo yum install certbot python3-certbot-nginx -y  # CentOS/RHEL
sudo zypper install certbot python3-certbot-nginx  # SUSE
sudo apt install certbot python3-certbot-nginx -y  # Ubuntu

# Получение сертификата
sudo certbot --nginx -d your-domain.ru

# Автоматическое обновление
sudo crontab -e
# Добавить строку:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## Настройка резервного копирования

### Скрипт резервного копирования

```bash
# Создание скрипта backup
sudo tee /opt/flight-tracking-system/backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/opt/flight-tracking-system/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="flight_tracking_backup_${TIMESTAMP}"

# Создание директории для бэкапа
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# Резервная копия базы данных
docker-compose exec -T postgres pg_dump -U flight_user flight_tracking > "${BACKUP_DIR}/${BACKUP_NAME}/database.sql"

# Резервная копия данных
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}/data.tar.gz" data/

# Резервная копия конфигурации
cp .env "${BACKUP_DIR}/${BACKUP_NAME}/"
cp docker-compose.yml "${BACKUP_DIR}/${BACKUP_NAME}/"

# Архивирование
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"

# Удаление старых бэкапов (старше 30 дней)
find "${BACKUP_DIR}" -name "flight_tracking_backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_NAME}.tar.gz"
EOF

# Установка прав
chmod +x /opt/flight-tracking-system/backup.sh

# Настройка cron для автоматического резервного копирования
sudo crontab -e -u flighttracking
# Добавить строку для ежедневного бэкапа в 2:00:
# 0 2 * * * /opt/flight-tracking-system/backup.sh >> /opt/flight-tracking-system/logs/backup.log 2>&1
```

## Настройка мониторинга и алертов

### Конфигурация алертов Prometheus

```bash
# Создание правил алертов
mkdir -p monitoring/prometheus/rules

cat > monitoring/prometheus/rules/alerts.yml << EOF
groups:
  - name: flight_tracking_alerts
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ \$labels.instance }} is down"
          description: "{{ \$labels.instance }} has been down for more than 1 minute"

      - alert: HighCPUUsage
        expr: rate(process_cpu_seconds_total[5m]) * 100 > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ \$labels.instance }}"
          description: "CPU usage is above 80% for more than 5 minutes"

      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes / 1024 / 1024 > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ \$labels.instance }}"
          description: "Memory usage is above 1GB for more than 5 minutes"

      - alert: DatabaseConnectionError
        expr: flight_api_requests_total{status=~"5.*"} > 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection errors"
          description: "More than 10 5xx errors in 2 minutes"
EOF
```

## Обновление системы

### Процедура обновления

```bash
# Скрипт обновления
sudo tee /opt/flight-tracking-system/update.sh << 'EOF'
#!/bin/bash

set -e

echo "Starting system update..."

# Создание бэкапа перед обновлением
./backup.sh

# Остановка системы
docker-compose down

# Обновление кода
git pull origin main

# Обновление образов
docker-compose pull
docker-compose build --no-cache

# Запуск обновленной системы
docker-compose up -d

# Проверка состояния
sleep 30
docker-compose ps

# Проверка API
curl -f http://localhost:8000/health || exit 1

echo "System update completed successfully"
EOF

chmod +x /opt/flight-tracking-system/update.sh
```

## Устранение неполадок

### Диагностические команды

```bash
# Проверка состояния контейнеров
docker-compose ps

# Просмотр логов
docker-compose logs --tail=100 backend
docker-compose logs --tail=100 postgres
docker-compose logs --tail=100 frontend

# Проверка использования ресурсов
docker stats

# Проверка сетевых подключений
docker-compose exec backend netstat -tulpn
```

### Частые проблемы и решения

#### 1. Ошибка подключения к базе данных
```bash
# Проверка статуса PostgreSQL
docker-compose exec postgres pg_isready -U flight_user

# Перезапуск базы данных
docker-compose restart postgres

# Проверка логов
docker-compose logs postgres
```

#### 2. Медленная работа системы
```bash
# Увеличение ресурсов в docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

# Оптимизация PostgreSQL
docker-compose exec postgres psql -U flight_user -d flight_tracking -c "
ANALYZE;
REINDEX DATABASE flight_tracking;
"
```

#### 3. Проблемы с геопривязкой
```bash
# Проверка наличия шейп-файлов
ls -la data/shapefiles/

# Обновление шейп-файлов
curl -X POST "http://localhost:8000/api/v1/regions/update-shapefiles"

# Очистка кеша геопривязки
curl -X DELETE "http://localhost:8000/api/v1/regions/cache/cleanup"
```

## Контрольный список развертывания

### Перед запуском в продакшене

- [ ] Системные требования выполнены
- [ ] Docker и Docker Compose установлены
- [ ] Пользователь и права настроены
- [ ] Файрвол настроен
- [ ] Конфигурация (.env) настроена
- [ ] Секретные ключи изменены
- [ ] Шейп-файлы регионов РФ загружены
- [ ] Nginx настроен (если используется)
- [ ] SSL сертификаты настроены (если используется)
- [ ] Резервное копирование настроено
- [ ] Мониторинг настроен
- [ ] Systemd сервис создан
- [ ] Логирование настроено

### После развертывания

- [ ] Все сервисы запущены
- [ ] API доступен (/health возвращает OK)
- [ ] Веб-интерфейс доступен
- [ ] База данных инициализирована
- [ ] Тестовая загрузка данных работает
- [ ] Геопривязка функционирует
- [ ] Мониторинг собирает метрики
- [ ] Логи записываются
- [ ] Резервное копирование работает

## Контактная информация

При возникновении проблем с развертыванием:

1. Проверьте логи системы
2. Изучите раздел "Устранение неполадок"
3. Обратитесь к технической документации
4. Свяжитесь с командой разработки

---

**Дата создания:** Октябрь 2025  
**Версия:** 1.0.0  
**Совместимость:** Linux, Docker 20.10+, Docker Compose 2.0+

