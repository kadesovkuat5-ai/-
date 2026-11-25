#!/bin/bash
# Install the Kazakh-ready fonts in this folder for the current user (fontconfig, Chromium, ffmpeg/libass).
set -e
d="$(cd "$(dirname "$0")" && pwd)"
mkdir -p ~/.local/share/fonts/kazakh
cp "$d"/*.ttf ~/.local/share/fonts/kazakh/
fc-cache -f >/dev/null 2>&1 || true
