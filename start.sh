#!/bin/bash

# EDU RAG - Automated Startup Script 🚀
# This script ensures local services are stopped to avoid port conflicts with Docker.

echo "------------------------------------------------"
echo "🚀 Starting EDU RAG Environment..."
echo "------------------------------------------------"

# Function to check and stop conflicting services
stop_service() {
    if systemctl is-active --quiet $1; then
        echo "⚠️  Stopping local $1 to avoid port conflicts..."
        sudo systemctl stop $1
    fi
}

# Stop known conflicting services (Postgres, Nginx, Apache)
stop_service apache2
stop_service nginx
stop_service postgresql

# Step 1: Start Infrastructure (DBs, Cache, MQ)
echo "🐳 Starting Infrastructure (Postgres, Milvus, Redis, RabbitMQ)..."
docker compose up -d postgres redis rabbitmq etcd minio milvus

# Step 2: Wait for healthy state
echo "------------------------------------------------"
echo "⏳ Waiting for databases to settle and become healthy..."

# Function to wait for container health
wait_for_health() {
    local container=$1
    local name=$2
    echo -n "🔍 Waiting for $name..."
    while [ "$(docker inspect -f '{{.State.Health.Status}}' $container 2>/dev/null)" != "healthy" ]; do
        echo -n "."
        sleep 2
    done
    echo " ✅"
}

wait_for_health edurag-postgres-1 "Postgres"
wait_for_health edurag-milvus-1 "Milvus"
wait_for_health edurag-redis-1 "Redis"

# Step 3: Start Application Services
echo "------------------------------------------------"
echo "🚀 Launching Backend API, Worker, and Frontend..."
docker compose up -d backend-api backend-worker frontend nginx
echo "------------------------------------------------"
echo "✨ System is initializing..."
sleep 5

# Final check using curl with a longer timeout (Next.js dev server needs time to compile on first hit)
echo "🔍 Verifying connection to frontend..."
if curl -s --max-time 15 http://localhost | grep -q "RAGU"; then
    echo "✅ SUCCESS! EDU RAG is reachable at: http://localhost"
    echo "📊 Dashboard & Chat are ready for use."
else
    echo "⚠️  Frontend is taking longer than expected to compile."
    echo "👉 Try refreshing your browser in 10-15 seconds."
    echo "👉 If 'localhost' fails, try: http://127.0.0.1"
    echo "📂 Run 'docker compose ps' to ensure all containers stay 'Up'."
fi

echo "------------------------------------------------"
