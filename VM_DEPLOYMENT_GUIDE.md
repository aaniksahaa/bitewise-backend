# VM Deployment Guide

This guide covers deploying BiteWise backend to your VM with Supabase, addressing CI/CD compatibility and authentication issues.

## 🔧 Pre-Deployment Setup

### 1. Get Supabase Access Token (Required for VM)

Since VMs don't have browsers, you need an access token for Supabase CLI authentication:

1. Go to [Supabase Dashboard → Account → Access Tokens](https://supabase.com/dashboard/account/tokens)
2. Click "Generate new token"
3. Give it a name like "VM Deployment"
4. Copy the token (you won't see it again!)

### 2. Configure Environment

```bash
# Copy the example file
cp .env.vm.example .env.vm

# Edit with your actual values
nano .env.vm
```

**Important**: Add your Supabase access token to `.env.vm`:
```bash
SUPABASE_ACCESS_TOKEN=sbp_your_actual_access_token_here
```

## 🚀 Deployment Options

### Option 1: Supabase CLI (Recommended)

**Pros:**
- Exact same setup as local development
- Automatic migration sync
- Built-in Supabase Studio UI
- Easy to manage

**Deploy:**
```bash
./deploy-vm.sh supabase-cli
```

**What it does:**
1. Installs Supabase CLI if needed
2. Authenticates using your access token (no browser needed!)
3. Starts local Supabase services
4. Deploys FastAPI with production settings

### Option 2: Docker Compose (Full Stack)

**Pros:**
- Complete control over all services
- Single docker-compose file
- No external dependencies

**Deploy:**
```bash
./deploy-vm.sh docker
# or just
./deploy-vm.sh
```

## 📋 Service URLs

### Supabase CLI Mode:
- **FastAPI Backend**: http://your-vm-ip:8000
- **Supabase Studio**: http://your-vm-ip:54323
- **Supabase REST API**: http://your-vm-ip:54321
- **PostgreSQL**: your-vm-ip:54322

### Docker Compose Mode:
- **FastAPI Backend**: http://your-vm-ip:8000
- **Supabase REST API**: http://your-vm-ip:54321
- **Supabase Auth**: http://your-vm-ip:54324
- **Supabase Storage**: http://your-vm-ip:54325
- **PostgreSQL**: your-vm-ip:54322

## 🔍 Health Checks

```bash
# Check all services
./check-vm-health.sh

# Check Supabase status (CLI mode only)
supabase status

# Check Docker containers
docker ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f  # CLI mode
docker-compose -f docker-compose.vm.yml logs -f    # Docker mode
```

## 🛑 Stop Services

### Supabase CLI Mode:
```bash
docker-compose -f docker-compose.prod.yml down
supabase stop
```

### Docker Compose Mode:
```bash
docker-compose -f docker-compose.vm.yml --env-file .env.vm down
```

## 🔄 GitHub CI/CD Compatibility

The GitHub workflows have been updated to work with the new test structure:

### CI Workflow Changes:
- ✅ Updated test paths to match new structure
- ✅ Added missing environment variables
- ✅ Split tests into unit/integration/config categories
- ✅ Added proper async test support
- ✅ Skip external API tests in CI

### CD Workflow:
- ✅ Compatible with both deployment methods
- ✅ Uses existing SSH deployment to your VM

## 🐛 Troubleshooting

### Supabase CLI Authentication Issues:
```bash
# Check if authenticated
supabase projects list

# Re-authenticate if needed
echo "your_access_token" | supabase login --token
```

### Database Connection Issues:
```bash
# Check database health
docker exec bitewise-supabase-db pg_isready -U supabase_admin -d postgres

# Check database logs
docker logs bitewise-supabase-db
```

### Port Conflicts:
```bash
# Check what's using ports
sudo netstat -tulpn | grep :54321
sudo netstat -tulpn | grep :8000

# Kill conflicting processes if needed
sudo fuser -k 54321/tcp
```

### Migration Issues:
```bash
# Reset Supabase (CLI mode)
supabase db reset

# Check migration status
supabase migration list
```

## 🔐 Security Notes

1. **Access Token**: Keep your Supabase access token secure in `.env.vm`
2. **Firewall**: Configure your VM firewall to allow necessary ports
3. **SSL**: Consider setting up SSL/TLS for production
4. **Database**: Use strong passwords for database users

## 📊 Monitoring

### Check Resource Usage:
```bash
# CPU and Memory
htop

# Docker stats
docker stats

# Disk usage
df -h
```

### Log Monitoring:
```bash
# FastAPI logs
docker logs bitewise-api -f

# Database logs
docker logs bitewise-supabase-db -f

# All services
docker-compose logs -f
```

## 🔄 Updates and Maintenance

### Update Application:
```bash
# Pull latest code
git pull origin main

# Redeploy
./deploy-vm.sh supabase-cli  # or docker
```

### Database Backups:
```bash
# Backup (CLI mode)
supabase db dump > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup (Docker mode)
docker exec bitewise-supabase-db pg_dump -U supabase_admin postgres > backup.sql
```

## 🆘 Emergency Recovery

### Complete Reset:
```bash
# Stop everything
docker-compose -f docker-compose.vm.yml down -v
supabase stop

# Remove all data (⚠️ DESTRUCTIVE)
docker system prune -a --volumes

# Redeploy from scratch
./deploy-vm.sh supabase-cli
```

### Restore from Backup:
```bash
# CLI mode
supabase db reset
psql -h localhost -p 54322 -U postgres < backup.sql

# Docker mode
docker exec -i bitewise-supabase-db psql -U supabase_admin postgres < backup.sql
```