#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-}"

if [[ -z "${PROJECT_ROOT}" ]]; then
  echo "Usage: $0 /path/to/HarmonyOS/project" >&2
  exit 2
fi

if [[ ! -d "${PROJECT_ROOT}" ]]; then
  echo "Project path does not exist: ${PROJECT_ROOT}" >&2
  exit 1
fi

cd "${PROJECT_ROOT}"

echo "# HarmonyOS Project Build Doctor"
echo
echo "Project: ${PROJECT_ROOT}"
echo

echo "## Root Files"
for f in build-profile.json5 oh-package.json5 AppScope/app.json5 hvigorfile.ts local.properties; do
  if [[ -f "${f}" ]]; then
    echo "- found ${f}"
  else
    echo "- missing ${f}"
  fi
done
echo

if [[ -f AppScope/app.json5 ]]; then
  echo "## AppScope"
  rg -n '"bundleName"|"bundleType"|"versionName"|"versionCode"|"icon"|"label"' AppScope/app.json5 || true
  echo
fi

if [[ -f build-profile.json5 ]]; then
  echo "## Modules From build-profile.json5"
  rg -n '"name"|"srcPath"|"signingConfigs"|"signingConfig"|"compatibleSdkVersion"|"targetSdkVersion"' build-profile.json5 || true
  echo
fi

echo "## Entry Modules"
entry_count=0
entry_names=()
while IFS= read -r module_file; do
  if rg -q '"type"\s*:\s*"entry"' "${module_file}"; then
    entry_count=$((entry_count + 1))
    entry_name="$(rg -m 1 '"name"\s*:' "${module_file}" | sed -E 's/.*"name"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' || true)"
    if [[ -n "${entry_name}" ]]; then
      entry_names+=("${entry_name}")
    fi
    echo "- ${module_file}"
    rg -n '"name"|"type"|"mainElement"|"srcEntry"|"installationFree"|"actions"|"entities"|"icon"|"label"' "${module_file}" || true
  fi
done < <(find . -path '*/src/main/module.json5' -type f | sort)

if [[ "${entry_count}" -eq 0 ]]; then
  echo "- no entry module detected"
fi
echo

echo "## DevEco Run Configuration"
if [[ -f .idea/workspace.xml ]]; then
  rg -n 'RunManager|selected="Application|configuration name=.*(OhosDebugTask|HotReLoadTask)|MODULE_NAME|LAUNCH_ABILITY_CONFIG_TYPE|MULTI_HAP_MODULE_DATA|DEPLOY_MULTI_HAP|ALL_MODULES|HOT_RELOAD_MODULE_NAME' .idea/workspace.xml || true
else
  echo "- .idea/workspace.xml not found"
fi
echo

echo "## Hvigor Recent Errors"
if [[ -f .hvigor/outputs/build-logs/build.log ]]; then
  rg -n '\[ERROR\]|ERROR|error|failed|fatal|No signingConfig|Local dependencies|shouldDeduplicateHar|deploy|install|SignHap|PackageHap' .hvigor/outputs/build-logs/build.log | tail -n 80 || true
else
  echo "- .hvigor/outputs/build-logs/build.log not found"
fi
echo

echo "## Quick Interpretation"
if [[ -f AppScope/app.json5 ]] && rg -q '"bundleName"\s*:\s*"([^"]*xxxxxx|com\.atomicservice\.xxxxxx)"' AppScope/app.json5; then
  project_name="$(basename "${PROJECT_ROOT}")"
  echo "- FIX: AppScope uses a placeholder bundleName. Change it to cn.ZhaoDK.${project_name}."
fi

if [[ -f AppScope/app.json5 ]] && rg -q '"bundleType"\s*:\s*"atomicService"' AppScope/app.json5; then
  echo "- FIX: AppScope declares bundleType=atomicService. For local normal-app debugging, remove it so launcher label/icon behavior matches SupportClientHuawei."
fi

if [[ "${entry_count}" -gt 0 ]]; then
  echo "- Detected entry module name(s): ${entry_names[*]}"
fi

if [[ -f .idea/workspace.xml ]]; then
  selected_app="$(rg -o 'selected="Application\.[^"]+"' .idea/workspace.xml | sed -E 's/selected="Application\.([^"]+)"/\1/' | head -n 1 || true)"
  if [[ -n "${selected_app}" && "${entry_count}" -gt 0 ]]; then
    selected_is_entry=false
    for entry_name in "${entry_names[@]}"; do
      if [[ "${selected_app}" == "${entry_name}" ]]; then
        selected_is_entry=true
      fi
    done
    if [[ "${selected_is_entry}" == "false" ]]; then
      echo "- FIX: Selected run configuration is Application.${selected_app}, but detected entry module name(s) are: ${entry_names[*]}. Set RunManager selected to Application.<entry module name>."
    fi
  fi
fi

if [[ -f .idea/workspace.xml ]] && rg -q '<DEPLOY_MULTI_HAP>true</DEPLOY_MULTI_HAP>' .idea/workspace.xml && rg -q '<MULTI_HAP_MODULE_DATA>\[\]</MULTI_HAP_MODULE_DATA>' .idea/workspace.xml; then
  echo "- FIX: Multi-HAP deploy is enabled with an empty module list. Set DEPLOY_MULTI_HAP=false for initial startup."
fi

if [[ -f .idea/workspace.xml ]] && rg -q 'selected="Application\.([^"]*(pay|address|home|find|mine|detail|license|others)[^"]*)"' .idea/workspace.xml; then
  echo "- FIX: The selected run configuration points at a feature/service module. Switch it to the detected entry module."
fi

while IFS= read -r module_file; do
  if rg -q '"type"\s*:\s*"entry"' "${module_file}" && rg -q '"installationFree"\s*:\s*true' "${module_file}"; then
    echo "- FIX: Entry module ${module_file} has installationFree=true. For normal installed app debugging, set installationFree=false."
  fi
  if rg -q '"type"\s*:\s*"entry"' "${module_file}" && rg -q '"action\.system\.home"' "${module_file}"; then
    echo "- FIX: Entry module ${module_file} uses action.system.home. For this template workflow, align with SupportClientHuawei and use ohos.want.action.home."
  fi
done < <(find . -path '*/src/main/module.json5' -type f | sort)

if [[ -f .hvigor/outputs/build-logs/build.log ]] && rg -q 'No signingConfig found' .hvigor/outputs/build-logs/build.log; then
  echo "- Signing config is missing or skipped. This may be harmless for a first debug launch, but AGC services and some devices may require manual signing."
fi

if [[ -f .hvigor/outputs/build-logs/build.log ]] && rg -q 'shouldDeduplicateHar' .hvigor/outputs/build-logs/build.log; then
  echo "- FIX: Hvigor reported shouldDeduplicateHar input issues. Regenerate .hvigor/build caches after preserving source files."
fi

echo
echo "Done."
