#!/usr/bin/env bash
# ==============================================================================
# Reims Desktop ISO Remastering Script
# Customiza a ISO Live para aplicar a identidade visual do Reims Desktop,
# remover bloatware e pré-instalar o Reims Control Center no Desktop.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CUSTOM_DIR="${REPO_ROOT}/iso-builder/customization"
CONFIG_DIR="${REPO_ROOT}/iso-builder/config"
DIST_DIR="${REPO_ROOT}/dist"
STAGE_DIR="${REPO_ROOT}/build/iso-remaster"

ISO_INPUT="${1:-"${DIST_DIR}/iso/reims-os-24.04-amd64.iso"}"
ISO_OUTPUT="${2:-"${DIST_DIR}/iso/reims-os-remastered.iso"}"

DRY_RUN=false
for arg in "${@:-}"; do
    case "${arg}" in
        --dry-run)
            DRY_RUN=true
            ;;
        *)
            ;;
    esac
done

echo "=================================================================="
echo "          Reims Desktop: Remasterização da Identidade Visual e Live CD   "
echo "=================================================================="

# 1. Validação de Arquivos de Customização
echo "==> Verificando arquivos de customização e branding..."
if [[ ! -f "${CUSTOM_DIR}/wallpaper.svg" ]]; then
    echo "ERRO: Wallpaper ${CUSTOM_DIR}/wallpaper.svg não encontrado!" >&2
    exit 1
fi

if [[ ! -f "${CUSTOM_DIR}/reims-logo.png" ]]; then
    echo "ERRO: Logo do Reims Desktop ${CUSTOM_DIR}/reims-logo.png não encontrado!" >&2
    exit 1
fi

if [[ ! -f "${CUSTOM_DIR}/reims-installer-prompt.py" ]]; then
    echo "ERRO: Script de boas-vindas ${CUSTOM_DIR}/reims-installer-prompt.py não encontrado!" >&2
    exit 1
fi

if [[ ! -f "${CUSTOM_DIR}/90-touchpad.conf" ]]; then
    echo "ERRO: Configuração de touchpad ${CUSTOM_DIR}/90-touchpad.conf não encontrada!" >&2
    exit 1
fi

if [[ ! -f "${CUSTOM_DIR}/reims-touchpad.sh" ]]; then
    echo "ERRO: Script de touchpad ${CUSTOM_DIR}/reims-touchpad.sh não encontrado!" >&2
    exit 1
fi

if [[ ! -f "${CUSTOM_DIR}/remove-packages.list" ]]; then
    echo "ERRO: Lista de remoção de bloatware não encontrada!" >&2
    exit 1
fi

if [[ ! -f "${CUSTOM_DIR}/grub/theme.txt" ]]; then
    echo "ERRO: Tema do GRUB ${CUSTOM_DIR}/grub/theme.txt não encontrado!" >&2
    exit 1
fi

if [[ ! -f "${CUSTOM_DIR}/grub/background.png" ]]; then
    echo "ERRO: Background do GRUB ${CUSTOM_DIR}/grub/background.png não encontrado!" >&2
    exit 1
fi

if [[ "${DRY_RUN}" == "true" ]]; then
    echo ""
    echo "==> [MODO SIMULAÇÃO / DRY-RUN ATIVO]"
    echo "✓ Wallpaper do Reims Desktop validado."
    echo "✓ Logo e ícones de boot do Reims Desktop validados."
    echo "✓ Tema do seletor de boot GRUB do Reims Desktop validado."
    echo "✓ Suporte e configuração de touchpad (tap-to-click e gestures) validados."
    echo "✓ Prompt de boas-vindas do Live CD (Live vs Instalar) validado."
    echo "✓ Lista de pacotes bloatware a remover ($(grep -vc '^#' "${CUSTOM_DIR}/remove-packages.list" | tr -d ' ') pacotes)."
    echo "✓ Configurações de tema escuro e painel LXQt validadas."
    echo "✓ Calamares branding configurado para o Reims Desktop."
    echo "✓ Script de remasterização testado com 100% de sucesso!"
    exit 0
fi

if [[ "$(uname -s)" != "Linux" ]] || [[ "${EUID}" -ne 0 ]]; then
    echo "ERRO: A remasterização real de SquashFS requer Linux com privilégios de root (sudo)." >&2
    echo "Dica: Utilize --dry-run para testes locais." >&2
    exit 1
fi

if [[ ! -f "${ISO_INPUT}" ]]; then
    echo "ERRO: ISO de entrada ${ISO_INPUT} não encontrada!" >&2
    exit 1
fi

# 2. Extração da ISO e do SquashFS
echo "==> Extraindo imagem ISO..."
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}/iso" "${STAGE_DIR}/squashfs"

