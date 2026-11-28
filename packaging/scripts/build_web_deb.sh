#!/usr/bin/env bash
set -euo pipefail

# Diretórios base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
STAGE_DIR="${REPO_ROOT}/build/stage-reims-web"

# Versão do pacote: sobrescreva com REIMS_VERSION (ex.: 0.1.0+build.20261124)
REIMS_VERSION="${REIMS_VERSION:-0.1.0}"

echo "==> Iniciando empacotamento do reims-web..."

# Limpeza e preparação
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}" "${DIST_DIR}"

# Copia template do pacote (inclui DEBIAN/, usr/bin, lib/systemd)
cp -R "${REPO_ROOT}/packaging/templates/reims-web/." "${STAGE_DIR}/"

# Instala o código Python do reims_web em dist-packages do pacote
PYTHON_DEST="${STAGE_DIR}/usr/lib/python3/dist-packages/reims_web"
mkdir -p "${PYTHON_DEST}"
cp -R "${REPO_ROOT}/reims-web/src/reims_web/." "${PYTHON_DEST}/"

# Garante permissões de execução nos scripts
chmod 755 "${STAGE_DIR}/DEBIAN"
chmod 755 "${STAGE_DIR}/DEBIAN/postinst"
chmod 755 "${STAGE_DIR}/usr/bin/"*
chmod 644 "${STAGE_DIR}/lib/systemd/system/reims-web.service"

# Aplica a versão no control e gera o pacote
sed -i.bak "s/^Version: .*/Version: ${REIMS_VERSION}/" "${STAGE_DIR}/DEBIAN/control"
rm -f "${STAGE_DIR}/DEBIAN/control.bak"

OUTPUT_DEB="${DIST_DIR}/reims-web_${REIMS_VERSION}_all.deb"
python3 "${SCRIPT_DIR}/make_deb.py" "${STAGE_DIR}" "${OUTPUT_DEB}"

echo "==> Pacote reims-web gerado com sucesso em: ${OUTPUT_DEB}"
