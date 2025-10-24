#!/bin/bash
set -e

echo "Starting Tesla-Amber-Sync..."

# Wait a moment for the filesystem to be ready
sleep 2

# Ensure data directory exists
mkdir -p /app/data

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Start the application
echo "Starting application server..."
exec "$@"
