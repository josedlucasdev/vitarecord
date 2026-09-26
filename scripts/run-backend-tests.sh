#!/usr/bin/env bash
# Levanta la infraestructura minima (sin frontend/landing) y corre la suite
# de Pytest del backend dentro del contenedor. El resultado queda tambien en
# _data/test-results.log (ignorado por git) para poder revisarlo despues.
#
# Uso:  bash scripts/run-backend-tests.sh [argumentos extra de pytest]
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p _data
LOG="_data/test-results.log"
{
  echo "=== $(date) ==="
  docker compose up -d --build mysql redis storage mailtrap vault backend
  echo "Esperando a que el backend responda..."
  for i in $(seq 1 60); do
    if docker compose exec -T backend python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')" >/dev/null 2>&1; then
      echo "Backend listo."; break
    fi
    sleep 3
  done
  docker compose exec -T backend python -m pytest -q -p no:cacheprovider "$@"
  echo "=== exit code: $? ==="
} 2>&1 | tee "$LOG"