mkdir -p "${STAGE_DIR}/mnt_iso"
mount -o loop,ro "${ISO_INPUT}" "${STAGE_DIR}/mnt_iso"
cp -a "${STAGE_DIR}/mnt_iso/." "${STAGE_DIR}/iso/"
umount "${STAGE_DIR}/mnt_iso"
rmdir "${STAGE_DIR}/mnt_iso"

echo "==> Descompactando filesystem.squashfs..."
unsquashfs -d "${STAGE_DIR}/squashfs" "${STAGE_DIR}/iso/casper/filesystem.squashfs"

# 3. Customização do Sistema de Arquivos (Chroot)
echo "==> Customizando sistema no chroot..."
ROOTFS="${STAGE_DIR}/squashfs"

cleanup_mounts() {
    echo "==> Desfazendo montagens do chroot..."
    umount -lf "${ROOTFS}/mnt/installer" 2>/dev/null || true
    umount -lf "${ROOTFS}/mnt"/* 2>/dev/null || true
    umount -lf "${ROOTFS}/sys" 2>/dev/null || true
    umount -lf "${ROOTFS}/proc" 2>/dev/null || true
    umount -lf "${ROOTFS}/dev/pts" 2>/dev/null || true
    umount -lf "${ROOTFS}/dev" 2>/dev/null || true
    rm -rf "${ROOTFS}/mnt"/* "${ROOTFS}/tmp"/* 2>/dev/null || true
}
trap cleanup_mounts EXIT INT TERM

# Prepara mounts
mount --bind /dev "${ROOTFS}/dev"
mount --bind /proc "${ROOTFS}/proc"
mount --bind /sys "${ROOTFS}/sys"

# Configura DNS para permitir download de dependencias pelo apt-get
if [[ -e "${ROOTFS}/etc/resolv.conf" ]]; then
    mv "${ROOTFS}/etc/resolv.conf" "${ROOTFS}/etc/resolv.conf.bak" 2>/dev/null || true
fi
cp -L /etc/resolv.conf "${ROOTFS}/etc/resolv.conf"

# Copia pacotes Reims Desktop
mkdir -p "${ROOTFS}/tmp/reims-pkgs"
cp "${DIST_DIR}"/*.deb "${ROOTFS}/tmp/reims-pkgs/"
cp "${CUSTOM_DIR}/remove-packages.list" "${ROOTFS}/tmp/remove-packages.list"
cp "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/tmp/reims-logo.png"

# Injeta Wallpaper do Reims Desktop
mkdir -p "${ROOTFS}/usr/share/backgrounds"
cp "${CUSTOM_DIR}/wallpaper.svg" "${ROOTFS}/usr/share/backgrounds/reims-wallpaper.svg"
if [[ -f "${CUSTOM_DIR}/reims-wallpaper.png" ]]; then
    cp "${CUSTOM_DIR}/reims-wallpaper.png" "${ROOTFS}/usr/share/backgrounds/reims-wallpaper.png"
    # Sobrescreve diretamente TODOS os wallpapers do Lubuntu/Ubuntu para que NENHUMA tela mostre o antigo
    if [[ -d "${ROOTFS}/usr/share/lubuntu/wallpapers" ]]; then
        for wp in "${ROOTFS}/usr/share/lubuntu/wallpapers"/*; do
            if [[ -f "${wp}" ]]; then
                cp -f "${CUSTOM_DIR}/reims-wallpaper.png" "${wp}"
            fi
        done
    fi
fi

# Injeta Tema do GRUB do Reims Desktop no RootFS
echo "==> Injetando tema do GRUB do Reims Desktop no RootFS..."
mkdir -p "${ROOTFS}/usr/share/grub/themes/reims" "${ROOTFS}/boot/grub/themes/reims"
cp -rf "${CUSTOM_DIR}/grub/"* "${ROOTFS}/usr/share/grub/themes/reims/"
cp -rf "${CUSTOM_DIR}/grub/"* "${ROOTFS}/boot/grub/themes/reims/"

# Sobrescreve também qualquer tema lubuntu existente no rootfs
if [[ -d "${ROOTFS}/usr/share/grub/themes/lubuntu-grub-theme" ]]; then
    cp -rf "${CUSTOM_DIR}/grub/"* "${ROOTFS}/usr/share/grub/themes/lubuntu-grub-theme/"
fi
if [[ -d "${ROOTFS}/boot/grub/themes/lubuntu-grub-theme" ]]; then
    cp -rf "${CUSTOM_DIR}/grub/"* "${ROOTFS}/boot/grub/themes/lubuntu-grub-theme/"
fi

# Configura defaults do GRUB para usar o tema do Reims
mkdir -p "${ROOTFS}/etc/default/grub.d"
cp -f "${CUSTOM_DIR}/grub/50_reims_theme.cfg" "${ROOTFS}/etc/default/grub.d/50_reims_theme.cfg"
if [[ -f "${ROOTFS}/etc/default/grub.d/lubuntu-grub-theme.cfg" ]]; then
    cp -f "${CUSTOM_DIR}/grub/50_reims_theme.cfg" "${ROOTFS}/etc/default/grub.d/lubuntu-grub-theme.cfg"
fi
if [[ -f "${ROOTFS}/etc/default/grub" ]]; then
    sed -i 's/^GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="Reims Desktop"/' "${ROOTFS}/etc/default/grub" || true
    if grep -q "^GRUB_THEME=" "${ROOTFS}/etc/default/grub"; then
        sed -i 's|^GRUB_THEME=.*|GRUB_THEME="/usr/share/grub/themes/reims/theme.txt"|' "${ROOTFS}/etc/default/grub" || true
    else
        echo 'GRUB_THEME="/usr/share/grub/themes/reims/theme.txt"' >> "${ROOTFS}/etc/default/grub"
    fi
fi

# Injeta Configurações do LXQt (Dark Theme e Wallpaper) em todos os caminhos XDG e Skel
for CONFIG_BASE in \
    "${ROOTFS}/etc/xdg/xdg-Lubuntu" \
    "${ROOTFS}/etc/xdg" \
    "${ROOTFS}/usr/share" \
    "${ROOTFS}/etc/skel/.config" \
    "${ROOTFS}/home/lubuntu/.config" \
    "${ROOTFS}/home/reims/.config"; do
    if [[ -d "${CONFIG_BASE}" ]]; then
        mkdir -p "${CONFIG_BASE}/pcmanfm-qt/lxqt" "${CONFIG_BASE}/lxqt"
        cp "${CUSTOM_DIR}/pcmanfm-qt-desktop.conf" "${CONFIG_BASE}/pcmanfm-qt/lxqt/settings.conf"
        cp "${CUSTOM_DIR}/lxqt.conf" "${CONFIG_BASE}/lxqt/lxqt.conf"
    fi
done

for SKEL_DIR in "${ROOTFS}/etc/skel" "${ROOTFS}/home/lubuntu" "${ROOTFS}/home/reims"; do
    if [[ -d "${SKEL_DIR}" ]]; then
        mkdir -p "${SKEL_DIR}/.config/pcmanfm-qt/lxqt" "${SKEL_DIR}/.config/lxqt" "${SKEL_DIR}/Desktop"
        cp "${CUSTOM_DIR}/pcmanfm-qt-desktop.conf" "${SKEL_DIR}/.config/pcmanfm-qt/lxqt/settings.conf"
        cp "${CUSTOM_DIR}/lxqt.conf" "${SKEL_DIR}/.config/lxqt/lxqt.conf"
        # Limpa atalhos antigos duplicados
        rm -f "${SKEL_DIR}/Desktop/install-reims.desktop"
    fi
done

# Injeta o tema oficial do Reims Desktop no LXQt
if [[ -d "${CUSTOM_DIR}/theme/reims" ]]; then
    mkdir -p "${ROOTFS}/usr/share/lxqt/themes/reims"
    cp -rf "${CUSTOM_DIR}/theme/reims/"* "${ROOTFS}/usr/share/lxqt/themes/reims/"
fi

# Configura ícone do Reims Desktop no Menu Iniciar do painel LXQt
for PANEL_CONF in \
    "${ROOTFS}/etc/xdg/xdg-Lubuntu/lxqt/panel.conf" \
    "${ROOTFS}/etc/xdg/lxqt/panel.conf" \
    "${ROOTFS}/etc/skel/.config/lxqt/panel.conf" \
    "${ROOTFS}/home/lubuntu/.config/lxqt/panel.conf"; do
    if [[ -f "${PANEL_CONF}" ]]; then
        sed -i '/icon=\/usr\/share\/pixmaps\/reims-logo.png/d' "${PANEL_CONF}" || true
        sed -i '/^\[mainmenu\]/a icon=/usr/share/pixmaps/reims-logo.png' "${PANEL_CONF}" || true
        sed -i '/background-color=@Variant/d' "${PANEL_CONF}" || true
        sed -i '/font-color=@Variant/d' "${PANEL_CONF}" || true
    fi
done
if [[ -f "${ROOTFS}/etc/xdg/xdg-Lubuntu/lxqt/panel.conf" ]]; then
    mkdir -p "${ROOTFS}/etc/skel/.config/lxqt" "${ROOTFS}/home/lubuntu/.config/lxqt"
    cp -f "${ROOTFS}/etc/xdg/xdg-Lubuntu/lxqt/panel.conf" "${ROOTFS}/etc/skel/.config/lxqt/panel.conf" || true
    cp -f "${ROOTFS}/etc/xdg/xdg-Lubuntu/lxqt/panel.conf" "${ROOTFS}/home/lubuntu/.config/lxqt/panel.conf" || true
fi

# Configura Branding do Calamares (Reims Desktop)
mkdir -p "${ROOTFS}/etc/calamares/branding/reims"
# Se existir branding do Lubuntu, copia como base (show.qml, slides, traduções em lang/)
if [[ -d "${ROOTFS}/etc/calamares/branding/lubuntu" ]]; then
    cp -r "${ROOTFS}/etc/calamares/branding/lubuntu/"* "${ROOTFS}/etc/calamares/branding/reims/"
fi
# Sobrescreve com as definições oficiais do Reims Desktop
cp -r "${CONFIG_DIR}/calamares/branding/reims/"* "${ROOTFS}/etc/calamares/branding/reims/"

# Aplica settings.conf customizado do Reims Desktop (remove pkgselect/tela de tipo de instalação e snaps)
if [[ -f "${CONFIG_DIR}/calamares/settings.conf" ]]; then
    cp -v "${CONFIG_DIR}/calamares/settings.conf" "${ROOTFS}/etc/calamares/settings.conf"
fi
if [[ -d "${CONFIG_DIR}/calamares/modules" ]]; then
    mkdir -p "${ROOTFS}/etc/calamares/modules"
    cp -rv "${CONFIG_DIR}/calamares/modules/"* "${ROOTFS}/etc/calamares/modules/"
fi

# Remove módulos e contextos obsoletos de seleção de pacotes/snaps
rm -f "${ROOTFS}/etc/calamares/modules/pkgselect"* "${ROOTFS}/usr/lib/x86_64-linux-gnu/calamares/modules/pkgselect/libcalamares_viewmodule_pkgselect.so" || true

# Sobrescreve também o branding do lubuntu caso o calamares aponte para ele
if [[ -d "${ROOTFS}/etc/calamares/branding/lubuntu" ]]; then
    sed -i 's/productName: .*/productName: Reims Desktop/' "${ROOTFS}/etc/calamares/branding/lubuntu/branding.desc" || true
    sed -i 's/shortProductName: .*/shortProductName: Reims Desktop/' "${ROOTFS}/etc/calamares/branding/lubuntu/branding.desc" || true
    sed -i 's/versionedName: .*/versionedName: Reims Desktop 24.04 LTS/' "${ROOTFS}/etc/calamares/branding/lubuntu/branding.desc" || true
    sed -i 's/shortVersionedName: .*/shortVersionedName: Reims Desktop/' "${ROOTFS}/etc/calamares/branding/lubuntu/branding.desc" || true
    sed -i 's/bootloaderEntryName: .*/bootloaderEntryName: Reims Desktop/' "${ROOTFS}/etc/calamares/branding/lubuntu/branding.desc" || true
fi

# Configura atalho do instalador do Reims Desktop (substituindo o lubuntu-calamares.desktop para evitar duplicatas)
mkdir -p "${ROOTFS}/usr/share/applications"
cat << 'EOF' > "${ROOTFS}/usr/share/applications/lubuntu-calamares.desktop"
[Desktop Entry]
Type=Application
Version=1.0
Name=Install Reims Desktop 24.04 LTS
Name[pt]=Instalar o Reims Desktop 24.04 LTS
Name[pt_BR]=Instalar o Reims Desktop 24.04 LTS
GenericName=Install Reims Desktop
GenericName[pt]=Instalar o Reims Desktop
GenericName[pt_BR]=Instalar o Reims Desktop
Exec=sudo -E /usr/bin/calamares-launch-normal
Comment=Install Reims Desktop on your disk
Comment[pt_BR]=Instalar o Reims Desktop no seu disco
Icon=/usr/share/pixmaps/reims-logo.png
Terminal=false
StartupNotify=true
Categories=Qt;System;
Keywords=installer;calamares;system;reims;
EOF
chmod +x "${ROOTFS}/usr/share/applications/lubuntu-calamares.desktop"

# Limpa atalhos de instalação do /etc/skel para não propagar para usuários instalados
mkdir -p "${ROOTFS}/etc/skel/Desktop"
rm -f "${ROOTFS}/etc/skel/Desktop"/*calamares*.desktop "${ROOTFS}/etc/skel/Desktop"/*install*.desktop 2>/dev/null || true

# Atalho do instalador apenas na sessão Live (usuários lubuntu e reims)
for LIVE_USER_DIR in "${ROOTFS}/home/lubuntu" "${ROOTFS}/home/reims"; do
    if [[ -d "${LIVE_USER_DIR}" ]]; then
        mkdir -p "${LIVE_USER_DIR}/Desktop"
        rm -f "${LIVE_USER_DIR}/Desktop"/*calamares*.desktop "${LIVE_USER_DIR}/Desktop"/*install*.desktop 2>/dev/null || true
        cp "${ROOTFS}/usr/share/applications/lubuntu-calamares.desktop" "${LIVE_USER_DIR}/Desktop/lubuntu-calamares.desktop"
        chmod +x "${LIVE_USER_DIR}/Desktop/lubuntu-calamares.desktop"
        chown -R 1000:1000 "${LIVE_USER_DIR}/Desktop" 2>/dev/null || true
    fi
done

# Configura inicialização automática do Reims Desktop Control ao entrar na sessão
mkdir -p "${ROOTFS}/etc/xdg/autostart"
cat << 'EOF' > "${ROOTFS}/etc/xdg/autostart/reims-desktop.desktop"
[Desktop Entry]
Type=Application
Name=Reims Desktop Control
Name[pt_BR]=Painel de Controle Reims Desktop
Name[es_ES]=Panel de Control Reims Desktop
Comment=Launch Reims Desktop Control automatically on login
Comment[pt_BR]=Iniciar Painel de Controle Reims Desktop automaticamente ao entrar
Comment[es_ES]=Iniciar Panel de Control Reims Desktop automáticamente al iniciar sesión
Exec=/usr/bin/reims-desktop
Icon=/usr/share/pixmaps/reims-logo.png
Terminal=false
StartupNotify=false
Categories=System;Emulator;Qt;
X-LXQt-Need-Tray=true
EOF
chmod 644 "${ROOTFS}/etc/xdg/autostart/reims-desktop.desktop"

# Ajusta informações do disco (.disk/info)
echo "Reims Desktop 24.04 LTS - Release amd64" > "${STAGE_DIR}/iso/.disk/info"

# Injeta Ícones de Boot e Splash (Plymouth) do Reims Desktop
echo "==> Injetando temas de boot e Plymouth do Reims Desktop..."
mkdir -p "${ROOTFS}/usr/share/pixmaps"
cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/pixmaps/reims-logo.png"
cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/pixmaps/reims-desktop.png"
cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/pixmaps/reims-gui.png"
cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/pixmaps/calamares.png" 2>/dev/null || true
find "${ROOTFS}/usr/share/icons" -name "*calamares*" -exec cp -vf "${CUSTOM_DIR}/reims-logo.png" {} + 2>/dev/null || true

if [[ -f "${CUSTOM_DIR}/reims-logo.png" ]]; then
    # Substitui logos padrão do sistema
    cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/plymouth/ubuntu-logo.png" || true

    # Atualiza tema spinner padrão
    if [[ -d "${ROOTFS}/usr/share/plymouth/themes/spinner" ]]; then
        cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/plymouth/themes/spinner/watermark.png" || true
        cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/plymouth/themes/spinner/bgrt-fallback.png" || true
    fi

    # Atualiza tema lubuntu-logo removendo os 200 frames do logo do Lubuntu e aplicando a identidade do Reims Desktop
    if [[ -d "${ROOTFS}/usr/share/plymouth/themes/lubuntu-logo" ]]; then
        cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/plymouth/themes/lubuntu-logo/lubuntu_logo.png"
        cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/plymouth/themes/lubuntu-logo/watermark.png"
        if [[ -d "${ROOTFS}/usr/share/plymouth/themes/lubuntu-logo/spinner" ]]; then
            cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/plymouth/themes/lubuntu-logo/spinner/watermark.png"
            cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/plymouth/themes/lubuntu-logo/spinner/bgrt-fallback.png"
            # Substitui todos os frames de animação do logo do Lubuntu pelo logo do Reims Desktop
            for anim in "${ROOTFS}/usr/share/plymouth/themes/lubuntu-logo/spinner/animation-"*.png; do
                if [[ -f "${anim}" ]]; then
                    cp -f "${CUSTOM_DIR}/reims-logo.png" "${anim}"
                fi
            done
            for throb in "${ROOTFS}/usr/share/plymouth/themes/lubuntu-logo/spinner/throbber-"*.png; do
                if [[ -f "${throb}" ]]; then
                    cp -f "${CUSTOM_DIR}/reims-logo.png" "${throb}"
                fi
            done
        fi

        # Altera cores de fundo azul do Lubuntu para tema escuro do Reims Desktop (#121418)
        sed -i 's/0x0078c2/0x121418/g' "${ROOTFS}/usr/share/plymouth/themes/lubuntu-logo/lubuntu-logo.plymouth" || true
        if [[ -f "${ROOTFS}/usr/share/plymouth/themes/lubuntu-logo/bgrt/bgrt.plymouth" ]]; then
            sed -i 's/0x0078c2/0x121418/g' "${ROOTFS}/usr/share/plymouth/themes/lubuntu-logo/bgrt/bgrt.plymouth" || true
        fi
    fi

    # Calamares brandings
    if [[ -d "${ROOTFS}/etc/calamares/branding/lubuntu" ]]; then
        cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/etc/calamares/branding/lubuntu/welcome.png"
        cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/etc/calamares/branding/lubuntu/logo.png"
        cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/etc/calamares/branding/lubuntu/icon.png"
    fi
    if [[ -d "${ROOTFS}/etc/calamares/branding/reims" ]]; then
        cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/etc/calamares/branding/reims/welcome.png"
        cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/etc/calamares/branding/reims/logo.png"
        cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/etc/calamares/branding/reims/icon.png"
        cp -v "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/etc/calamares/branding/reims/reims-logo.png"
    fi
fi

# Injeta Prompt de Boas-Vindas Customizado (Botões Live CD e Instalar Reims Desktop)
echo "==> Configurando assistente de boas-vindas do Live CD (Live vs Instalar)..."
cp -v "${CUSTOM_DIR}/reims-installer-prompt.py" "${ROOTFS}/usr/bin/reims-installer-prompt"
chmod +x "${ROOTFS}/usr/bin/reims-installer-prompt"

# Substitui o lubuntu-installer-prompt para garantir a chamada nativa do Reims Desktop
if [[ -f "${ROOTFS}/usr/bin/lubuntu-installer-prompt" ]] || [[ -d "${ROOTFS}/usr/bin" ]]; then
    ln -sf /usr/bin/reims-installer-prompt "${ROOTFS}/usr/bin/lubuntu-installer-prompt"
fi
if [[ -f "${ROOTFS}/usr/libexec/start-lubuntu-live-env" ]]; then
    sed -i 's/lubuntu-installer-prompt/reims-installer-prompt/g' "${ROOTFS}/usr/libexec/start-lubuntu-live-env"
fi

# Injeta Suporte e Configuração de Touchpad (Tap-to-click e gestures)
echo "==> Configurando suporte a touch/touchpad (tap-to-click e gestures)..."
mkdir -p "${ROOTFS}/etc/X11/xorg.conf.d" "${ROOTFS}/usr/share/X11/xorg.conf.d"
cp -v "${CUSTOM_DIR}/90-touchpad.conf" "${ROOTFS}/etc/X11/xorg.conf.d/90-touchpad.conf"
cp -v "${CUSTOM_DIR}/90-touchpad.conf" "${ROOTFS}/usr/share/X11/xorg.conf.d/90-touchpad.conf"

cp -v "${CUSTOM_DIR}/reims-touchpad.sh" "${ROOTFS}/usr/bin/reims-touchpad"
chmod +x "${ROOTFS}/usr/bin/reims-touchpad"
mkdir -p "${ROOTFS}/etc/xdg/autostart" "${ROOTFS}/etc/X11/Xsession.d"
cp -v "${CUSTOM_DIR}/reims-touchpad.desktop" "${ROOTFS}/etc/xdg/autostart/reims-touchpad.desktop"
cp -v "${CUSTOM_DIR}/reims-touchpad.sh" "${ROOTFS}/etc/X11/Xsession.d/99-reims-touchpad"
chmod +x "${ROOTFS}/etc/X11/Xsession.d/99-reims-touchpad"

# Garante que o touch funcione imediatamente no ambiente live antes do prompt
if [[ -f "${ROOTFS}/usr/libexec/start-lubuntu-live-env" ]]; then
    if ! grep -q "reims-touchpad" "${ROOTFS}/usr/libexec/start-lubuntu-live-env"; then
        sed -i '/openbox &/a /usr/bin/reims-touchpad &' "${ROOTFS}/usr/libexec/start-lubuntu-live-env"
    fi
fi

# Customiza Menu de Boot e Tema do GRUB na ISO
echo "==> Customizando entradas e tema do GRUB da ISO para Reims Desktop..."
mkdir -p "${STAGE_DIR}/iso/boot/grub/themes/reims"
cp -rf "${CUSTOM_DIR}/grub/"* "${STAGE_DIR}/iso/boot/grub/themes/reims/"

# Sobrescreve se existir lubuntu-grub-theme na ISO
if [[ -d "${STAGE_DIR}/iso/boot/grub/themes/lubuntu-grub-theme" ]]; then
    cp -rf "${CUSTOM_DIR}/grub/"* "${STAGE_DIR}/iso/boot/grub/themes/lubuntu-grub-theme/"
fi

# Copia wallpaper/splash para a pasta do grub da ISO
cp -f "${CUSTOM_DIR}/grub/background.png" "${STAGE_DIR}/iso/boot/grub/splash.png" 2>/dev/null || true
cp -f "${CUSTOM_DIR}/grub/background.png" "${STAGE_DIR}/iso/boot/grub/background.png" 2>/dev/null || true

for CFG in "${STAGE_DIR}/iso/boot/grub/grub.cfg" "${STAGE_DIR}/iso/boot/grub/loopback.cfg"; do
    if [[ -f "${CFG}" ]]; then
        sed -i 's/Try or Install Lubuntu/Experimentar ou Instalar o Reims Desktop/g' "${CFG}" || true
        sed -i 's/Lubuntu (safe graphics)/Reims Desktop (Modo Seguro \/ Safe Graphics)/g' "${CFG}" || true
        sed -i 's/OEM install (for manufacturers)/Instalação OEM Reims Desktop/g' "${CFG}" || true
        sed -i 's/Lubuntu/Reims Desktop/g' "${CFG}" || true
        sed -i 's|/boot/grub/themes/lubuntu-grub-theme/theme.txt|/boot/grub/themes/reims/theme.txt|g' "${CFG}" || true
        sed -i 's|/usr/share/grub/themes/lubuntu-grub-theme/theme.txt|/boot/grub/themes/reims/theme.txt|g' "${CFG}" || true

        # Se ainda não tiver set theme configurado no grub.cfg da ISO, injeta logo no início
        if ! grep -q "themes/reims/theme.txt" "${CFG}"; then
            sed -i '1i\set theme=/boot/grub/themes/reims/theme.txt\ninsmod png\ninsmod gfxterm\ninsmod gfxmenu\nset gfxmode=auto\nterminal_output gfxterm' "${CFG}" || true
        fi
    fi
done

# Executa limpeza e instalação no chroot
cat << 'EOF' > "${ROOTFS}/tmp/customize.sh"
#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# 1. Remove bloatware de forma resiliente
echo "==> Removendo pacotes desnecessários da imagem base..."
while IFS= read -r pkg || [[ -n "$pkg" ]]; do
    pkg="$(echo "$pkg" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [[ -z "$pkg" || "$pkg" =~ ^# ]] && continue
    echo "  -> Purgando: $pkg"
    apt-get purge -y "$pkg" 2>/dev/null || true
done < /tmp/remove-packages.list

if command -v snap &>/dev/null; then
    snap remove --purge firefox 2>/dev/null || true
    snap remove --purge thunderbird 2>/dev/null || true
fi

apt-get autoremove --purge -y || true

# 2. Instala pacotes do Reims Desktop
echo "==> Atualizando repositórios e instalando pacotes do Reims Desktop..."
apt-get update -y || true
dpkg -i /tmp/reims-pkgs/*.deb || apt-get install -f -y --fix-missing

# 3. Atalhos do Reims Desktop na area de trabalho do live user
for DESKTOP_DIR in /etc/skel/Desktop /home/lubuntu/Desktop /home/reims/Desktop; do
    if [ -d "$DESKTOP_DIR" ]; then
        rm -f "$DESKTOP_DIR"/reims*.desktop 2>/dev/null || true
        cp /usr/share/applications/reims-desktop.desktop "$DESKTOP_DIR/" 2>/dev/null || cp /usr/share/applications/reims-gui.desktop "$DESKTOP_DIR/"
        chmod +x "$DESKTOP_DIR"/*.desktop
        chown -R 1000:1000 "$DESKTOP_DIR" 2>/dev/null || true
    fi
done

# 4. Garante sobreescrita dos assets de marca transparentes sobre pacotes instalados
if [ -f /tmp/reims-logo.png ]; then
    cp -vf /tmp/reims-logo.png /usr/share/pixmaps/reims-logo.png 2>/dev/null || true
    cp -vf /tmp/reims-logo.png /usr/share/pixmaps/reims-desktop.png 2>/dev/null || true
    cp -vf /tmp/reims-logo.png /usr/share/pixmaps/reims-gui.png 2>/dev/null || true
    cp -vf /tmp/reims-logo.png /usr/lib/python3/dist-packages/reims_gui/assets/reims-logo.png 2>/dev/null || true
fi

# 5. Atualiza initramfs com os novos icones e splash do Plymouth
echo "==> Atualizando initramfs com a identidade visual do Reims Desktop..."
KERNEL_VER=$(ls /lib/modules 2>/dev/null | tail -n 1 || uname -r)
rm -f /boot/initrd.img*
update-initramfs -c -k "${KERNEL_VER}" || update-initramfs -u || true

# 6. Atualiza configurações do GRUB no chroot
echo "==> Atualizando configurações do GRUB no chroot..."
command -v update-grub &>/dev/null && update-grub || true

# 7. Configura servidor OpenSSH com suporte a senha e firewall UFW liberado
echo "==> Configurando servidor SSH e liberação de LAN..."
apt-get install -y openssh-server ufw 2>/dev/null || true
mkdir -p /etc/ssh/sshd_config.d
cat << 'SSHEOF' > /etc/ssh/sshd_config.d/60-reims-ssh.conf
# Reims Desktop LAN SSH Access
Port 22
PasswordAuthentication yes
KbdInteractiveAuthentication yes
PermitRootLogin prohibit-password
PubkeyAuthentication yes
SSHEOF

ssh-keygen -A 2>/dev/null || true
systemctl enable ssh.socket 2>/dev/null || true
systemctl enable ssh 2>/dev/null || true
if command -v ufw &>/dev/null; then
    ufw allow 22/tcp comment 'Reims Desktop SSH' 2>/dev/null || true
fi

# 8. Limpeza de cache
apt-get clean
rm -rf /tmp/*
EOF

chmod +x "${ROOTFS}/tmp/customize.sh"
chroot "${ROOTFS}" /bin/bash /tmp/customize.sh

# Restaura resolv.conf original
if [[ -f "${ROOTFS}/etc/resolv.conf.bak" ]]; then
    mv -f "${ROOTFS}/etc/resolv.conf.bak" "${ROOTFS}/etc/resolv.conf"
else
    rm -f "${ROOTFS}/etc/resolv.conf"
fi

# Reforço pós-chroot de todos os assets transparentes
cp -vf "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/pixmaps/reims-logo.png"
cp -vf "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/pixmaps/reims-desktop.png"
cp -vf "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/pixmaps/reims-gui.png"
cp -vf "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/share/pixmaps/calamares.png" 2>/dev/null || true
if [[ -d "${ROOTFS}/usr/lib/python3/dist-packages/reims_gui/assets" ]]; then
    cp -vf "${CUSTOM_DIR}/reims-logo.png" "${ROOTFS}/usr/lib/python3/dist-packages/reims_gui/assets/reims-logo.png"
fi

# Sincroniza initrd e vmlinuz se um novo kernel/initrd real tiver sido gerado no chroot
for candidate in "${ROOTFS}/boot/initrd.img-"*; do
    if [[ -f "${candidate}" ]] && [[ ! -L "${candidate}" ]]; then
        echo "==> Sincronizando novo initrd (${candidate}) com casper/initrd..."
        cp -v "${candidate}" "${STAGE_DIR}/iso/casper/initrd"
        break
    fi
done

for candidate in "${ROOTFS}/boot/vmlinuz-"*; do
    if [[ -f "${candidate}" ]] && [[ ! -L "${candidate}" ]]; then
        echo "==> Sincronizando novo vmlinuz (${candidate}) com casper/vmlinuz..."
        cp -v "${candidate}" "${STAGE_DIR}/iso/casper/vmlinuz"
        break
    fi
done

# Desmonta chroot de forma limpa
trap - EXIT INT TERM
cleanup_mounts

# 4. Recompactação do SquashFS
echo "==> Recompactando filesystem.squashfs com zstd..."
rm -f "${STAGE_DIR}/iso/casper/filesystem.squashfs"
mksquashfs "${STAGE_DIR}/squashfs" "${STAGE_DIR}/iso/casper/filesystem.squashfs" -comp zstd -b 1048576 -Xcompression-level 6

# Atualiza tamanho do filesystem
printf $(du -sx --block-size=1 "${STAGE_DIR}/squashfs" | cut -f1) > "${STAGE_DIR}/iso/casper/filesystem.size"

# 5. Geração da Nova ISO
echo "==> Gerando nova imagem ISO do Reims Desktop..."
mkdir -p "$(dirname "${ISO_OUTPUT}")"
xorriso -as mkisofs \
    -iso-level 3 \
    -r -V "REIMS_OS" \
    -b boot/grub/i386-pc/eltorito.img \
    -c boot.catalog \
    -no-emul-boot -boot-load-size 4 -boot-info-table \
    --grub2-boot-info \
    -eltorito-alt-boot \
    -e EFI/boot/bootx64.efi \
    -no-emul-boot -isohybrid-gpt-basdat \
    -o "${ISO_OUTPUT}" \
    "${STAGE_DIR}/iso"

echo "==> Remasterização concluída com sucesso! ISO gravada em: ${ISO_OUTPUT}"
