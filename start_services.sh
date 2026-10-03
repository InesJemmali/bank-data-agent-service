#!/bin/bash
# Starts Ollama and the API on the current compute node
# Usage: source start_services.sh

source env.sh

ollama serve > ollama_job.log 2>&1 &
echo "Waiting for Ollama to start..."
until curl -s http://$OLLAMA_HOST/api/tags > /dev/null; do sleep 2; done
echo "Ollama is running at $OLLAMA_HOST"

uvicorn api:app --host 127.0.0.1 --port 8000 > api_job.log 2>&1 &
echo "Waiting for API to start..."
until curl -s localhost:8000/health > /dev/null; do sleep 2;done
echo "API is running at $(hostname):8000"
curl -s localhoist:8000/health; echo
