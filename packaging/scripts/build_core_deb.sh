#!/usr/bin/env bash
set -euo pipefail

# Diretórios base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
STAGE_DIR="${REPO_ROOT}/build/stage-reims-core"

# Versão do pacote: sobrescreva com REIMS_VERSION (ex.: 0.1.0+build.20261124)
REIMS_VERSION="${REIMS_VERSION:-0.1.0}"

echo "==> Iniciando empacotamento do reims-core..."

# Limpeza e preparação
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}" "${DIST_DIR}"

# Copia arquivos do template
cp -r "${REPO_ROOT}/packaging/templates/reims-core/"* "${STAGE_DIR}/"

# Injeta tema oficial do GRUB do Reims Desktop no pacote reims-core
mkdir -p "${STAGE_DIR}/usr/share/grub/themes/reims" "${STAGE_DIR}/etc/default/grub.d"
cp -rf "${REPO_ROOT}/iso-builder/customization/grub/"* "${STAGE_DIR}/usr/share/grub/themes/reims/"
cp -f "${REPO_ROOT}/iso-builder/customization/grub/50_reims_theme.cfg" "${STAGE_DIR}/etc/default/grub.d/50_reims_theme.cfg"
chmod -R 644 "${STAGE_DIR}/usr/share/grub/themes/reims/"*
chmod 644 "${STAGE_DIR}/etc/default/grub.d/50_reims_theme.cfg"

# Garante permissões adequadas
chmod 755 "${STAGE_DIR}/DEBIAN"
chmod 755 "${STAGE_DIR}/DEBIAN/postinst"
if [[ -d "${STAGE_DIR}/usr/bin" ]]; then
    chmod 755 "${STAGE_DIR}/usr/bin/"*
fi
chmod -R 644 "${STAGE_DIR}/etc/modules-load.d/"*
chmod -R 644 "${STAGE_DIR}/etc/udev/rules.d/"*
if [[ -d "${STAGE_DIR}/etc/apt/sources.list.d" ]]; then
    chmod -R 644 "${STAGE_DIR}/etc/apt/sources.list.d/"*
fi
if [[ -d "${STAGE_DIR}/usr/share/keyrings" ]]; then
    chmod -R 644 "${STAGE_DIR}/usr/share/keyrings/"*
fi
if [[ -f "${STAGE_DIR}/etc/sudoers.d/90-reims-vm-mode" ]]; then
    chmod 440 "${STAGE_DIR}/etc/sudoers.d/90-reims-vm-mode"
fi

# Aplica a versão no control e gera o pacote
sed -i.bak "s/^Version: .*/Version: ${REIMS_VERSION}/" "${STAGE_DIR}/DEBIAN/control"
rm -f "${STAGE_DIR}/DEBIAN/control.bak"

OUTPUT_DEB="${DIST_DIR}/reims-core_${REIMS_VERSION}_all.deb"
python3 "${SCRIPT_DIR}/make_deb.py" "${STAGE_DIR}" "${OUTPUT_DEB}"

echo "==> Pacote reims-core gerado com sucesso em: ${OUTPUT_DEB}"
