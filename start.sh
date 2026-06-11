#!/bin/bash
set -e

# Path to local database file
DB_FILE="data/churn_analytics.db"

# Check if database file exists
if [ ! -f "$DB_FILE" ]; then
    echo "Database file $DB_FILE not found. Running data generator..."
    python3 data/generate_data.py
    
    echo "Running Machine Learning Pipeline scoring..."
    python3 ml/train.py
else
    echo "Database file $DB_FILE found. Skipping initialization."
fi

echo "Starting FastAPI application server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
