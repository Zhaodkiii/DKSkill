#!/usr/bin/env bash

# Create first-level feature documentation directories safely and idempotently.
# Avoid `nounset`: macOS ships Bash 3.2, which treats an empty array expansion as
# unset under `set -u` even when the array has been initialized intentionally.
set -eo pipefail

usage() {
  cat <<'USAGE'
Usage:
  create_feature_doc_dirs.sh --project-root <project> [input options]
  create_feature_doc_dirs.sh --docs-root <total-docs-dir> [input options]

Input options (use one or more):
  --features-file <file>  Read one feature per line.
  --feature <name>        Add one feature; may be repeated.
  --stdin                 Read feature lines from standard input.

Other options:
  --dry-run               Print planned changes without creating directories.
  --help                  Show this help.

Feature line format:
  登录与会话管理
  - 文件与 OSS
  3. 第二相机
  AI 设置 | 可选说明，脚本只使用竖线左侧的目录名
USAGE
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

normalize_feature_line() {
  local line="$1"
  line="${line%$'\r'}"
  line="$(trim "$line")"

  if [[ -z "$line" || "${line:0:1}" == "#" ]]; then
    return 1
  fi

  line="$(printf '%s' "$line" | sed -E 's/^[[:space:]]*([-*+]|[0-9]+[.)])[[:space:]]+//')"
  line="${line%%|*}"
  line="$(trim "$line")"

  [[ -n "$line" ]] || return 1
  printf '%s' "$line"
}

validate_feature_name() {
  local name="$1"
  if [[ "$name" == *"/"* || "$name" == *"\\"* || "$name" == "." || "$name" == ".." ]]; then
    printf 'Invalid feature directory name: %s\n' "$name" >&2
    printf 'Feature names must be a single directory name without slash or traversal segments.\n' >&2
    return 1
  fi
}

contains_feature() {
  local target="$1"
  local item
  for item in "${features[@]}"; do
    [[ "$item" == "$target" ]] && return 0
  done
  return 1
}

add_feature() {
  local raw="$1"
  local name

  if ! name="$(normalize_feature_line "$raw")"; then
    return 0
  fi

  validate_feature_name "$name"

  if contains_feature "$name"; then
    printf 'DUPLICATE  %s\n' "$name" >&2
    return 0
  fi

  features+=("$name")
}

project_root=""
docs_root=""
features_file=""
read_stdin=false
dry_run=false
raw_features=()
features=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-root)
      [[ $# -ge 2 ]] || { printf '%s\n' '--project-root requires a value.' >&2; exit 2; }
      project_root="$2"
      shift 2
      ;;
    --docs-root)
      [[ $# -ge 2 ]] || { printf '%s\n' '--docs-root requires a value.' >&2; exit 2; }
      docs_root="$2"
      shift 2
      ;;
    --features-file)
      [[ $# -ge 2 ]] || { printf '%s\n' '--features-file requires a value.' >&2; exit 2; }
      features_file="$2"
      shift 2
      ;;
    --feature)
      [[ $# -ge 2 ]] || { printf '%s\n' '--feature requires a value.' >&2; exit 2; }
      raw_features+=("$2")
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

if [[ -n "$project_root" && -n "$docs_root" ]]; then
  printf '%s\n' 'Use either --project-root or --docs-root, not both.' >&2
  exit 2
fi

if [[ -z "$docs_root" ]]; then
  if [[ -z "$project_root" ]]; then
    printf '%s\n' 'Provide --project-root or --docs-root.' >&2
    usage >&2
    exit 2
  fi
  if [[ ! -d "$project_root" ]]; then
    printf 'Project root does not exist or is not a directory: %s\n' "$project_root" >&2
    exit 2
  fi
  docs_root="$project_root/总领文档"
fi

if [[ -n "$features_file" ]]; then
  if [[ ! -f "$features_file" ]]; then
    printf 'Feature list file does not exist: %s\n' "$features_file" >&2
    exit 2
  fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    add_feature "$line"
  done < "$features_file"
fi

for item in "${raw_features[@]}"; do
  add_feature "$item"
done

if [[ "$read_stdin" == true ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    add_feature "$line"
  done
fi

if [[ ${#features[@]} -eq 0 ]]; then
  printf '%s\n' 'No valid feature names were provided.' >&2
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
for item in "${features[@]}"; do
  target="$docs_root/$item"
  if [[ -e "$target" && ! -d "$target" ]]; then
    printf 'CONFLICT  %s exists and is not a directory.\n' "$target" >&2
    exit 1
  fi

  if [[ -d "$target" ]]; then
    printf 'EXISTS    %s\n' "$target"
    existing_count=$((existing_count + 1))
    continue
  fi

  if [[ "$dry_run" == true ]]; then
    printf 'CREATE    %s\n' "$target"
  else
    mkdir -p -- "$target"
    printf 'CREATED   %s\n' "$target"
  fi
  created_count=$((created_count + 1))
done

printf 'SUMMARY   created=%d existing=%d requested=%d\n' "$created_count" "$existing_count" "${#features[@]}"
