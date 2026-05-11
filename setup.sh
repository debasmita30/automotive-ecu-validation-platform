#!/usr/bin/env bash
set -e

echo "=== ECU Diagnostics Platform – Setup ==="

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

mkdir -p logs reports database

echo ""
echo "=== Setup complete ==="
echo ""
echo "Commands:"
echo "  Activate venv      : source .venv/bin/activate"
echo "  SIL demo           : python main.py --mode demo"
echo "  FastAPI server     : python main.py --mode api"
echo "  Streamlit dashboard: streamlit run dashboard/app.py"
echo "  Run all tests      : pytest testing/ -v"
echo "  Docker build+run   : docker-compose up --build"
