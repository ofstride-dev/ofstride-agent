#!/bin/bash
set -e
echo "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt
echo "Starting application..."
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}
