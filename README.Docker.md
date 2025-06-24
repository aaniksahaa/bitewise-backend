# Docker Setup for Bitewise API

This guide explains how to run the Bitewise FastAPI backend using Docker.

## Quick Start (Development)

### 1. Prerequisites

- Docker and Docker Compose installed
- Git (to clone the repository)

### 2. Clone and Setup

```bash
git clone <your-repo-url>
cd bitewise-backend
```

### 3. Environment Configuration

Copy the example environment file and configure it:

```bash
cp env.example .env
```

Edit `.env` with your actual API keys and configuration:

```bash
# Required for basic functionality
SECRET_KEY=your_super_secret_key_here
OPENAI_API_KEY=your_openai_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key_here

# Optional but recommended
RESEND_API_KEY=your_resend_api_key_here
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
```

### 4. Run with Docker Compose (Development)

```bash
# Start all services (API + PostgreSQL + Redis)
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

## Production Deployment on Azure VM

Since you already have nginx configured on your VM with SSL certificates, the production setup is simplified:

### 1. Environment Setup

Create a production `.env` file on your VM:

```bash
# Application
SECRET_KEY=<your-strong-production-secret>
ENVIRONMENT=production

# Database (use your production PostgreSQL)
DATABASE_URL=<your-production-database-url>

# Required APIs
OPENAI_API_KEY=<your-openai-key>
SUPABASE_URL=<your-supabase-url>
SUPABASE_KEY=<your-supabase-key>

# OAuth (update callback URL for production)
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
GOOGLE_CALLBACK_URL=https://bitewise.twiggle.tech/api/v1/auth/google/callback

# Email
RESEND_API_KEY=<your-resend-key>
EMAIL_FROM=<your-production-email>
```

### 2. Deploy with Docker Compose

```bash
# Build and start production API
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f api
```

### 3. Your Existing Nginx Configuration

Your current nginx config is perfect! It already:
- ✅ Handles SSL with Let's Encrypt certificates
- ✅ Proxies `/api/` requests to `http://127.0.0.1:8000`
- ✅ Serves frontend from `/var/www/bitewise`
- ✅ Redirects HTTP to HTTPS

The Docker container binds to `127.0.0.1:8000` so it works perfectly with your existing nginx proxy configuration.

### 4. Verify Deployment

```bash
# Check if API is running
curl -f http://localhost:8000/

# Check through nginx
curl -f https://bitewise.twiggle.tech/api/v1/

# View API docs
# Visit: https://bitewise.twiggle.tech/api/v1/docs
```

## Database Migrations

Migrations run automatically when the container starts. To run them manually:

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Create new migration
docker-compose -f docker-compose.prod.yml exec api alembic revision --autogenerate -m "description"
```

## Docker Commands Reference

### Building

```bash
# Build the image
docker build -t bitewise-api .

# Build with no cache
docker build --no-cache -t bitewise-api .
```

### Production Management

```bash
# Start production services
make prod-up
# or
docker-compose -f docker-compose.prod.yml up -d

# Stop production services
make prod-down
# or
docker-compose -f docker-compose.prod.yml down

# View production logs
make prod-logs
# or
docker-compose -f docker-compose.prod.yml logs -f api

# Enter production container
docker-compose -f docker-compose.prod.yml exec api bash
```

### Debugging

```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# View detailed logs
docker-compose -f docker-compose.prod.yml logs --tail=100 api

# Restart API service
docker-compose -f docker-compose.prod.yml restart api

# Check resource usage
docker stats bitewise-api-prod
```

## Services Overview

### API Service (Production)
- **Port**: 127.0.0.1:8000 (localhost only)
- **Health Check**: GET /
- **SSL**: Handled by your existing nginx
- **Domain**: https://bitewise.twiggle.tech/api/

### Database Service (Development Only)
- **Image**: postgres:15-alpine
- **Port**: 5432
- **Database**: bitewise_dev
- **User**: bitewise

## Troubleshooting

### Common Issues

1. **API Not Accessible Through Nginx**
   ```bash
   # Check if API container is running
   docker-compose -f docker-compose.prod.yml ps
   
   # Test direct API access
   curl http://localhost:8000/
   
   # Check nginx status
   sudo systemctl status nginx
   
   # Test nginx config
   sudo nginx -t
   ```

2. **Database Connection Error**
   ```bash
   # Check environment variables
   docker-compose -f docker-compose.prod.yml exec api env | grep DATABASE
   
   # Test database connection
   docker-compose -f docker-compose.prod.yml exec api python -c "
   from app.db.session import engine
   print('Database connection:', engine.url)
   "
   ```

3. **SSL Certificate Issues**
   ```bash
   # Check certificate status
   sudo certbot certificates
   
   # Renew certificates if needed
   sudo certbot renew
   
   # Restart nginx after certificate renewal
   sudo systemctl restart nginx
   ```

4. **Container Resource Issues**
   ```bash
   # Check container resources
   docker stats bitewise-api-prod
   
   # Check system resources
   free -h
   df -h
   ```

### Health Checks

```bash
# Check API health directly
curl http://localhost:8000/

# Check API through nginx
curl https://bitewise.twiggle.tech/api/v1/

# Check SSL certificate
curl -I https://bitewise.twiggle.tech/
```

## Deployment Workflow

### Initial Deployment

```bash
# 1. Clone repository on VM
git clone <repo-url>
cd bitewise-backend

# 2. Create production environment file
cp env.example .env
# Edit .env with production values

# 3. Deploy
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify
curl https://bitewise.twiggle.tech/api/v1/
```

### Updates and Maintenance

```bash
# 1. Pull latest changes
git pull origin main

# 2. Rebuild and restart
docker-compose -f docker-compose.prod.yml up --build -d

# 3. Check logs
docker-compose -f docker-compose.prod.yml logs -f api

# 4. Run any new migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Backup and Monitoring

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs --tail=100 api

# Monitor resources
docker stats bitewise-api-prod

# Backup logs
docker-compose -f docker-compose.prod.yml logs api > api-logs-$(date +%Y%m%d).log
```

## Security Notes

- ✅ Container runs as non-root user
- ✅ API bound to localhost only (127.0.0.1:8000)
- ✅ SSL handled by your existing nginx + Let's Encrypt
- ✅ Environment variables properly secured
- ✅ Resource limits configured

## Performance Notes

- **Memory**: Limited to 1GB with 512MB reservation
- **CPU**: Limited to 0.5 cores with 0.25 cores reservation
- **Logging**: Rotated logs (10MB max, 3 files)
- **Health Checks**: 30s intervals with proper timeouts

Your existing nginx configuration is production-ready and works perfectly with this Docker setup! 