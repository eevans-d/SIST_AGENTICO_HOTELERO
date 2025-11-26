#!/bin/bash
set -e

# Use default .env (local Docker environment)
# No need to source .env.supabase

# Run the application
~/.local/bin/poetry run uvicorn app.main:app --host 127.0.0.1 --port 8001
