#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARGS=("$@")

echo "=================================================="
echo " Reims Desktop: Debian Package Compilation (.deb) "
echo "=================================================="

"${SCRIPT_DIR}/build_core_deb.sh"
"${SCRIPT_DIR}/build_gui_deb.sh"
"${SCRIPT_DIR}/build_reims_binaries.sh" "${ARGS[@]:-}"

echo ""
echo "All packages successfully generated in dist/:"
ls -lh "${SCRIPT_DIR}/../../dist"/*.deb
