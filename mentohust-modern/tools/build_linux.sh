#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace_root="$(cd "$project_root/.." && pwd)"
venv_root="$workspace_root/.build-venv-linux"
python="$venv_root/bin/python"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This script builds Linux packages on a Linux host." >&2
  exit 1
fi

if [[ ! -x "$python" ]] || ! "$python" -c 'import sys; raise SystemExit(sys.version_info < (3, 12))' >/dev/null 2>&1; then
  python3 -m venv "$venv_root"
fi

"$python" -m pip install --upgrade pip
"$python" -m pip install -e "$project_root[build]"
"$python" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --onedir \
  --name "MentoHUST Modern" \
  --distpath "$workspace_root/dist" \
  --workpath "$workspace_root/build/pyinstaller-linux" \
  --specpath "$workspace_root" \
  --paths "$project_root/src" \
  --add-data "$project_root/src/mentohust_modern/assets:mentohust_modern/assets" \
  --add-data "$workspace_root/Ruijie Supplicant:Ruijie Supplicant" \
  --collect-submodules scapy \
  --collect-all PIL \
  --collect-all ttkbootstrap \
  "$project_root/launcher.py"

"$python" -m PyInstaller \
  --noconfirm \
  --clean \
  --console \
  --onedir \
  --name "mentohust-modern-cli" \
  --distpath "$workspace_root/dist" \
  --workpath "$workspace_root/build/pyinstaller-linux-cli" \
  --specpath "$workspace_root" \
  --paths "$project_root/src" \
  --add-data "$workspace_root/Ruijie Supplicant:Ruijie Supplicant" \
  --collect-submodules scapy \
  --exclude-module tkinter \
  --exclude-module PIL \
  --exclude-module ttkbootstrap \
  --exclude-module pystray \
  "$project_root/launcher_cli.py"
