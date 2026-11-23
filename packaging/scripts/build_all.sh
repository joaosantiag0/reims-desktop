#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARGS=("$@")

echo "=================================================="
echo "    ReimsOS: Compilação de Pacotes Debian (.deb)  "
echo "=================================================="

"${SCRIPT_DIR}/build_core_deb.sh"
"${SCRIPT_DIR}/build_gui_deb.sh"
"${SCRIPT_DIR}/build_reims_binaries.sh" "${ARGS[@]:-}"

echo ""
echo "Todos os pacotes foram gerados com sucesso no diretório dist/:"
ls -lh "${SCRIPT_DIR}/../../dist"/*.deb
