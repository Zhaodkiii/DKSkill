#!/usr/bin/env bash

# Create one module-level requirement stub and list its sub-features inside it.
# Existing documents are preserved. Compatible with macOS Bash 3.2.
set -eo pipefail

usage() {
  cat <<'USAGE'
Usage:
  create_module_doc_stubs.sh --docs-root <total-docs-dir> [input options]

Input options (use one or more):
  --spec-file <file>  Read one module specification per line.
  --module <spec>     Add one module specification; may be repeated.
  --stdin             Read module specifications from standard input.

Other options:
  --dry-run            Print planned changes without creating files.
  --force              Regenerate an existing module document.
  --help               Show this help.

Specification format:
  会话与认证 | Apple 登录；验证码登录；设备游客账号；会话恢复与退出
  内容与公开分享 | 文件目录；文章发布；公开分享
  OCR

The final document path is:
  <docs-root>/<module>/<module>需求.md

  The right side is written as module sections inside the module document.
USAGE
}

trim() {
  local value="$1"
  printf '%s' "$value" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//'
}

normalize_module() {
  local raw="$1"
  local module
  module="${raw%$'\r'}"
  module="${module%%|*}"
  while [[ "$module" == " "* ]]; do module="${module# }"; done
  while [[ "$module" == *" " ]]; do module="${module% }"; done
  [[ -n "$module" ]] || return 1
  printf '%s' "$module"
}

normalize_features() {
  local raw="$1"
  local features
  features="${raw#*|}"
  printf '%s' "$features"
}

validate_module() {
  local module="$1"
  local segment
  local old_ifs="$IFS"
  IFS='/'
  for segment in $module; do
    if [[ -z "$segment" || "$segment" == "." || "$segment" == ".." || "$segment" == *"\\"* ]]; then
      IFS="$old_ifs"
      printf 'Invalid module directory name: %s\n' "$module" >&2
      return 1
    fi
  done
  IFS="$old_ifs"
}

contains_module() {
  local target="$1"
  local item
  for item in "${modules[@]}"; do
    [[ "$item" == "$target" ]] && return 0
  done
  return 1
}

add_module() {
  local raw="$1"
  local module

  if ! module="$(normalize_module "$raw")"; then
    return 0
  fi
  validate_module "$module"

  if contains_module "$module"; then
    printf 'DUPLICATE  %s\n' "$module" >&2
    return 0
  fi

  modules+=("$module")
  specs+=("$raw")
}

docs_root=""
spec_file=""
read_stdin=false
dry_run=false
force=false
raw_modules=()
modules=()
specs=()

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
    --module)
      [[ $# -ge 2 ]] || { printf '%s\n' '--module requires a value.' >&2; exit 2; }
      raw_modules+=("$2")
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
    --force)
      force=true
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
    printf 'Module spec file does not exist: %s\n' "$spec_file" >&2
    exit 2
  fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    add_module "$line"
  done < "$spec_file"
fi

for item in "${raw_modules[@]}"; do
  add_module "$item"
done

if [[ "$read_stdin" == true ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    add_module "$line"
  done
fi

if [[ ${#modules[@]} -eq 0 ]]; then
  printf '%s\n' 'No valid module specifications were provided.' >&2
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
for index in "${!modules[@]}"; do
  module="${modules[$index]}"
  spec="${specs[$index]}"
  module_leaf="${module##*/}"
  target="$docs_root/$module/${module_leaf}需求.md"
  parent="${target%/*}"

  if [[ -e "$target" && ! -f "$target" ]]; then
    printf 'CONFLICT  %s exists and is not a file.\n' "$target" >&2
    exit 1
  fi

  if [[ -f "$target" && "$force" != true ]]; then
    printf 'EXISTS    %s\n' "$target"
    existing_count=$((existing_count + 1))
    continue
  fi

  if [[ "$dry_run" == true ]]; then
    printf 'CREATE    %s\n' "$target"
    continue
  fi

  mkdir -p -- "$parent"
  {
    printf '# %s需求\n\n' "$module_leaf"
    printf '## 一、模块目标\n\n'
    printf '## 二、%s模块结构\n\n' "$module_leaf"
    printf '## 三、功能模块\n\n'
    feature_text="$(normalize_features "$spec")"
    while [[ "$feature_text" == " "* ]]; do feature_text="${feature_text# }"; done
    while [[ "$feature_text" == *" " ]]; do feature_text="${feature_text% }"; done
    if [[ -n "$feature_text" ]]; then
      feature_index=1
      while IFS= read -r feature || [[ -n "$feature" ]]; do
        while [[ "$feature" == " "* ]]; do feature="${feature# }"; done
        while [[ "$feature" == *" " ]]; do feature="${feature% }"; done
        [[ -n "$feature" ]] || continue
        anchor="${feature// /-}"
        printf '### 3.%d [%s](#%s)\n\n' "$feature_index" "$feature" "$anchor"
        printf '#### 需求说明\n\n'
        printf '#### 基础要求\n\n'
        printf '#### 验收标准\n\n'
        printf '#### 技术细节与设计代码位置\n\n'
        feature_index=$((feature_index + 1))
      done <<EOF
$(printf '%s\n' "$feature_text" | awk -F '[；、,]' '{ for (i = 1; i <= NF; i++) if ($i ~ /[^[:space:]]/) print $i }')
EOF
    else
      printf '### 3.1 功能模块\n\n'
      printf '#### 需求说明\n\n'
      printf '#### 基础要求\n\n'
      printf '#### 验收标准\n\n'
      printf '#### 技术细节与设计代码位置\n\n'
    fi
    printf '## 四、整体业务流程\n\n'
    printf '## 五、状态模型\n\n'
    printf '## 六、数据与持久化\n\n'
    printf '## 七、错误模型\n\n'
    printf '## 八、与其他模块的接口边界\n\n'
    printf '## 九、关键代码对应关系\n\n'
    printf '## 十、测试策略\n\n'
    printf '## 十一、当前实现、缺口与演进\n\n'
    printf '## 十二、整体验收标准\n\n'
  } > "$target"
  if [[ "$force" == true && -f "$target" ]]; then
    printf 'UPDATED   %s\n' "$target"
  else
    printf 'CREATED   %s\n' "$target"
  fi
  created_count=$((created_count + 1))
done

printf 'SUMMARY   created=%d existing=%d requested=%d\n' "$created_count" "$existing_count" "${#modules[@]}"
