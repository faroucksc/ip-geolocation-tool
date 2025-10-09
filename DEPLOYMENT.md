# Docker Deployment Guide

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- DirectAdmin API credentials
- `.env` file configured

### 2. Setup Environment

Copy the example environment file and configure your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:

```env
# DirectAdmin Configuration
DIRECTADMIN_HOST=https://london.mxroute.com:2222
DIRECTADMIN_USER=your_username
DIRECTADMIN_KEY=your_api_key
DEFAULT_DOMAIN=xseller.io

# JWT Authentication (auto-generated if not set)
JWT_SECRET=your_secret_key_here_min_32_chars
JWT_EXPIRE_MINUTES=1440

# Default Admin User (CHANGE IMMEDIATELY after first login)
DEFAULT_ADMIN_EMAIL=admin@xseller.io
DEFAULT_ADMIN_PASSWORD=ChangeMe123!
```

### 3. Deploy with Docker Compose

```bash
# Build and start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

The API will be available at: `http://localhost:8000`

### 4. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"ok","service":"email-provisioning-api"}
```

### 5. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 6. First Login

```bash
# Login with default admin credentials
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@xseller.io",
    "password": "ChangeMe123!"
  }'
```

**⚠️ IMPORTANT**: Change the default admin password immediately after first login!

## Docker Commands

### Start Services

```bash
docker-compose up -d
```

### Stop Services

```bash
docker-compose down
```

### View Logs

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f email-api
```

### Restart Service

```bash
docker-compose restart email-api
```

### Rebuild Image

```bash
# Rebuild after code changes
docker-compose build

# Rebuild and restart
docker-compose up -d --build
```

### Access Shell

```bash
docker-compose exec email-api /bin/bash
```

## Data Persistence

The SQLite database is persisted using a Docker volume:

```bash
# List volumes
docker volume ls | grep email

# Inspect volume
docker volume inspect email_provisioning_db

# Backup database
docker run --rm -v email_provisioning_db:/data -v $(pwd):/backup \
  alpine tar -czf /backup/email-db-backup.tar.gz -C /data .

# Restore database
docker run --rm -v email_provisioning_db:/data -v $(pwd):/backup \
  alpine tar -xzf /backup/email-db-backup.tar.gz -C /data
```

## Production Configuration

### Environment Variables

All configuration is done via environment variables in `.env`:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DIRECTADMIN_HOST` | DirectAdmin server URL | Yes | - |
| `DIRECTADMIN_USER` | DirectAdmin username | Yes | - |
| `DIRECTADMIN_KEY` | DirectAdmin API key | Yes | - |
| `DEFAULT_DOMAIN` | Default email domain | Yes | - |
| `JWT_SECRET` | JWT signing secret (min 32 chars) | No | Auto-generated |
| `JWT_EXPIRE_MINUTES` | Token expiration in minutes | No | 1440 (24 hours) |
| `DEFAULT_ADMIN_EMAIL` | Default admin email | Yes | - |
| `DEFAULT_ADMIN_PASSWORD` | Default admin password | Yes | - |

### Ports

- **8000**: API HTTP port (mapped to host)

### Health Check

Docker automatically monitors application health:

- **Endpoint**: `GET /health`
- **Interval**: Every 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3 before marking unhealthy
- **Start Period**: 10 seconds grace period

## Troubleshooting

### Check Container Status

```bash
docker-compose ps
```

### View Application Logs

```bash
docker-compose logs -f email-api
```

### Restart Container

```bash
docker-compose restart email-api
```

### Reset Everything

```bash
# Stop and remove containers, volumes, and images
docker-compose down -v --rmi local
```

### Database Issues

If database is locked or corrupted:

```bash
# Stop service
docker-compose down

# Remove volume
docker volume rm email_provisioning_db

# Restart (will create fresh database)
docker-compose up -d
```

### DirectAdmin Connection Issues

Verify credentials in `.env`:

```bash
# Test connection manually
docker-compose exec email-api python -c "
import os
from email_api.api.client import DirectAdminClient
client = DirectAdminClient(
    os.getenv('DIRECTADMIN_HOST'),
    os.getenv('DIRECTADMIN_USER'),
    os.getenv('DIRECTADMIN_KEY'),
    os.getenv('DEFAULT_DOMAIN')
)
print(client.list_emails())
"
```

## Updating the Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

## Security Best Practices

1. **Change default passwords** immediately after deployment
2. **Use strong JWT secrets** (min 32 characters, random)
3. **Enable HTTPS** via reverse proxy (nginx/traefik)
4. **Restrict API access** via firewall rules
5. **Regular backups** of the database volume
6. **Keep images updated** - rebuild regularly
7. **Monitor logs** for suspicious activity

## Reverse Proxy Setup (nginx example)

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

For HTTPS, use certbot:

```bash
sudo certbot --nginx -d api.yourdomain.com
```

## Monitoring

### Check Container Health

```bash
docker inspect email-provisioning-api | grep -A 5 Health
```

### Resource Usage

```bash
docker stats email-provisioning-api
```

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- GitHub Issues: [project-url]/issues
- Documentation: See `email_api/README.md`
