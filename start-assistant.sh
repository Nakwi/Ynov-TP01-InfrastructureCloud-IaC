#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSISTANT="$ROOT/terraform_assistant.py"

if [ ! -f "$ASSISTANT" ]; then
    echo "terraform_assistant.py introuvable dans $ROOT" >&2
    exit 1
fi

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1 && python --version 2>&1 | grep -q '^Python 3\.'; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    read -r -p "Python 3 est absent. L'installer maintenant ? [Y/n] " answer
    answer="${answer:-Y}"
    case "$answer" in
        y|Y|o|O)
            if command -v apt-get >/dev/null 2>&1; then
                sudo apt-get update
                sudo apt-get install -y python3
                PYTHON_BIN="python3"
            elif command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y python3
                PYTHON_BIN="python3"
            elif command -v yum >/dev/null 2>&1; then
                sudo yum install -y python3
                PYTHON_BIN="python3"
            elif command -v pacman >/dev/null 2>&1; then
                sudo pacman -Sy --noconfirm python
                PYTHON_BIN="python3"
            else
                echo "Gestionnaire de paquets non reconnu. Installe Python 3 puis relance." >&2
                exit 1
            fi
            ;;
        *)
            echo "Python 3 est requis pour lancer l'assistant." >&2
            exit 1
            ;;
    esac
fi

cd "$ROOT"
exec "$PYTHON_BIN" "$ASSISTANT" --auto "$@"
