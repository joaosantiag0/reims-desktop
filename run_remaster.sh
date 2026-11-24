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

echo "==> Copiando ISO para a raiz do SSD (/reims-os.iso no nvme0n1p2)..."
cp -f "${OUTPUT_ISO}" /reims-os.iso

echo "==> Atualizando /etc/grub.d/40_custom com opção de boot direto do SSD..."
cat << 'EOF' > /etc/grub.d/40_custom
#!/bin/sh
exec tail -n +3 $0

# ReimsOS Live Installer (Direto do SSD nvme0n1p2 - Alta Velocidade)
menuentry "Instalar ReimsOS (Direto do SSD - Alta Velocidade)" --class reims --class gnu-linux {
    insmod part_gpt
    insmod ext2
    insmod loopback
    search --no-floppy --fs-uuid --set=root c4613fcf-5953-482a-9202-9da73f43191e
    set isofile="/reims-os.iso"
    loopback loop $isofile
    linux (loop)/casper/vmlinuz boot=casper iso-scan/filename=$isofile noprompt noeject quiet splash ---
    initrd (loop)/casper/initrd
}

# ReimsOS Live Installer (Sem Pendrive - Boot Direto do Disco sda1)
menuentry "Instalar ReimsOS (Sem Pendrive - Boot Direto do Disco sda1)" --class reims --class gnu-linux {
    insmod part_gpt
    insmod fat
    insmod loopback
    search --no-floppy --fs-uuid --set=root 43D3-471B
    set isofile="/reims-os.iso"
    loopback loop $isofile
    linux (loop)/casper/vmlinuz boot=casper iso-scan/filename=$isofile noprompt noeject quiet splash ---
    initrd (loop)/casper/initrd
}

menuentry "Instalar ReimsOS (Modo Seguro / Safe Graphics)" --class reims --class gnu-linux {
    insmod part_gpt
    insmod ext2
    insmod loopback
    search --no-floppy --fs-uuid --set=root c4613fcf-5953-482a-9202-9da73f43191e
    set isofile="/reims-os.iso"
    loopback loop $isofile
    linux (loop)/casper/vmlinuz boot=casper iso-scan/filename=$isofile nomodeset noprompt noeject quiet splash ---
    initrd (loop)/casper/initrd
}

# GParted Live a partir do ISO no HDD (sda1)
menuentry "GParted Live (ISO no HDD) - redimensionar SSD" {
    insmod part_gpt
    insmod fat
    insmod loopback
    search --no-floppy --fs-uuid --set=root 43D3-471B
    set isofile="/gparted-live.iso"
    loopback loop $isofile
    linux (loop)/live/vmlinuz boot=live union=overlay username=user config components loglevel=3 noswap net.ifnames=0 nosplash findiso=$isofile ocs_1_cpu_udev scsi_mod.use_blk_mq=0 nvme.poll_queues=1
    initrd (loop)/live/initrd.img
}

# OpenCore (Hackintosh)
menuentry "OpenCore (Hackintosh)" {
    insmod part_gpt
    insmod fat
    search --no-floppy --file /EFI/OC/OpenCore.efi --set=root
    chainloader /EFI/OC/OpenCore.efi
}
EOF
chmod +x /etc/grub.d/40_custom
echo "==> Atualizando menu do GRUB no SSD (update-grub)..."
update-grub

echo "==> Atualizando vmlinuz, initrd, filesystem.squashfs e bootloader EFI na particao /dev/sda1..."
mkdir -p /tmp/remaster_iso_mnt
mount -o loop,ro /mnt/installer/reims-os.iso /tmp/remaster_iso_mnt
cp -vf /tmp/remaster_iso_mnt/casper/vmlinuz /mnt/installer/casper/vmlinuz
cp -vf /tmp/remaster_iso_mnt/casper/initrd /mnt/installer/casper/initrd
cp -vf /tmp/remaster_iso_mnt/casper/filesystem.* /mnt/installer/casper/
cp -rf /tmp/remaster_iso_mnt/EFI /mnt/installer/
cp -rf /tmp/remaster_iso_mnt/.disk /mnt/installer/

# Atualiza tema e menu do GRUB diretamente na particao do instalador (/dev/sda1)
mkdir -p /mnt/installer/boot/grub/themes/reims
cp -rf "${SCRIPT_DIR}/iso-builder/customization/grub/"* /mnt/installer/boot/grub/themes/reims/ 2>/dev/null || true
if [[ -d "/mnt/installer/boot/grub/themes/lubuntu-grub-theme" ]]; then
    cp -rf "${SCRIPT_DIR}/iso-builder/customization/grub/"* /mnt/installer/boot/grub/themes/lubuntu-grub-theme/ 2>/dev/null || true
fi
cp -vf "${SCRIPT_DIR}/iso-builder/customization/grub/background.png" /mnt/installer/boot/grub/splash.png 2>/dev/null || true
cp -vf "${SCRIPT_DIR}/iso-builder/customization/grub/background.png" /mnt/installer/boot/grub/background.png 2>/dev/null || true

for CFG in /mnt/installer/boot/grub/grub.cfg /mnt/installer/boot/grub/loopback.cfg; do
    if [[ -f "${CFG}" ]]; then
        sed -i 's/Try or Install Lubuntu/Experimentar ou Instalar o Reims Desktop/g' "${CFG}" || true
        sed -i 's/Lubuntu (safe graphics)/Reims Desktop (Modo Seguro \/ Safe Graphics)/g' "${CFG}" || true
        sed -i 's/OEM install (for manufacturers)/Instalação OEM Reims Desktop/g' "${CFG}" || true
        sed -i 's/Lubuntu/Reims Desktop/g' "${CFG}" || true
        sed -i 's|/boot/grub/themes/lubuntu-grub-theme/theme.txt|/boot/grub/themes/reims/theme.txt|g' "${CFG}" || true
        sed -i 's|/usr/share/grub/themes/lubuntu-grub-theme/theme.txt|/boot/grub/themes/reims/theme.txt|g' "${CFG}" || true
        if ! grep -q "themes/reims/theme.txt" "${CFG}"; then
            sed -i '1i\set theme=/boot/grub/themes/reims/theme.txt\ninsmod png\ninsmod gfxterm\ninsmod gfxmenu\nset gfxmode=auto\nterminal_output gfxterm' "${CFG}" || true
        fi
    fi
done

umount /tmp/remaster_iso_mnt
rmdir /tmp/remaster_iso_mnt

sync
echo "==> Remasterização concluída com 100% de sucesso!"
echo "REMASTER_COMPLETED_SUCCESSFULLY"
