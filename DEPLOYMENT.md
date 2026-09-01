# Deployment Guide — MainPixel

Production deployment instructions for MainPixel.

---

## Table of Contents

- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
- [VPS Deployment](#vps-deployment)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [SSL/TLS](#ssltls)
- [Reverse Proxy](#reverse-proxy)
- [Backup Strategy](#backup-strategy)
- [Monitoring](#monitoring)
- [Scaling](#scaling)
- [Security Checklist](#security-checklist)

---

## Deployment Options

| Option | Best For | Complexity |
|--------|----------|------------|
| **Docker Compose** | Small schools, single server | Low |
| **VPS (Hetzner, OVH, DigitalOcean)** | Production, full control | Medium |
| **AWS / GCP / Azure** | Scale, reliability | High |
| **Railway / Render** | Quick deploy, managed | Low |

---

## Docker Deployment

### Single Server Deployment

```bash
# 1. Clone the repo
git clone https://github.com/SaadEddine-ware/MainPixel.git
cd MainPixel

# 2. Create production .env
cp .env.example .env
# Edit .env with production values (see Environment Variables below)

# 3. Build and start
docker compose -f docker-compose.prod.yml up -d --build

# 4. Initialize database
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python -m app.seed

# 5. Verify
curl http://localhost:8000/health
```

### docker-compose.prod.yml

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"  # Only expose to localhost
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redisdata:/data
    ports:
      - "127.0.0.1:6379:6379"  # Only expose to localhost
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - uploads:/app/uploads
      - backups:/app/backups

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: always
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - backend
      - frontend

  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

volumes:
  pgdata:
  redisdata:
  uploads:
  backups:
```

---

## VPS Deployment

### Recommended Specifications

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| Storage | 20 GB SSD | 50 GB SSD |
| Bandwidth | 1 TB | Unlimited |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

### Provider Recommendations

| Provider | Region | Starting Price |
|----------|--------|---------------|
| Hetzner | Germany/Finland | €4.50/mo |
| OVH | France | €3.50/mo |
| DigitalOcean | Amsterdam/Frankfurt | $12/mo |
| AWS Lightsail | Frankfurt | $10/mo |

### Setup Script

```bash
#!/bin/bash
# server-setup.sh — Run on fresh Ubuntu server

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER

# Install Docker Compose
apt install docker-compose-plugin -y

# Install certbot
apt install certbot -y

# Clone the project
cd /opt
git clone https://github.com/SaadEddine-ware/MainPixel.git
cd MainPixel

# Create .env from template
cp .env.example .env
echo "Edit /opt/MainPixel/.env with production values"

# Start services
docker compose -f docker-compose.prod.yml up -d

# Set up SSL
# (See SSL/TLS section below)
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (64+ random chars) | `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `POSTGRES_DB` | Database name | `mainpixel` |
| `POSTGRES_USER` | Database user | `mainpixel` |
| `POSTGRES_PASSWORD` | Database password | `strong-random-password` |
| `REDIS_URL` | Redis connection string | `redis://:password@localhost:6379/0` |
| `REDIS_PASSWORD` | Redis password | `strong-random-password` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Backend listen address |
| `API_PORT` | `8000` | Backend listen port |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |
| `SMTP_HOST` | — | Email server host |
| `SMTP_PORT` | `587` | Email server port |
| `SMTP_USER` | — | Email username |
| `SMTP_PASSWORD` | — | Email password |
| `DEFAULT_ADMIN_EMAIL` | `superadmin@mainpixel.ma` | Super admin email |
| `DEFAULT_ADMIN_PASSWORD` | `ChangeMe123!` | Super admin password |
| `LOG_LEVEL` | `INFO` | Logging level |

### Generate Production Secrets

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate POSTGRES_PASSWORD
openssl rand -base64 32

# Generate REDIS_PASSWORD
openssl rand -base64 32
```

---

## Database Setup

### Initial Setup

```bash
# Run migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Seed super admin + Moroccan curriculum
docker compose -f docker-compose.prod.yml exec backend python -m app.seed
```

### Create First School

Via API:

```bash
curl -X POST http://localhost:8000/api/schools/register \
  -H "Content-Type: application/json" \
  -d '{
    "school_name": "Your School Name",
    "admin_email": "admin@yourschool.ma",
    "admin_password": "secure-password-here",
    "admin_full_name": "Admin Name"
  }'
```

### Enable Row-Level Security

```bash
# Connect to PostgreSQL
docker compose -f docker-compose.prod.yml exec postgres psql -U mainpixel -d mainpixel

# Run RLS setup (see DATABASE.md for full SQL)
\i /path/to/rls-setup.sql
```

### Backup Cron

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * docker compose -f /opt/MainPixel/docker-compose.prod.yml exec -T postgres pg_dump -U mainpixel mainpixel | gzip > /opt/backups/mainpixel_$(date +\%Y\%m\%d).sql.gz

# Keep only last 30 backups
0 3 * * * find /opt/backups -name "mainpixel_*.sql.gz" -mtime +30 -delete
```

---

## SSL/TLS

### Using Certbot (Let's Encrypt)

```bash
# 1. Point your domain to the server's IP
# DNS A record: mainpixel.yourdomain.com → server_ip

# 2. Stop nginx temporarily
docker compose -f docker-compose.prod.yml stop nginx

# 3. Get certificate
certbot certonly --standalone -d mainpixel.yourdomain.com

# 4. Copy certificates to nginx directory
mkdir -p ./certbot/conf/live/mainpixel.yourdomain.com
cp /etc/letsencrypt/live/mainpixel.yourdomain.com/*.pem ./certbot/conf/live/mainpixel.yourdomain.com/

# 5. Update nginx.conf with SSL server block
# (See nginx.conf section below)

# 6. Start nginx
docker compose -f docker-compose.prod.yml start nginx
```

### nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name mainpixel.yourdomain.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name mainpixel.yourdomain.com;

        ssl_certificate /etc/letsencrypt/live/mainpixel.yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/mainpixel.yourdomain.com/privkey.pem;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # API
        location /api/ {
            limit_req zone=auth burst=10 nodelay;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Docs (restrict to admin in production)
        location /docs {
            proxy_pass http://backend;
            # Add IP restriction if needed
        }

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

---

## Backup Strategy

### What to Back Up

| Component | Frequency | Retention |
|-----------|-----------|-----------|
| PostgreSQL database | Daily | 30 days |
| Redis data | Daily | 7 days |
| Uploaded files | Daily | 30 days |
| Configuration | On change | Forever |

### Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE="/opt/MainPixel/docker-compose.prod.yml"

# Database backup
docker compose -f $COMPOSE_FILE exec -T postgres \
    pg_dump -U mainpixel mainpixel | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# File backup
tar -czf $BACKUP_DIR/files_$DATE.tar.gz \
    /opt/MainPixel/backend/uploads \
    /opt/MainPixel/.env

# Cleanup old backups
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "files_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Restore Procedure

```bash
# 1. Stop the backend
docker compose -f docker-compose.prod.yml stop backend

# 2. Drop and recreate database
docker compose -f docker-compose.prod.yml exec postgres \
    psql -U mainpixel -c "DROP DATABASE mainpixel;"
docker compose -f docker-compose.prod.yml exec postgres \
    psql -U mainpixel -c "CREATE DATABASE mainpixel;"

# 3. Restore from backup
zcat /opt/backups/db_20260829_020000.sql.gz | \
    docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U mainpixel -d mainpixel

# 4. Restart backend
docker compose -f docker-compose.prod.yml start backend

# 5. Verify
curl http://localhost:8000/api/health
```

---

## Monitoring

### Health Check Endpoint

```python
# In app/main.py
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}
```

### Docker Health Checks

Already configured in `docker-compose.prod.yml` for PostgreSQL and Redis.

### Log Aggregation

For production, use structured JSON logs:

```python
# In app/main.py
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()
```

### Metrics (Future)

Add Prometheus metrics:

```python
from prometheus_client import Counter, Histogram

request_count = Counter("api_requests_total", "Total API requests", ["method", "endpoint"])
request_latency = Histogram("api_request_duration_seconds", "Request latency", ["endpoint"])
```

---

## Scaling

### Vertical Scaling (First Step)

When traffic grows:
1. Increase server CPU/RAM
2. Increase PostgreSQL `shared_buffers` and `work_mem`
3. Add Redis maxmemory policy

### Horizontal Scaling (Future)

```
                    ┌─────────────┐
                    │   Load      │
                    │   Balancer  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
         │ Backend │  │ Backend │  │ Backend │
         │   #1    │  │   #2    │  │   #3    │
         └────┬────┘  └────┬────┘  └────┬────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL │
                    │  (Primary)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Read       │
                    │  Replica    │
                    └─────────────┘
```

### Database Partitioning

For large datasets, partition heavy tables:

```sql
-- Partition attendance_records by month
CREATE TABLE attendance_records_2026_09 PARTITION OF attendance_records
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
```

---

## Security Checklist

### Before Launch

- [ ] Change all default passwords
- [ ] Set `SECRET_KEY` to random 64+ char string
- [ ] Enable SSL/TLS (HTTPS only)
- [ ] Configure CORS to only allow your domain
- [ ] Enable rate limiting on auth endpoints
- [ ] Verify RLS is enabled on all tables
- [ ] Run IDOR tests (user A accessing school B data)
- [ ] Set up automated backups
- [ ] Configure firewall (UFW/iptables)
  ```bash
  # Allow only SSH, HTTP, HTTPS
  ufw allow 22/tcp
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw enable
  ```
- [ ] Disable PostgreSQL and Redis public access
- [ ] Set up log monitoring
- [ ] Review SQL query logs for sensitive data exposure

### Ongoing Security

- [ ] Rotate `SECRET_KEY` every 90 days
- [ ] Rotate database passwords every 90 days
- [ ] Review audit logs weekly
- [ ] Update dependencies monthly (`pip-audit`, `npm audit`)
- [ ] Run penetration tests quarterly
- [ ] Monitor for failed login attempts
- [ ] Keep CNDP registration current (Moroccan law)

### Security Headers

Already configured in nginx.conf:
- `X-Frame-Options: SAMEORIGIN` — Prevents clickjacking
- `X-Content-Type-Options: nosniff` — Prevents MIME sniffing
- `X-XSS-Protection: 1; mode=block` — XSS protection
- `Strict-Transport-Security: max-age=31536000` — HSTS

### Rate Limiting

| Endpoint | Limit | Window | Action |
|----------|-------|--------|--------|
| `POST /auth/login` | 5 requests | 15 min | 429 Too Many Requests |
| `POST /auth/register` | 3 requests | 1 hour | 429 Too Many Requests |
| `POST /auth/refresh` | 10 requests | 15 min | 429 Too Many Requests |

---

## Legal Requirements (Morocco)

### Before Commercial Launch

1. **CNDP Registration**
   - Register with the National Commission for Data Protection
   - Required because processing minors' personal data
   - Website: https://www.cndp.ma

2. **Privacy Policy**
   - Present at school registration
   - Clear explanation of data collection and processing
   - In French and Arabic

3. **Data Processing Agreement (DPA)**
   - Between platform and each client school
   - Clarifies: school owns data, platform processes on their behalf

4. **Right to Data Portability**
   - Schools can export their data at any time (`POST /export/backup`)
   - Implemented in the API

---

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs backend

# Common issues:
# 1. DATABASE_URL incorrect → Check .env
# 2. Migrations not run → alembic upgrade head
# 3. Port already in use → Check for other processes
```

### Database connection pool exhausted

```python
# Increase pool size in database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
```

### High memory usage

```bash
# Check container stats
docker stats

# Restart a specific service
docker compose -f docker-compose.prod.yml restart backend
```

### SSL certificate not renewing

```bash
# Check certbot logs
docker compose -f docker-compose.prod.yml logs certbot

# Manual renewal
certbot renew --dry-run
```
