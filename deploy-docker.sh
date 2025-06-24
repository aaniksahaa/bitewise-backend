#!/bin/bash
set -e

echo "🚀 Starting Docker deployment..."

# Navigate to project directory
cd /home/azureuser/bitewise-backend

# Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# Handle frontend if it exists in the same repo
# if [ -d "frontend" ]; then
#     echo "🎨 Building frontend..."
#     cd frontend
#     npm install
#     npm run build
    
#     # Copy built files to nginx directory
#     sudo cp -r dist/* /var/www/bitewise/ || sudo cp -r build/* /var/www/bitewise/
#     cd ..
# fi

# Stop existing containers gracefully
echo "🛑 Stopping existing containers..."
docker compose -f docker-compose.prod.yml down || echo "No containers to stop"

# Build and start new containers
echo "🔨 Building and starting containers..."
docker compose -f docker-compose.prod.yml up --build -d

# Wait for container to be ready
echo "⏳ Waiting for API to be ready..."
sleep 10

# Health check
echo "🔍 Running health check..."
for i in {1..30}; do
    if curl -f http://localhost:8000/ > /dev/null 2>&1; then
        echo "✅ API is healthy!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ API health check failed after 30 attempts"
        docker compose -f docker-compose.prod.yml logs api
        exit 1
    fi
    sleep 2
done

# Test through nginx
echo "🌐 Testing through nginx..."
if curl -f https://bitewise.twiggle.tech/api/v1/ > /dev/null 2>&1; then
    echo "✅ API accessible through nginx!"
else
    echo "⚠️  API not accessible through nginx, but container is running"
fi

# Clean up old images to save space
echo "🧹 Cleaning up old Docker images..."
docker image prune -f

echo "🎉 Deployment completed successfully!"

# Optional: Send notification (uncomment if you want)
# curl -X POST -H 'Content-type: application/json' \
#   --data '{"text":"✅ Bitewise API deployed successfully!"}' \
#   $SLACK_WEBHOOK_URL 