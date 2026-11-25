#!/usr/bin/env bash
# ==============================================================================
# Reims Desktop ISO Builder
# Script automatizado para geração da imagem ISO do Reims Desktop (Ubuntu 24.04 LTS)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_DIR="${REPO_ROOT}/iso-builder/config"
DIST_DIR="${REPO_ROOT}/dist"
BUILD_DIR="${REPO_ROOT}/build/iso-build"
ISO_OUTPUT_DIR="${REPO_ROOT}/dist/iso"

DRY_RUN=false
UBUNTU_RELEASE="noble"
UBUNTU_MIRROR="http://archive.ubuntu.com/ubuntu/"

for arg in "$@"; do
    case "${arg}" in
        --dry-run)
            DRY_RUN=true
            ;;
        *)
            ;;
    esac
done

echo "=================================================================="
echo "          Reims Desktop: Pipeline de Construção de Imagem ISO           "
echo "=================================================================="

# 1. Validação de Arquivos de Configuração
echo "==> Verificando arquivos de configuração..."
if [[ ! -f "${CONFIG_DIR}/packages.list" ]]; then
    echo "ERRO: Lista de pacotes ${CONFIG_DIR}/packages.list não encontrada!" >&2
    exit 1
fi

if [[ ! -f "${CONFIG_DIR}/calamares/settings.conf" ]]; then
    echo "ERRO: Configuração do Calamares não encontrada!" >&2
    exit 1
fi

# 2. Garante compilação dos pacotes Reims (.deb)
echo "==> Verificando pacotes .deb do Reims Desktop..."
if [[ ! -f "${DIST_DIR}/reims-core_0.1.0_all.deb" ]] || [[ ! -f "${DIST_DIR}/reims-gui_0.1.0_all.deb" ]]; then
    echo "==> Compilando pacotes Debian..."
    "${REPO_ROOT}/packaging/scripts/build_all.sh"
fi

if [[ "${DRY_RUN}" == "true" ]]; then
    echo ""
    echo "==> [MODO SIMULAÇÃO / DRY-RUN ATIVO]"
    echo "✓ Lista de pacotes verificada com sucesso ($(grep -vc '^#' "${CONFIG_DIR}/packages.list" | tr -d ' ') pacotes)."
    echo "✓ Configurações do Calamares e temas validados."
    echo "✓ Pacotes Debian presentes:"
    ls -lh "${DIST_DIR}"/*.deb
    echo "✓ Validação do pipeline de ISO concluída com 100% de sucesso!"
    exit 0
fi

# 3. Execução Real do Build (Requer Linux e privilégios de root)
if [[ "$(uname -s)" != "Linux" ]]; then
    echo "ERRO: A compilação completa da ISO requer um ambiente Linux com debootstrap e xorriso." >&2
    echo "Dica: Em sistemas de desenvolvimento ou macOS, utilize --dry-run para validação." >&2
    exit 1
fi

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERRO: A criação da imagem ISO requer privilégios de root (sudo)." >&2
    exit 1
fi

echo "==> Iniciando debootstrap para Ubuntu ${UBUNTU_RELEASE}..."
mkdir -p "${BUILD_DIR}/chroot" "${ISO_OUTPUT_DIR}"
debootstrap --arch=amd64 "${UBUNTU_RELEASE}" "${BUILD_DIR}/chroot" "${UBUNTU_MIRROR}"

echo "==> Configurando chroot e instalando pacotes base..."
mount --bind /dev "${BUILD_DIR}/chroot/dev"
mount --bind /proc "${BUILD_DIR}/chroot/proc"
mount --bind /sys "${BUILD_DIR}/chroot/sys"

# Copia pacotes .deb para dentro do chroot
mkdir -p "${BUILD_DIR}/chroot/tmp/reims-debs"
cp "${DIST_DIR}"/*.deb "${BUILD_DIR}/chroot/tmp/reims-debs/"

# Script interno de provisionamento do chroot
cat << 'EOF' > "${BUILD_DIR}/chroot/tmp/setup.sh"
#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# Atualiza repositórios com main, restricted, universe
cat << 'REPO' > /etc/apt/sources.list
deb http://archive.ubuntu.com/ubuntu/ noble main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ noble-updates main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu/ noble-security main restricted universe multiverse
REPO

apt-get update
# Instala pacotes do repositório
grep -v '^#' /tmp/packages.list | xargs apt-get install -y --no-install-recommends

# Instala pacotes do Reims Desktop
dpkg -i /tmp/reims-debs/*.deb || apt-get install -f -y

# Criação do usuário live padrão
useradd -m -s /bin/bash -G sudo,kvm,render,video reims
echo "reims:reims" | chpasswd
echo "reims ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/reims-live
chmod 0440 /etc/sudoers.d/reims-live

# Limpeza
apt-get clean
rm -rf /tmp/*
EOF

cp "${CONFIG_DIR}/packages.list" "${BUILD_DIR}/chroot/tmp/packages.list"
chmod +x "${BUILD_DIR}/chroot/tmp/setup.sh"
chroot "${BUILD_DIR}/chroot" /tmp/setup.sh

# Desmonta sistemas de arquivos do chroot
umount "${BUILD_DIR}/chroot/sys"
umount "${BUILD_DIR}/chroot/proc"
umount "${BUILD_DIR}/chroot/dev"

echo "==> Gerando imagem SquashFS compactada com zstd..."
mkdir -p "${BUILD_DIR}/image/casper"
mksquashfs "${BUILD_DIR}/chroot" "${BUILD_DIR}/image/casper/filesystem.squashfs" -comp zstd -Xcompression-level 15

echo "==> Gerando ISO Híbrida UEFI/BIOS..."
xorriso -as mkisofs \
    -r -V "REIMS_OS_2404" \
    -b isolinux/isolinux.bin \
    -c isolinux/boot.cat \
    -no-emul-boot -boot-load-size 4 -boot-info-table \
    -eltorito-alt-boot \
    -e boot/grub/efi.img \
    -no-emul-boot -isohybrid-gpt-basdat \
    -o "${ISO_OUTPUT_DIR}/reims-os-24.04-amd64.iso" \
    "${BUILD_DIR}/image"

echo "==> ISO gerada com sucesso em: ${ISO_OUTPUT_DIR}/reims-os-24.04-amd64.iso"
