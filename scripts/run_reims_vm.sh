#!/usr/bin/env bash
# ==============================================================================
# ReimsOS VM Test Runner (QEMU)
# Executa a imagem ISO do ReimsOS em uma máquina virtual para teste local
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ISO_PATH="${1:-"${REPO_ROOT}/dist/iso/reims-os-24.04-amd64.iso"}"
RAM_MB="4096"
CPUS="4"
DISK_IMAGE="${REPO_ROOT}/build/test-disk.qcow2"
DRY_RUN=false

for arg in "$@"; do
    case "${arg}" in
        --dry-run)
            DRY_RUN=true
            ;;
    esac
done

echo "=================================================================="
echo "          ReimsOS: Inicialização de Teste em QEMU                 "
echo "=================================================================="

# Detecta acelerador de virtualização
ACCEL_ARGS=()
if [[ "$(uname -s)" == "Darwin" ]]; then
    ACCEL_ARGS+=("-accel" "hvf" "-cpu" "host")
elif [[ "$(uname -s)" == "Linux" ]] && [[ -e /dev/kvm ]] && [[ -r /dev/kvm ]] && [[ -w /dev/kvm ]]; then
    ACCEL_ARGS+=("-enable-kvm" "-cpu" "host")
else
    ACCEL_ARGS+=("-cpu" "qemu64")
fi

# Cria disco de teste de 20GB se não existir
mkdir -p "${REPO_ROOT}/build"
if [[ ! -f "${DISK_IMAGE}" ]] && [[ "${DRY_RUN}" != "true" ]]; then
    qemu-img create -f qcow2 "${DISK_IMAGE}" 20G || true
fi

CMD=(
    "qemu-system-x86_64"
    "${ACCEL_ARGS[@]}"
    "-m" "${RAM_MB}"
    "-smp" "${CPUS}"
    "-cdrom" "${ISO_PATH}"
    "-drive" "file=${DISK_IMAGE},format=qcow2,if=virtio"
    "-net" "nic,model=virtio"
    "-net" "user"
    "-vga" "virtio"
    "-display" "default,show-cursor=on"
    "-boot" "d"
)

if [[ "${DRY_RUN}" == "true" ]]; then
    echo "==> [MODO SIMULAÇÃO ATIVO]"
    echo "✓ Comando QEMU gerado com sucesso:"
    echo "${CMD[*]}"
    exit 0
fi

if ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
    echo "ERRO: qemu-system-x86_64 não está instalado no sistema!" >&2
    exit 1
fi

echo "==> Iniciando ReimsOS VM com ${RAM_MB}MB RAM e ${CPUS} vCPUs..."
exec "${CMD[@]}"
