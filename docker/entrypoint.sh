#!/usr/bin/env bash
set -euo pipefail

# Start Ollama in the background
ollama serve >/var/log/ollama.log 2>&1 &

# Wait for Ollama API to be ready
for i in {1..60}; do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# Optionally pre-pull models
if [ "${OLLAMA_PULL_MODELS:-1}" != "0" ]; then
  ollama pull embeddinggemma
  ollama pull gemma3:latest
fi

exec python3 app.py
