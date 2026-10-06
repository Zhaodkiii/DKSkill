#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 /path/to/article-directory-or-article.md [metadata options]" >&2
  exit 2
fi

INPUT_PATH="$1"
shift

if [ -d "$INPUT_PATH" ]; then
  MARKDOWN_PATH="$(find "$INPUT_PATH" -maxdepth 1 -type f -name '*.md' ! -name '*流程说明.md' ! -name 'README.md' | sort | head -n 1)"
  if [ -z "$MARKDOWN_PATH" ]; then
    echo "No Markdown file found in directory: $INPUT_PATH" >&2
    exit 2
  fi
elif [ -f "$INPUT_PATH" ]; then
  MARKDOWN_PATH="$INPUT_PATH"
else
  echo "Input path does not exist: $INPUT_PATH" >&2
  exit 2
fi

python3 - "$SCRIPT_DIR" <<'PY'
import importlib.util
import subprocess
import sys

try:
    import oss2  # noqa: F401
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "oss2"])

try:
    import pypinyin  # noqa: F401
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "pypinyin"])
PY

echo "Uploading local Markdown assets to OSS and rewriting links..." >&2
MANIFEST_PATH="$(python3 "$SCRIPT_DIR/upload_oss_assets.py" "$MARKDOWN_PATH" "$@" | python3 -c 'import json,sys; print(json.load(sys.stdin)["manifest"])')"

echo "Generating SparkService import SQL..." >&2
python3 "$SCRIPT_DIR/generate_spark_content_sql.py" "$MARKDOWN_PATH" --manifest "$MANIFEST_PATH" "$@"

echo "{\"status\":\"done\",\"markdown\":\"$MARKDOWN_PATH\",\"manifest\":\"$MANIFEST_PATH\"}"
