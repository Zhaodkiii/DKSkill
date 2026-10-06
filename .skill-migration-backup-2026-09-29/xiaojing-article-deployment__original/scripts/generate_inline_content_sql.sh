#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 /path/to/article.md /path/to/oss-manifest.json [metadata options]" >&2
  exit 2
fi

MARKDOWN_PATH="$1"
MANIFEST_PATH="$2"
shift 2

python3 "$SCRIPT_DIR/generate_spark_content_sql.py" \
  "$MARKDOWN_PATH" \
  --manifest "$MANIFEST_PATH" \
  --inline-content \
  "$@"
