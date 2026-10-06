#!/usr/bin/env bash
set -euo pipefail

# SparkService 发板前只读检查。默认仅检查本地；传入 --remote 时同时检查服务器。

SPARK_SOURCE_DIR="${SPARK_SOURCE_DIR:-/Users/hua/Documents/project/Reference/SparkService}"
SERVER_TEMPLATE_DIR="${SERVER_TEMPLATE_DIR:-/Users/hua/Documents/project/Reference/2026}"
REMOTE_TARGET="${REMOTE_TARGET:-root@139.196.215.51}"
REMOTE_ROOT="${REMOTE_ROOT:-/root/2026}"
CHECK_REMOTE=0
FAILURES=0
WARNINGS=0

if [[ "${1:-}" == "--remote" ]]; then
  CHECK_REMOTE=1
elif [[ $# -gt 0 ]]; then
  echo "用法：$0 [--remote]" >&2
  exit 2
fi

ok() {
  printf '[正常] %s\n' "$*"
}

warn() {
  WARNINGS=$((WARNINGS + 1))
  printf '[提醒] %s\n' "$*" >&2
}

fail() {
  FAILURES=$((FAILURES + 1))
  printf '[失败] %s\n' "$*" >&2
}

require_file() {
  local path="$1"
  local label="$2"
  if [[ -f "$path" ]]; then
    ok "${label}：$path"
  else
    fail "${label}不存在：$path"
  fi
}

require_dir() {
  local path="$1"
  local label="$2"
  if [[ -d "$path" ]]; then
    ok "${label}：$path"
  else
    fail "${label}不存在：$path"
  fi
}

require_command() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    ok "本地命令可用：$name"
  else
    fail "缺少本地命令：$name"
  fi
}

check_env_key() {
  local key="$1"
  if rg -q "^${key}=" "$SPARK_SOURCE_DIR/.env"; then
    ok "生产配置包含：$key"
  else
    fail "生产配置缺少：$key"
  fi
}

echo "==> 本地项目"
require_dir "$SPARK_SOURCE_DIR" "SparkService 源码目录"
require_dir "$SERVER_TEMPLATE_DIR" "2026 服务器模板目录"
require_file "$SPARK_SOURCE_DIR/scripts/deploy_sparkservice.sh" "本地发板脚本"
require_file "$SPARK_SOURCE_DIR/manage.py" "Django manage.py"
require_file "$SPARK_SOURCE_DIR/requirements.txt" "Python 依赖文件"
require_file "$SPARK_SOURCE_DIR/.env" "生产配置来源"
require_file "$SERVER_TEMPLATE_DIR/docker-compose.yml" "Docker Compose 配置"
require_file "$SERVER_TEMPLATE_DIR/bin/deploy_remote.sh" "远端发板脚本"

echo
echo "==> 本地工具"
for command_name in bash ssh scp rsync tar pnpm rg; do
  require_command "$command_name"
done

echo
echo "==> 前端项目"
require_file "$SPARK_SOURCE_DIR/backoffice-web/package.json" "后台前端 package.json"
require_file "$SPARK_SOURCE_DIR/backoffice-web/pnpm-lock.yaml" "后台前端锁文件"
require_file "$SPARK_SOURCE_DIR/open-web/package.json" "开放端 package.json"
require_file "$SPARK_SOURCE_DIR/open-web/pnpm-lock.yaml" "开放端锁文件"
require_file "$SPARK_SOURCE_DIR/chat-web/package.json" "对话前端 package.json"
require_file "$SPARK_SOURCE_DIR/chat-web/pnpm-lock.yaml" "对话前端锁文件"

if rg -q "output:[[:space:]]*['\"]standalone['\"]" "$SPARK_SOURCE_DIR/chat-web/next.config.ts"; then
  ok "chat-web 已启用 Next.js standalone"
else
  fail "chat-web/next.config.ts 未发现 output: standalone"
fi

echo
echo "==> 生产配置键"
for env_key in \
  DJANGO_ALLOWED_HOSTS \
  CSRF_TRUSTED_ORIGINS \
  CORS_ALLOWED_ORIGINS \
  DJANGO_SECRET_KEY \
  DB_HOST \
  DB_NAME \
  DB_USER \
  DB_PASSWORD \
  CELERY_BROKER_URL \
  CELERY_RESULT_BACKEND \
  CELERY_QUEUES \
  APNS_USE_SANDBOX \
  CHAT_WEB_PORT; do
  check_env_key "$env_key"
done

if rg -q '^CELERY_QUEUES=.*chat\.ai' "$SPARK_SOURCE_DIR/.env" \
  && rg -q '^CELERY_QUEUES=.*chat\.events' "$SPARK_SOURCE_DIR/.env" \
  && rg -q '^CELERY_QUEUES=.*chat\.recovery' "$SPARK_SOURCE_DIR/.env" \
  && rg -q '^CELERY_QUEUES=.*subscriptions' "$SPARK_SOURCE_DIR/.env"; then
  ok "Web AI 与 RevenueCat Celery 队列完整"
else
  fail "CELERY_QUEUES 缺少 chat.ai、chat.events、chat.recovery 或 subscriptions"
fi

if [[ -f "$SPARK_SOURCE_DIR/subscriptions/tasks.py" ]] \
  && rg -q 'process_revenuecat_webhook_event|reconcile_revenuecat_subscriptions_task|retry_pending_revenuecat_webhooks_task|sync_revenuecat_user_task' "$SPARK_SOURCE_DIR/subscriptions/tasks.py"; then
  ok "RevenueCat Celery 任务源码存在"
else
  fail "RevenueCat Celery 任务源码不完整"
fi

if [[ "$CHECK_REMOTE" == "1" ]]; then
  echo
  echo "==> 远端服务器"
  if ! ssh -o BatchMode=yes -o ConnectTimeout=8 "$REMOTE_TARGET" true; then
    fail "无法免交互连接服务器：$REMOTE_TARGET"
  else
    ok "SSH 连接正常：$REMOTE_TARGET"
    if ssh "$REMOTE_TARGET" "test -f '$REMOTE_ROOT/docker-compose.yml' && test -f '$REMOTE_ROOT/.deploy.env'"; then
      ok "远端 Compose 和生产配置存在"
    else
      fail "远端缺少 docker-compose.yml 或 .deploy.env"
    fi

    remote_report="$(ssh "$REMOTE_TARGET" "
      set -u
      printf 'DISK='; df -P '$REMOTE_ROOT' | awk 'NR==2 {print \$5}'
      printf 'DOCKER='; systemctl is-active docker 2>/dev/null || true
      printf 'MYSQL='; systemctl is-active mysqld 2>/dev/null || systemctl is-active mysql 2>/dev/null || true
      printf 'REDIS='; systemctl is-active redis 2>/dev/null || systemctl is-active redis-server 2>/dev/null || true
      printf 'NGINX='; systemctl is-active nginx 2>/dev/null || true
      printf 'CURRENT='; readlink '$REMOTE_ROOT/current' 2>/dev/null || true
      printf 'ENV_MODE='; stat -c '%a' '$REMOTE_ROOT/.deploy.env' 2>/dev/null || true
    " 2>/dev/null || true)"
    printf '%s\n' "$remote_report"

    disk_percent="$(printf '%s\n' "$remote_report" | sed -n 's/^DISK=\([0-9][0-9]*\)%.*/\1/p')"
    if [[ -n "$disk_percent" && "$disk_percent" -ge 85 ]]; then
      fail "远端磁盘使用率 ${disk_percent}%，不应开始 Docker 构建"
    elif [[ -n "$disk_percent" && "$disk_percent" -ge 75 ]]; then
      warn "远端磁盘使用率 ${disk_percent}%，发板前应确认构建缓存和历史包空间"
    else
      ok "远端磁盘空间满足发板预检"
    fi

    if printf '%s\n' "$remote_report" | rg -q '^ENV_MODE=600$'; then
      ok "远端 .deploy.env 权限为 600"
    else
      warn "远端 .deploy.env 权限不是 600 或无法读取"
    fi

    root_cron="$(ssh "$REMOTE_TARGET" 'crontab -l 2>/dev/null || true')"
    if printf '%s\n' "$root_cron" | rg -q 'domain_healthcheck\.sh'; then
      ok "远端域名健康检查定时任务存在"
    else
      warn "远端域名健康检查定时任务缺失"
    fi
    if printf '%s\n' "$root_cron" | rg -q 'certbot renew'; then
      ok "远端 Certbot 续期定时任务存在"
    else
      warn "远端 Certbot 续期定时任务缺失"
    fi
    if printf '%s\n' "$root_cron" | rg -q '^20 4 .*2026.*restart'; then
      ok "远端每天 04:20 项目重启存在"
    else
      warn "远端未发现每天 04:20 项目重启"
    fi

    systemd_services="$(ssh "$REMOTE_TARGET" 'systemctl cat sparkservice-2026.service 2>/dev/null || true')"
    for compose_service in web celery_worker celery_beat frontend open_web chat_web; do
      if printf '%s\n' "$systemd_services" | rg -q -w "$compose_service"; then
        ok "systemd 启动清单包含：$compose_service"
      else
        fail "systemd 启动清单缺少：$compose_service"
      fi
    done
  fi
fi

echo
printf '==> 预检完成：失败 %d，提醒 %d\n' "$FAILURES" "$WARNINGS"
if [[ "$FAILURES" -gt 0 ]]; then
  exit 1
fi
