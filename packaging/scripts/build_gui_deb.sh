#!/usr/bin/env bash
set -euo pipefail

# Diretórios base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
STAGE_DIR="${REPO_ROOT}/build/stage-reims-gui"

echo "==> Iniciando empacotamento do reims-gui..."

# Limpeza e preparação
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}" "${DIST_DIR}"

# Copia template do pacote
cp -r "${REPO_ROOT}/packaging/templates/reims-gui/"* "${STAGE_DIR}/"

# Instala o código Python do reims_gui em dist-packages do pacote
PYTHON_DEST="${STAGE_DIR}/usr/lib/python3/dist-packages/reims_gui"
mkdir -p "${PYTHON_DEST}"
cp -r "${REPO_ROOT}/reims-gui/src/reims_gui/"* "${PYTHON_DEST}/"

# Garante permissões de execução nos scripts
chmod 755 "${STAGE_DIR}/DEBIAN"
chmod 755 "${STAGE_DIR}/DEBIAN/postinst"
chmod 755 "${STAGE_DIR}/usr/bin/reims-gui"

# Permissões nos arquivos estáticos
chmod 644 "${STAGE_DIR}/usr/share/applications/reims-gui.desktop"
chmod 644 "${STAGE_DIR}/usr/share/icons/hicolor/scalable/apps/reims-gui.svg"

# Executa construtor de pacote
OUTPUT_DEB="${DIST_DIR}/reims-gui_0.1.0_all.deb"
python3 "${SCRIPT_DIR}/make_deb.py" "${STAGE_DIR}" "${OUTPUT_DEB}"

echo "==> Pacote reims-gui gerado com sucesso em: ${OUTPUT_DEB}"
