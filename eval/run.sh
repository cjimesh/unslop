#!/usr/bin/env bash
# Regenerate output.md for every case with the current skill, then score.
# Usage: run.sh [cases_dir] [model]    defaults: cases, sonnet
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cases="${1:-$here/cases}"
model="${2:-sonnet}"
for dir in "$cases"/*/; do
  [ -f "$dir/type" ] || continue
  echo "running $(basename "$dir")" >&2
  claude -p --model "$model" "/unslop $(cat "$dir/input.md")" < /dev/null 2>/dev/null > "$dir/output.md"
done
python3 "$here/score.py" "$cases"
