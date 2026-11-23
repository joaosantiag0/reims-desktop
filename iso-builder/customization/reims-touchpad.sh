#!/bin/sh
# Ativa toque para clicar (tap-to-click) em todos os touchpads
if which xinput >/dev/null 2>&1; then
    for id in $(xinput list --id-only 2>/dev/null); do
        # Ativa Tapping se suportado pelo dispositivo
        prop=$(xinput list-props "$id" 2>/dev/null | grep -i "libinput Tapping Enabled (" | head -n1 | awk -F'[()]' '{print $2}')
        if [ -n "$prop" ]; then
            xinput set-prop "$id" "$prop" 1 2>/dev/null || true
        fi

        # Ativa Tapping Drag (arrastar ao tocar duas vezes)
        drag_prop=$(xinput list-props "$id" 2>/dev/null | grep -i "libinput Tapping Drag Enabled (" | head -n1 | awk -F'[()]' '{print $2}')
        if [ -n "$drag_prop" ]; then
            xinput set-prop "$id" "$drag_prop" 1 2>/dev/null || true
        fi

        # Configura Click Method para clickfinger (1 dedo = clique esquerdo, 2 dedos = clique direito)
        click_prop=$(xinput list-props "$id" 2>/dev/null | grep -i "libinput Click Method Enabled (" | head -n1 | awk -F'[()]' '{print $2}')
        if [ -n "$click_prop" ]; then
            xinput set-prop "$id" "$click_prop" 0 1 2>/dev/null || true
        fi
    done
fi
