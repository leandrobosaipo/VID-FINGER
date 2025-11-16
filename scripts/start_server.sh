#!/bin/bash
# Wrapper simples para iniciar servidor
# Uso: ./scripts/start_server.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/manage_server.sh" start

