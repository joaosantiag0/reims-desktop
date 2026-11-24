#!/bin/bash
set -euo pipefail

echo "=================================================================="
echo "          Iniciando Pipeline de Remasterização do ReimsOS          "
echo "=================================================================="

# 1. Garante montagem de /dev/sda1
mkdir -p /mnt/installer
if ! mountpoint -q /mnt/installer; then
    echo "==> Montando /dev/sda1 em /mnt/installer..."
    mount /dev/sda1 /mnt/installer
fi

# 2. Executa a compilação dos pacotes .deb com assets atualizados
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"
echo "==> Compilando pacotes .deb com assets transparentes atualizados..."
./packaging/scripts/build_all.sh

# 3. Executa a remasterização gerando a ISO no NVMe (alta velocidade)
mkdir -p dist
OUTPUT_ISO="${SCRIPT_DIR}/dist/reims-os-custom.iso"
rm -f "${OUTPUT_ISO}"

echo "==> Executando remaster_iso.sh..."
./iso-builder/scripts/remaster_iso.sh /mnt/installer/reims-os.iso "${OUTPUT_ISO}"

if [[ ! -f "${OUTPUT_ISO}" ]]; then
    echo "ERRO: ISO remasterizada nao foi gerada em ${OUTPUT_ISO}!" >&2
    exit 1
fi

echo "==> Atualizando /mnt/installer/reims-os.iso com a nova imagem..."
cp -f "${OUTPUT_ISO}" /mnt/installer/reims-os.iso

echo "==> Atualizando vmlinuz e initrd na particao /dev/sda1..."
mkdir -p /tmp/remaster_iso_mnt
mount -o loop,ro /mnt/installer/reims-os.iso /tmp/remaster_iso_mnt
cp -vf /tmp/remaster_iso_mnt/casper/vmlinuz /mnt/installer/casper/vmlinuz
cp -vf /tmp/remaster_iso_mnt/casper/initrd /mnt/installer/casper/initrd
umount /tmp/remaster_iso_mnt
rmdir /tmp/remaster_iso_mnt

sync
echo "==> Remasterização concluída com 100% de sucesso!"
echo "REMASTER_COMPLETED_SUCCESSFULLY"
