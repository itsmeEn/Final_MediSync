#!/bin/bash

# MediSync Analytics System Startup Script
echo "Starting MediSync Analytics System..."

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Starting Redis server..."
    redis-server --daemonize yes
    sleep 2
fi

# Start Celery Worker
echo "Starting Celery Worker..."
celery -A backend worker --loglevel=info --detach

# Start Celery Beat (for scheduled tasks)
echo "Starting Celery Beat..."
celery -A backend beat --loglevel=info --detach

# Start Django development server
echo "Starting Django server..."
python manage.py runserver 0.0.0.0:8000

echo "Analytics system started successfully!"
echo "Celery Worker: Running in background"
echo "Celery Beat: Running in background" 
echo "Django Server: Running on http://localhost:8000"
echo ""
echo "Analytics API Endpoints:"
echo "- GET /analytics/ - Get analytics results"
echo "- POST /analytics/ - Trigger new analysis"
echo "- GET /analytics/status/{task_id}/ - Check task status"
echo "- GET /analytics/realtime/ - Real-time analytics dashboard"
echo "- GET /analytics/stream/ - Real-time analytics stream"
