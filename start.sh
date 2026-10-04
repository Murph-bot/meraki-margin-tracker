#!/bin/sh
set -e
cd /app/backend
python -m app.scripts.reencrypt_connections
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
