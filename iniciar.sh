#!/usr/bin/env bash
# Arranca Sentinel en la red local (macOS / Linux).
# Uso: ./iniciar.sh [puerto] [--https] [--con-datos]
set -e

cd "$(dirname "$0")"
PUERTO="${1:-5000}"

if [ "$#" -gt 0 ]; then shift; fi

if ! command -v uv >/dev/null 2>&1; then
    echo "No se encontró 'uv'. Instálalo desde https://docs.astral.sh/uv/"
    exit 1
fi

echo "Instalando dependencias..."
uv sync

export PORT="$PUERTO"

exec uv run python servidor.py "$@"