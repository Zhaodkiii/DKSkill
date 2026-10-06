#!/usr/bin/env bash
set -euo pipefail

# SparkService 发板后只读验收。不会修改、重启或清理服务器。

REMOTE_TARGET="${REMOTE_TARGET:-root@139.196.215.51}"
REMOTE_ROOT="${REMOTE_ROOT:-/root/2026}"
FAILED=0
WARNED=0

ok() {
  printf '[正常] %s\n' "$*"
}

warn() {
  WARNED=$((WARNED + 1))
  printf '[提醒] %s\n' "$*" >&2
}

fail() {
  FAILED=$((FAILED + 1))
  printf '[失败] %s\n' "$*" >&2
}

remote() {
  ssh -o BatchMode=yes -o ConnectTimeout=8 "$REMOTE_TARGET" "$@"
}

check_url() {
  local label="$1"
  local url="$2"
  local code
  code="$(curl -L -sS -o /dev/null -w '%{http_code}' --connect-timeout 8 --max-time 20 "$url" || true)"
  if [[ "$code" =~ ^(200|201|202|204|301|302|307|308)$ ]]; then
    ok "${label}：HTTP $code $url"
  else
    fail "${label}：HTTP ${code:-000} $url"
  fi
}

echo "==> 服务器连接"
if ! remote true; then
  fail "无法连接服务器：$REMOTE_TARGET"
  exit 1
fi
ok "SSH 连接正常"

echo
echo "==> 版本和主机资源"
host_report="$(remote "
  printf 'CURRENT='; readlink '$REMOTE_ROOT/current' 2>/dev/null || true
  printf 'DISK='; df -P '$REMOTE_ROOT' | awk 'NR==2 {print \$5}'
  printf 'MEMORY='; free -h | awk '/^Mem:/ {print \$3 \"/\" \$2 \" available=\" \$7}'
  printf 'SWAP='; free -h | awk '/^Swap:/ {print \$3 \"/\" \$2}'
  printf 'LOAD='; uptime | sed 's/.*load average: //'
")"
printf '%s\n' "$host_report"

disk_percent="$(printf '%s\n' "$host_report" | sed -n 's/^DISK=\([0-9][0-9]*\)%.*/\1/p')"
if [[ -n "$disk_percent" && "$disk_percent" -ge 90 ]]; then
  fail "磁盘使用率 ${disk_percent}%"
elif [[ -n "$disk_percent" && "$disk_percent" -ge 80 ]]; then
  warn "磁盘使用率 ${disk_percent}%"
else
  ok "磁盘使用率未达到告警线"
fi

echo
echo "==> 基础 systemd 服务"
for service_name in docker nginx mysqld redis sparkservice-2026; do
  state="$(remote "systemctl is-active '$service_name' 2>/dev/null || true")"
  enabled="$(remote "systemctl is-enabled '$service_name' 2>/dev/null || true")"
  if [[ "$state" == "active" ]]; then
    ok "${service_name}：active，enabled=$enabled"
  else
    fail "${service_name}：state=${state:-unknown}，enabled=${enabled:-unknown}"
  fi
done

echo
echo "==> Docker Compose 六个服务"
compose_rows="$(remote "cd '$REMOTE_ROOT' && docker compose --env-file .deploy.env ps --format '{{.Service}}|{{.State}}|{{.Health}}|{{.Status}}'")"
printf '%s\n' "$compose_rows"
for service_name in web celery_worker celery_beat frontend open_web chat_web; do
  row="$(printf '%s\n' "$compose_rows" | awk -F'|' -v service="$service_name" '$1 == service {print; exit}')"
  if [[ -z "$row" ]]; then
    fail "Compose 服务缺失：$service_name"
  elif printf '%s' "$row" | rg -q '\|running\|'; then
    if [[ "$service_name" =~ ^(web|frontend|open_web|chat_web)$ ]] \
      && ! printf '%s' "$row" | rg -q '\|healthy\|'; then
      warn "$service_name 正在运行但尚未 healthy：$row"
    else
      ok "${service_name}：$row"
    fi
  else
    fail "$service_name 状态异常：$row"
  fi
done

echo
echo "==> 本机端口和健康接口"
for port in 2026 6018 2028 9001 3306 6379; do
  if remote "ss -lnt | rg -q ':${port}\\b' 2>/dev/null || ss -lnt | grep -Eq ':${port}\\b'"; then
    ok "端口监听：$port"
  else
    fail "端口未监听：$port"
  fi
done

if remote "curl -fsS --connect-timeout 5 --max-time 15 http://127.0.0.1:2026/health/ >/dev/null"; then
  ok "Django 本机健康接口"
