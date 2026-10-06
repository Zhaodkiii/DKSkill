#!/usr/bin/env bash

# Create empty feature requirement documents from module/feature paths.
# macOS ships Bash 3.2, so keep this script compatible with Bash 3 syntax.
set -eo pipefail

usage() {
  cat <<'USAGE'
Usage:
  create_feature_doc_files.sh --docs-root <total-docs-dir> [input options]

Input options (use one or more):
  --spec-file <file>  Read one document path per line.
  --feature <path>    Add one document path; may be repeated.
  --stdin             Read document paths from standard input.

Other options:
  --dry-run            Print planned changes without creating files.
  --help               Show this help.

Document path format:
  内容与公开分享/文件目录/文章管理
  内容与公开分享/文件目录/公开分享
  账号与认证/登录与会话.md

The final path is:
  <docs-root>/<document-path>.md

Parent directories are created as needed. Existing files are never overwritten.
USAGE
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

normalize_path() {
  local path="$1"
  path="${path%$'\r'}"
  path="$(trim "$path")"

  if [[ -z "$path" || "${path:0:1}" == "#" ]]; then
    return 1
  fi

  path="$(printf '%s' "$path" | sed -E 's/^[[:space:]]*([-*+]|[0-9]+[.)])[[:space:]]+//')"
  path="${path%%|*}"
  path="$(trim "$path")"
  path="${path%.md}"
  path="$(trim "$path")"

  [[ -n "$path" ]] || return 1
  printf '%s' "$path"
}

validate_path() {
  local path="$1"
  local segment
  local old_ifs="$IFS"
  IFS='/'
  for segment in $path; do
    if [[ -z "$segment" || "$segment" == "." || "$segment" == ".." || "$segment" == *"\\"* ]]; then
      IFS="$old_ifs"
      printf 'Invalid document path: %s\n' "$path" >&2
      printf 'Paths must stay under docs root and cannot contain empty, . or .. segments.\n' >&2
      return 1
    fi
  done
  IFS="$old_ifs"
}

contains_path() {
  local target="$1"
  local item
  for item in "${documents[@]}"; do
    [[ "$item" == "$target" ]] && return 0
  done
  return 1
}

add_document() {
  local raw="$1"
  local path

  if ! path="$(normalize_path "$raw")"; then
    return 0
  fi

  validate_path "$path"

  if contains_path "$path"; then
    printf 'DUPLICATE  %s.md\n' "$path" >&2
    return 0
  fi

  documents+=("$path")
}

docs_root=""
spec_file=""
read_stdin=false
dry_run=false
raw_documents=()
documents=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --docs-root)
      [[ $# -ge 2 ]] || { printf '%s\n' '--docs-root requires a value.' >&2; exit 2; }
      docs_root="$2"
      shift 2
      ;;
    --spec-file)
      [[ $# -ge 2 ]] || { printf '%s\n' '--spec-file requires a value.' >&2; exit 2; }
      spec_file="$2"
      shift 2
      ;;
    --feature)
      [[ $# -ge 2 ]] || { printf '%s\n' '--feature requires a value.' >&2; exit 2; }
      raw_documents+=("$2")
      shift 2
      ;;
    --stdin)
      read_stdin=true
      shift
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$docs_root" ]]; then
  printf '%s\n' 'Provide --docs-root.' >&2
  usage >&2
  exit 2
fi

if [[ -n "$spec_file" ]]; then
  if [[ ! -f "$spec_file" ]]; then
    printf 'Document spec file does not exist: %s\n' "$spec_file" >&2
    exit 2
  fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    add_document "$line"
  done < "$spec_file"
fi

for item in "${raw_documents[@]}"; do
  add_document "$item"
done

if [[ "$read_stdin" == true ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    add_document "$line"
  done
fi

if [[ ${#documents[@]} -eq 0 ]]; then
  printf '%s\n' 'No valid document paths were provided.' >&2
  usage >&2
  exit 2
fi

if [[ "$dry_run" == true ]]; then
  printf 'DRY RUN  docs root: %s\n' "$docs_root"
else
  mkdir -p -- "$docs_root"
  printf 'DOCS ROOT  %s\n' "$docs_root"
fi

created_count=0
existing_count=0
for item in "${documents[@]}"; do
  target="$docs_root/$item.md"
  parent="${target%/*}"

  if [[ -e "$target" && ! -f "$target" ]]; then
    printf 'CONFLICT  %s exists and is not a file.\n' "$target" >&2
    exit 1
  fi

  if [[ -f "$target" ]]; then
    printf 'EXISTS    %s\n' "$target"
    existing_count=$((existing_count + 1))
    continue
  fi

  if [[ "$dry_run" == true ]]; then
    printf 'CREATE    %s\n' "$target"
  else
    mkdir -p -- "$parent"
    : > "$target"
    printf 'CREATED   %s\n' "$target"
  fi
  created_count=$((created_count + 1))
done

printf 'SUMMARY   created=%d existing=%d requested=%d\n' "$created_count" "$existing_count" "${#documents[@]}"
