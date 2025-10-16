# Deployment Guide

## Quick Deploy

1. **Copy to server:**
```bash
scp -r . user@admin.faso.dev:~/email-api/
```

2. **On server, update `.env`:**
```bash
API_BASE_URL=https://admin.faso.dev
JWT_SECRET=$(openssl rand -hex 32)
```

3. **Start:**
```bash
docker-compose up -d
docker-compose logs -f
```

4. **Setup reverse proxy (Caddy):**
```caddy
admin.faso.dev {
    reverse_proxy localhost:8002
}
```

Done! Access at https://admin.faso.dev/docs