else
  fail "Django 本机健康接口失败"
fi

echo
echo "==> 公网域名"
check_url "后台前端" "https://spark.dreamhua.top/"
check_url "Django API" "https://api.dreamhua.top/health/"
check_url "开放端" "https://share.dreamwhale.top/"
check_url "AI 对话端" "https://chat.dreamwhale.top/login"

echo
echo "==> Celery"
if remote "timeout 15s docker exec 2026-celery_worker-1 celery -A SparkService inspect ping --timeout=5" >/tmp/sparkservice_celery_ping.$$ 2>&1; then
  ok "Celery Worker inspect ping"
else
  fail "Celery Worker inspect ping 失败"
fi
rm -f /tmp/sparkservice_celery_ping.$$

registered="$(remote "timeout 15s docker exec 2026-celery_worker-1 celery -A SparkService inspect registered --timeout=5" 2>/dev/null || true)"
for task_name in \
  chat_sync.ai_tasks.run_tasks.run_chat \
  chat_sync.ai_tasks.run_tasks.resume_chat_run \
  chat_sync.ai_tasks.outbox_tasks.relay_chat_event_outbox \
  chat_sync.ai_tasks.recovery_tasks.recover_chat_runs \
  chat_sync.ai_tasks.recovery_tasks.expire_chat_interactions \
  notification_center.tasks.execute_notification_campaign_task \
  subscriptions.tasks.process_revenuecat_webhook_event \
  subscriptions.tasks.reconcile_revenuecat_subscriptions_task \
  subscriptions.tasks.retry_pending_revenuecat_webhooks_task \
  subscriptions.tasks.sync_revenuecat_user_task; do
  if printf '%s\n' "$registered" | rg -q -F "$task_name"; then
    ok "Celery task 已注册：$task_name"
  else
    fail "Celery task 未注册：$task_name"
  fi
done

for removed_task_name in \
  chat_sync.ai_tasks.knowledge_tasks.index_document_task \
  chat_sync.ai_tasks.knowledge_tasks.rebuild_index_version_task \
  chat_sync.ai_tasks.knowledge_tasks.extract_document_task; do
  if printf '%s\n' "$registered" | rg -q -F "$removed_task_name"; then
    fail "Celery 仍注册已移除任务：$removed_task_name"
  else
    ok "Celery 已移除旧任务：$removed_task_name"
  fi
done

active_queues="$(remote "timeout 15s docker exec 2026-celery_worker-1 celery -A SparkService inspect active_queues --timeout=5" 2>/dev/null || true)"
for queue_name in chat.ai chat.events chat.recovery notification.security.high notification.transactional notification.bulk notification.receipt subscriptions; do
  if printf '%s\n' "$active_queues" | rg -q -F "$queue_name"; then
    ok "Worker 正在消费：$queue_name"
  else
    fail "Worker 未消费：$queue_name"
  fi
done

echo
echo "==> 自动运维配置"
root_cron="$(remote 'crontab -l 2>/dev/null || true')"
if printf '%s\n' "$root_cron" | rg -q 'domain_healthcheck\.sh'; then
  ok "域名健康检查定时任务存在"
else
  warn "域名健康检查定时任务缺失"
fi
if printf '%s\n' "$root_cron" | rg -q 'certbot renew'; then
  ok "Certbot 续期定时任务存在"
else
  warn "Certbot 续期定时任务缺失"
fi
if printf '%s\n' "$root_cron" | rg -q '^20 4 .*2026.*restart'; then
  ok "每天 04:20 项目重启存在"
else
  warn "未发现每天 04:20 项目重启"
fi

echo
echo "==> 最近错误日志"
error_output="$(remote "
  for container_name in 2026-web-1 2026-celery_worker-1 2026-celery_beat-1 2026-frontend-1 2026-open_web-1 2026-chat_web-1; do
    docker logs --since=30m --tail=500 \"\$container_name\" 2>&1 \
      | grep -E -B2 -A8 'ERROR|CRITICAL|Traceback|Exception|OperationalError|ProgrammingError|DatabaseError|FAILED' \
      && printf '\\nCONTAINER=%s\\n' \"\$container_name\"
  done
" 2>/dev/null || true)"
if [[ -n "$error_output" ]]; then
  warn "最近 30 分钟发现匹配错误日志"
  printf '%s\n' "$error_output" | tail -n 120
else
  ok "最近 30 分钟未发现匹配错误日志"
fi

echo
printf '==> 验收完成：失败 %d，提醒 %d\n' "$FAILED" "$WARNED"
if [[ "$FAILED" -gt 0 ]]; then
  exit 1
fi
