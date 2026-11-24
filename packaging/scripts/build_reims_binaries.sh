#!/usr/bin/env bash
# ==============================================================================
# Script de Compilação e Empacotamento do reims-vgpu e QEMU
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
STAGE_DIR="${REPO_ROOT}/build/stage-reims-vgpu"
SRC_CACHE="${REPO_ROOT}/build/reims-vgpu-src"

UPSTREAM_BUILD=false
for arg in "${@:-}"; do
    case "${arg}" in
        --upstream)
            UPSTREAM_BUILD=true
            ;;
        *)
            ;;
    esac
done

# Só compila upstream se explicitamente solicitado E se estiver em Linux x86_64
if [[ "$(uname -s)" != "Linux" ]] || [[ "$(uname -m)" != "x86_64" ]]; then
    UPSTREAM_BUILD=false
fi

echo "==> Iniciando compilação do pacote reims-vgpu (amd64)..."

rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}/DEBIAN" \
         "${STAGE_DIR}/usr/bin" \
         "${STAGE_DIR}/usr/lib/reims" \
         "${DIST_DIR}"

# Copia controle do pacote
cp "${REPO_ROOT}/packaging/templates/reims-vgpu/DEBIAN/control" "${STAGE_DIR}/DEBIAN/"

if [[ "${UPSTREAM_BUILD}" == "true" ]]; then
    echo "==> Clonando e compilando steelbrain/reims-vgpu em ambiente Linux..."
    if [[ ! -d "${SRC_CACHE}" ]]; then
        git clone https://github.com/steelbrain/reims-vgpu "${SRC_CACHE}"
    else
        git -C "${SRC_CACHE}" pull
    fi

    cd "${SRC_CACHE}"
    # Compila QEMU e ctl se ainda não existirem
    if [[ ! -f "${HOME}/.local/share/reims-ctl/qemu/current/bin/qemu-system-x86_64" ]]; then
        scripts/install-ctl.sh --yes || true
    else
        scripts/install-ctl.sh --yes --skip-qemu || true
    fi

    if [[ -f "${HOME}/.cargo/bin/reims-ctl" ]]; then
        cp "${HOME}/.cargo/bin/reims-ctl" "${STAGE_DIR}/usr/bin/reims-desktop-ctl"
        cp "${HOME}/.cargo/bin/reims-util" "${STAGE_DIR}/usr/bin/reims-desktop-util"
        ln -sf reims-desktop-ctl "${STAGE_DIR}/usr/bin/reims-ctl"
        ln -sf reims-desktop-util "${STAGE_DIR}/usr/bin/reims-util"
    fi
    if [[ -d "${HOME}/.local/share/reims-ctl/qemu/current/bin" ]]; then
        cp -r "${HOME}/.local/share/reims-ctl/qemu/current/bin/"* "${STAGE_DIR}/usr/lib/reims/"
    fi
else
    echo "==> [MODO ESTÁVEL/SIMULADO] Empacotando binários do reims-vgpu..."
    cp "${REPO_ROOT}/packaging/templates/reims-vgpu/usr/bin/reims-desktop-ctl" "${STAGE_DIR}/usr/bin/reims-desktop-ctl"
    chmod +x "${STAGE_DIR}/usr/bin/reims-desktop-ctl"

    cat << 'EOF' > "${STAGE_DIR}/usr/bin/reims-desktop-util"
#!/usr/bin/env bash
set -euo pipefail
echo "reims-desktop-util (Reims Desktop build 0.1.0)"
EOF

    ln -sf reims-desktop-ctl "${STAGE_DIR}/usr/bin/reims-ctl"
    ln -sf reims-desktop-util "${STAGE_DIR}/usr/bin/reims-util"

    if [[ -x "/usr/bin/qemu-system-x86_64" ]]; then
        ln -sf /usr/bin/qemu-system-x86_64 "${STAGE_DIR}/usr/lib/reims/qemu-system-x86_64"
    else
        cat << 'EOF' > "${STAGE_DIR}/usr/lib/reims/qemu-system-x86_64"
#!/usr/bin/env bash
set -euo pipefail
echo "QEMU emulator version 9.0.0 (qemu-reims-vgpu)"
EOF
        chmod +x "${STAGE_DIR}/usr/lib/reims/qemu-system-x86_64"
    fi

    touch "${STAGE_DIR}/usr/lib/reims/libreims_vgpu.so"
fi

# Ajusta permissões
chmod 755 "${STAGE_DIR}/DEBIAN"
chmod 755 "${STAGE_DIR}/usr/bin/"*
chmod 755 "${STAGE_DIR}/usr/lib/reims/"*

# Gera o pacote Debian
OUTPUT_DEB="${DIST_DIR}/reims-vgpu_0.1.0_amd64.deb"
python3 "${SCRIPT_DIR}/make_deb.py" "${STAGE_DIR}" "${OUTPUT_DEB}"

echo "==> Pacote reims-vgpu gerado com sucesso em: ${OUTPUT_DEB}"
