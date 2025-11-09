#!/bin/bash
set -e

echo "Starting Tesla Sync..."

# Wait a moment for the filesystem to be ready
sleep 2

# Ensure data directory exists
mkdir -p /app/data

# Check if this is a fresh database
if [ ! -f /app/data/app.db ]; then
    echo "⚠️  WARNING: No database found at /app/data/app.db"
    echo "⚠️  A fresh database will be created. You'll need to register a new user."
    echo "⚠️  See DATABASE.md for backup/restore instructions."
else
    echo "✓ Database found at /app/data/app.db"
fi

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Start the application
echo "Starting application server..."
exec "$@"
