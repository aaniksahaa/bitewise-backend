#!/bin/bash

# VM Deployment Script for BiteWise Backend with Supabase
set -e

echo "🚀 Starting VM deployment..."

# Check if .env.vm exists
if [ ! -f .env.vm ]; then
    echo "❌ .env.vm file not found!"
    echo "Please copy .env.vm.example to .env.vm and configure your settings"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env.vm | xargs)

# Check deployment method
DEPLOYMENT_METHOD=${1:-"docker"}  # Default to docker, can be "supabase-cli"

echo "📋 Deployment method: $DEPLOYMENT_METHOD"

if [ "$DEPLOYMENT_METHOD" = "supabase-cli" ]; then
    echo "🔧 Using Supabase CLI deployment method..."
    
    # Check if Supabase CLI is installed
    if ! command -v supabase &> /dev/null; then
        echo "❌ Supabase CLI not found! Installing..."
        
        # Install Supabase CLI
        if command -v npm &> /dev/null; then
            npm install -g supabase
        else
            echo "Installing Supabase CLI via direct download..."
            curl -L https://github.com/supabase/cli/releases/latest/download/supabase_linux_amd64.tar.gz | tar -xz
            sudo mv supabase /usr/local/bin/
        fi
    fi
    
    # Authenticate with Supabase using access token
    if [ -n "$SUPABASE_ACCESS_TOKEN" ]; then
        echo "🔐 Authenticating with Supabase using access token..."
        echo "$SUPABASE_ACCESS_TOKEN" | supabase login --token
    else
        echo "❌ SUPABASE_ACCESS_TOKEN not found in .env.vm!"
        echo "Please get your access token from: https://supabase.com/dashboard/account/tokens"
        exit 1
    fi
    
    # Start Supabase locally
    echo "🚀 Starting Supabase services..."
    supabase start
    
    # Get the local Supabase URLs
    SUPABASE_LOCAL_URL=$(supabase status | grep "API URL" | awk '{print $3}')
    SUPABASE_LOCAL_ANON_KEY=$(supabase status | grep "anon key" | awk '{print $3}')
    
    echo "✅ Supabase started successfully!"
    echo "   API URL: $SUPABASE_LOCAL_URL"
    echo "   Anon Key: ${SUPABASE_LOCAL_ANON_KEY:0:20}..."
    
    # Update environment for FastAPI
    export SUPABASE_URL=$SUPABASE_LOCAL_URL
    export SUPABASE_KEY=$SUPABASE_LOCAL_ANON_KEY
    
    # Deploy FastAPI with production docker-compose
    echo "🐳 Starting FastAPI application..."
    docker-compose -f docker-compose.prod.yml --env-file .env.vm up -d --build
    
else
    echo "🐳 Using Docker Compose deployment method..."
    
    # Stop any existing containers
    docker-compose -f docker-compose.vm.yml --env-file .env.vm down
    
    # Pull latest images
    docker-compose -f docker-compose.vm.yml --env-file .env.vm pull
    
    # Build and start services
    docker-compose -f docker-compose.vm.yml --env-file .env.vm up -d --build
    
    echo "⏳ Waiting for services to be ready..."
    
    # Wait for database to be ready
    echo "Waiting for Supabase database..."
    until docker exec bitewise-supabase-db pg_isready -U supabase_admin -d postgres; do
        echo "Database is unavailable - sleeping"
        sleep 2
    done
    
    echo "✅ Database is ready!"
    
    # Wait for REST API to be ready
    echo "Waiting for Supabase REST API..."
    until curl -f http://localhost:54321/rest/v1/ > /dev/null 2>&1; do
        echo "REST API is unavailable - sleeping"
        sleep 2
    done
    
    echo "✅ REST API is ready!"
    
    # Wait for Auth service to be ready
    echo "Waiting for Supabase Auth..."
    until curl -f http://localhost:54324/health > /dev/null 2>&1; do
        echo "Auth service is unavailable - sleeping"
        sleep 2
    done
    
    echo "✅ Auth service is ready!"
    
    # Wait for main API to be ready
    echo "Waiting for FastAPI application..."
    until curl -f http://localhost:8000/ > /dev/null 2>&1; do
        echo "FastAPI is unavailable - sleeping"
        sleep 2
    done
    
    echo "✅ FastAPI is ready!"
fi

echo "🎉 Deployment completed successfully!"
echo ""
if [ "$DEPLOYMENT_METHOD" = "supabase-cli" ]; then
    echo "📋 Service URLs (Supabase CLI mode):"
    echo "   • FastAPI Backend: http://localhost:8000"
    echo "   • Supabase Studio: http://localhost:54323"
    echo "   • Supabase REST API: $SUPABASE_LOCAL_URL"
    echo "   • Supabase Auth: http://localhost:54324"
    echo "   • PostgreSQL: localhost:54322"
    echo ""
    echo "📊 Check Supabase status:"
    echo "   supabase status"
    echo ""
    echo "🛑 Stop services:"
    echo "   docker-compose -f docker-compose.prod.yml down"
    echo "   supabase stop"
else
    echo "📋 Service URLs (Docker Compose mode):"
    echo "   • FastAPI Backend: http://localhost:8000"
    echo "   • Supabase REST API: http://localhost:54321"
    echo "   • Supabase Auth: http://localhost:54324"
    echo "   • Supabase Storage: http://localhost:54325"
    echo "   • PostgreSQL: localhost:54322"
    echo ""
    echo "📊 Check service status:"
    echo "   docker-compose -f docker-compose.vm.yml --env-file .env.vm ps"
    echo ""
    echo "📝 View logs:"
    echo "   docker-compose -f docker-compose.vm.yml --env-file .env.vm logs -f [service_name]"
    echo ""
    echo "🛑 Stop services:"
    echo "   docker-compose -f docker-compose.vm.yml --env-file .env.vm down"
fi