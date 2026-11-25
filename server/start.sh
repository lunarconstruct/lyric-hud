#!/usr/bin/env bash
set -euo pipefail

server_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
web_dir="$server_dir/web"
python_bin="$server_dir/.venv/bin/python"
php_log="${TMPDIR:-/tmp}/lyric-hud-php-server.log"

if [[ ! -x "$python_bin" ]]; then
    printf 'Python environment not found at %s\n' "$python_bin" >&2
    printf 'Create it and install server/requirements.txt before starting lyric-hud.\n' >&2
    exit 1
fi

if ! command -v php >/dev/null 2>&1; then
    printf 'PHP is required to serve the web UI.\n' >&2
    exit 1
fi

printf 'Serving lyric-hud at http://localhost:8000\n'
printf 'PHP server output is being written to %s\n' "$php_log"

XDEBUG_MODE=off php -S localhost:8000 -t "$web_dir" >"$php_log" 2>&1 &
php_pid=$!

cleanup() {
    kill "$php_pid" 2>/dev/null || true
    wait "$php_pid" 2>/dev/null || true
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cd "$server_dir"
"$python_bin" main.py
