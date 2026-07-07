#!/bin/bash
set -e

export APP_URL="${APP_URL:-http://localhost:3000}"
export GEMINI_API_KEY="${GEMINI_API_KEY:-}"

echo "Initialising Redis..."
service redis-server start

echo "Applying DB migrations and seeding..."
cd /app/back-api
# DATABASE_URL is inherited from Cloud Run environment
# Assuming Alembic and seed exist
alembic upgrade head || echo "Alembic upgrade failed, continuing..."
python -m api.seed || echo "Seed failed, continuing..."
cd /app

echo "Stopping services before supervisord takes over..."
service redis-server stop
sleep 2

echo "Starting Supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
