#!/bin/bash

# Health Check Script for VM Deployment
echo "🔍 Checking service health..."

# Check if containers are running
echo "📦 Container Status:"
docker-compose -f docker-compose.vm.yml --env-file .env.vm ps

echo ""
echo "🌐 Service Health Checks:"

# Check Supabase Database
if docker exec bitewise-supabase-db pg_isready -U supabase_admin -d postgres > /dev/null 2>&1; then
    echo "✅ Supabase Database: Healthy"
else
    echo "❌ Supabase Database: Unhealthy"
fi

# Check Supabase REST API
if curl -f http://localhost:54321/rest/v1/ > /dev/null 2>&1; then
    echo "✅ Supabase REST API: Healthy"
else
    echo "❌ Supabase REST API: Unhealthy"
fi

# Check Supabase Auth
if curl -f http://localhost:54324/health > /dev/null 2>&1; then
    echo "✅ Supabase Auth: Healthy"
else
    echo "❌ Supabase Auth: Unhealthy"
fi

# Check Supabase Storage
if curl -f http://localhost:54325/status > /dev/null 2>&1; then
    echo "✅ Supabase Storage: Healthy"
else
    echo "❌ Supabase Storage: Unhealthy"
fi

# Check FastAPI
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ FastAPI Backend: Healthy"
else
    echo "❌ FastAPI Backend: Unhealthy"
fi

echo ""
echo "📊 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"