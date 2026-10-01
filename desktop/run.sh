#!/usr/bin/env bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ ! -d "$DIR/.venv" ]; then
    echo "Creating virtual environment in $DIR/.venv..."
    python3 -m venv "$DIR/.venv"
    "$DIR/.venv/bin/pip" install -r "$DIR/requirements.txt"
fi

"$DIR/.venv/bin/python" "$DIR/main.py"
