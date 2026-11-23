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

MOCK_BUILD=false
for arg in "${@:-}"; do
    case "${arg}" in
        --mock|--dry-run)
            MOCK_BUILD=true
            ;;
        *)
            ;;
    esac
done

# Se não estiver no Linux x86_64, ativa automaticamente o modo mock para desenvolvimento
if [[ "$(uname -s)" != "Linux" ]] || [[ "$(uname -m)" != "x86_64" ]]; then
    MOCK_BUILD=true
fi

echo "==> Iniciando compilação do pacote reims-vgpu (amd64)..."

rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}/DEBIAN" \
         "${STAGE_DIR}/usr/bin" \
         "${STAGE_DIR}/usr/lib/reims" \
         "${DIST_DIR}"

# Copia controle do pacote
cp "${REPO_ROOT}/packaging/templates/reims-vgpu/DEBIAN/control" "${STAGE_DIR}/DEBIAN/"

if [[ "${MOCK_BUILD}" == "true" ]]; then
    echo "==> [MODO MOCK ATIVO] Gerando binários simulados para teste de empacotamento..."
    cat << 'EOF' > "${STAGE_DIR}/usr/bin/reims-ctl"
#!/usr/bin/env bash
set -euo pipefail
echo "reims-ctl (ReimsOS mock build 0.1.0)"
if [[ "${1:-}" == "doctor" ]]; then
    echo "KVM: ok (/dev/kvm)"
    echo "udmabuf: ok (/dev/udmabuf)"
    echo "vulkan: ok (1.3)"
    echo "qemu: ok (reims-vgpu)"
elif [[ "${1:-}" == "gpus" ]]; then
    echo "[10de:2786] NVIDIA GeForce RTX 4070"
    echo "[1002:15bf] AMD Radeon 780M"
elif [[ "${1:-}" == "list" && "${2:-}" == "--json" ]]; then
    echo "[]"
fi
EOF

    cat << 'EOF' > "${STAGE_DIR}/usr/bin/reims-util"
#!/usr/bin/env bash
set -euo pipefail
echo "reims-util (ReimsOS mock build 0.1.0)"
EOF

    cat << 'EOF' > "${STAGE_DIR}/usr/lib/reims/qemu-system-x86_64"
#!/usr/bin/env bash
set -euo pipefail
echo "QEMU emulator version 9.0.0 (qemu-reims-vgpu)"
EOF

    touch "${STAGE_DIR}/usr/lib/reims/libreims_vgpu.so"
else
    echo "==> Clonando e compilando steelbrain/reims-vgpu em ambiente Linux..."
    if [[ ! -d "${SRC_CACHE}" ]]; then
        git clone https://github.com/steelbrain/reims-vgpu "${SRC_CACHE}"
    else
        git -C "${SRC_CACHE}" pull
    fi

    cd "${SRC_CACHE}"
    scripts/install-ctl.sh --yes --skip-qemu || true

    cp "${HOME}/.cargo/bin/reims-ctl" "${STAGE_DIR}/usr/bin/"
    cp "${HOME}/.cargo/bin/reims-util" "${STAGE_DIR}/usr/bin/"
    if [[ -d "${HOME}/.local/share/reims-ctl/qemu/current/bin" ]]; then
        cp -r "${HOME}/.local/share/reims-ctl/qemu/current/bin/"* "${STAGE_DIR}/usr/lib/reims/"
    fi
fi

# Ajusta permissões
chmod 755 "${STAGE_DIR}/DEBIAN"
chmod 755 "${STAGE_DIR}/usr/bin/"*
chmod 755 "${STAGE_DIR}/usr/lib/reims/"*

# Gera o pacote Debian
OUTPUT_DEB="${DIST_DIR}/reims-vgpu_0.1.0_amd64.deb"
python3 "${SCRIPT_DIR}/make_deb.py" "${STAGE_DIR}" "${OUTPUT_DEB}"

echo "==> Pacote reims-vgpu gerado com sucesso em: ${OUTPUT_DEB}"
