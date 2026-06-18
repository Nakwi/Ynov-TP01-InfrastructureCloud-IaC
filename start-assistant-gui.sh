#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUI="$ROOT/terraform_gui.py"

if [ ! -f "$GUI" ]; then
    echo "terraform_gui.py introuvable dans $ROOT" >&2
    exit 1
fi

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1 && python --version 2>&1 | grep -q '^Python 3\.'; then
    PYTHON_BIN="python"
fi

install_python_tk() {
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-tk
        PYTHON_BIN="python3"
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y python3 python3-tkinter
        PYTHON_BIN="python3"
    elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y python3 python3-tkinter
        PYTHON_BIN="python3"
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm python tk
        PYTHON_BIN="python3"
    else
        echo "Gestionnaire de paquets non reconnu. Installe Python 3 et Tkinter puis relance." >&2
        exit 1
    fi
}

if [ -z "$PYTHON_BIN" ]; then
    read -r -p "Python 3 est absent. L'installer maintenant ? [Y/n] " answer
    answer="${answer:-Y}"
    case "$answer" in
        y|Y|o|O) install_python_tk ;;
        *)
            echo "Python 3 est requis pour lancer l'interface graphique." >&2
            exit 1
            ;;
    esac
fi

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import tkinter
PY
then
    read -r -p "Tkinter est absent. L'installer maintenant ? [Y/n] " answer
    answer="${answer:-Y}"
    case "$answer" in
        y|Y|o|O) install_python_tk ;;
        *)
            echo "Tkinter est requis pour lancer l'interface graphique." >&2
            exit 1
            ;;
    esac
fi

cd "$ROOT"
exec "$PYTHON_BIN" "$GUI" "$@"
