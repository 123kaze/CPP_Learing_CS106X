#!/usr/bin/env bash
set -euo pipefail

WALLPAPER="/home/kaze123/Project/CPP_Learing_CS106X/IMG_2328.JPG"
PTYXIS_PROFILE="$(gsettings get org.gnome.Ptyxis default-profile-uuid | tr -d "'")"
PTYXIS_PATH="/org/gnome/Ptyxis/Profiles/${PTYXIS_PROFILE}/"

if [[ ! -f "$WALLPAPER" ]]; then
  echo "Wallpaper not found: $WALLPAPER" >&2
  exit 1
fi

pick_font() {
  if fc-match "JetBrainsMono Nerd Font" | grep -qi "JetBrains"; then
    printf "JetBrainsMono Nerd Font 12"
  elif fc-match "FiraCode Nerd Font" | grep -qi "Fira"; then
    printf "FiraCode Nerd Font 12"
  else
    printf "Monospace 12"
  fi
}

MONO_FONT="$(pick_font)"

gsettings set org.gnome.desktop.background picture-uri "file://${WALLPAPER}"
if gsettings list-keys org.gnome.desktop.background | grep -qx picture-uri-dark; then
  gsettings set org.gnome.desktop.background picture-uri-dark "file://${WALLPAPER}"
fi
gsettings set org.gnome.desktop.background picture-options 'zoom'

gsettings set org.gnome.desktop.interface gtk-theme 'Yaru-purple-dark'
gsettings set org.gnome.desktop.interface icon-theme 'Yaru-purple'
gsettings set org.gnome.desktop.interface cursor-theme 'Yaru'
gsettings set org.gnome.desktop.interface monospace-font-name "$MONO_FONT"
gsettings set org.gnome.desktop.interface show-battery-percentage true
gsettings set org.gnome.desktop.interface enable-animations true

gsettings set org.gnome.Ptyxis interface-style 'dark'
gsettings set org.gnome.Ptyxis use-system-font false
gsettings set org.gnome.Ptyxis font-name "$MONO_FONT"
gsettings set org.gnome.Ptyxis default-columns 100
gsettings set org.gnome.Ptyxis default-rows 30
gsettings set org.gnome.Ptyxis.Profile:"${PTYXIS_PATH}" palette 'Ubuntu'
gsettings set org.gnome.Ptyxis.Profile:"${PTYXIS_PATH}" opacity 0.84
gsettings set org.gnome.Ptyxis.Profile:"${PTYXIS_PATH}" bold-is-bright true
gsettings set org.gnome.Ptyxis.Profile:"${PTYXIS_PATH}" cell-height-scale 1.08

if gsettings list-schemas | grep -qx org.gnome.shell.extensions.dash-to-dock; then
  gsettings set org.gnome.shell.extensions.dash-to-dock dock-position 'BOTTOM'
  gsettings set org.gnome.shell.extensions.dash-to-dock extend-height false
  gsettings set org.gnome.shell.extensions.dash-to-dock dock-fixed true
  gsettings set org.gnome.shell.extensions.dash-to-dock dash-max-icon-size 34
  gsettings set org.gnome.shell.extensions.dash-to-dock transparency-mode 'FIXED'
  gsettings set org.gnome.shell.extensions.dash-to-dock background-opacity 0.24
  gsettings set org.gnome.shell.extensions.dash-to-dock running-indicator-style 'DOTS'
fi

mkdir -p "$HOME/.config/fastfetch"
cat > "$HOME/.config/fastfetch/config.jsonc" <<'JSON'
{
  "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
  "logo": {
    "type": "auto",
    "source": "ubuntu",
    "padding": {
      "top": 1,
      "right": 2
    }
  },
  "display": {
    "separator": " -> ",
    "color": {
      "keys": "yellow",
      "title": "green"
    }
  },
  "modules": [
    "title",
    "separator",
    "os",
    "kernel",
    "packages",
    "shell",
    "de",
    "wm",
    "terminal",
    "terminalfont",
    "cpu",
    "gpu",
    "memory",
    "disk",
    "display",
    "uptime",
    "weather"
  ]
}
JSON

echo "Applied pink GNOME look with transparent Ptyxis profile ${PTYXIS_PROFILE}."
