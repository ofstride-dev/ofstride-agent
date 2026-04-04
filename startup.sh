#!/bin/bash
set -e
echo "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r new_agent/requirements.txt
echo "Starting Ofstride Agent..."
python -m new_agent.server