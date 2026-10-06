# SparkService 发板故障处置手册

## 1. 处置原则

遇到生产故障时按以下顺序行动：

1. 先确认用户影响和是否仍在扩大。
2. 保存证据，不先清日志或大范围清理。
3. 判断是代码、配置、数据、依赖、资源还是入口层故障。
4. 优先恢复服务，再做根因修复。
5. 每个破坏性动作前确认目标和回退路径。
6. 恢复后执行完整验收，不以单个进程存在作为成功。

## 2. 第一现场证据

```bash
ssh root@139.196.215.51 'cd /root/2026 && ./bin/status_snapshot.sh'
```

额外记录：

```bash
ssh root@139.196.215.51 '
  date
  readlink /root/2026/current
  df -h /
  free -h
  docker system df
  cd /root/2026
  docker compose --env-file .deploy.env ps
'
```

事故记录应包含时间、用户症状、最近一次 release、最后一次配置同步、最近迁移和最早错误。

## 3. 故障分类

### A. 域名无法访问

判断层级：

```text
DNS -> 80/443 -> 证书 -> Nginx server_name -> proxy upstream -> 应用端口 -> 应用健康
```

检查：

```bash
dig +short chat.dreamwhale.top
curl -vkI https://chat.dreamwhale.top/login
ssh root@139.196.215.51 'nginx -t'
ssh root@139.196.215.51 'ss -lntp | grep -E ":(443|9001)\b"'
ssh root@139.196.215.51 'curl -I http://127.0.0.1:9001/login'
```

如果本机 upstream 正常、域名失败，问题通常在 DNS、证书或 Nginx。如果 upstream 也失败，先处理容器。

### B. 502/500

- `502 Bad Gateway`：Nginx 无法连接 upstream、upstream 提前断开或代理协议不匹配。
- Nginx `500`：可能是 Nginx 配置、Basic Auth 文件权限、内部重定向循环。
- Django `500`：查看 `2026-web-1` Traceback 和共享日志。

```bash
ssh root@139.196.215.51 'tail -n 200 /var/log/nginx/error.log'
ssh root@139.196.215.51 'docker logs --tail=300 2026-web-1'
```

### C. web 启动失败

检查顺序：

1. 容器退出码和健康状态。
2. Python import、环境变量、Django settings。
3. MySQL/Redis 连接。
4. migration 是否完整。
5. 2026 端口是否被其他进程占用。

```bash
ssh root@139.196.215.51 'docker inspect 2026-web-1 --format "{{json .State}}"'
ssh root@139.196.215.51 'docker logs --tail=300 2026-web-1'
ssh root@139.196.215.51 'ss -lntp | grep :2026 || true'
```

### D. Celery Worker 不执行任务

检查：

```bash
ssh root@139.196.215.51 'docker exec 2026-celery_worker-1 celery -A SparkService inspect ping'
ssh root@139.196.215.51 'docker exec 2026-celery_worker-1 celery -A SparkService inspect registered'
ssh root@139.196.215.51 'docker exec 2026-celery_worker-1 celery -A SparkService inspect active_queues'
ssh root@139.196.215.51 'docker logs --tail=300 2026-celery_worker-1'
```

常见根因：

- task 没有 import 或注册。
- route 发往 Worker 未消费的 queue。
- Redis broker 不可用。
- task 反序列化失败。
- Worker 被长任务占满。
- task 抛错但业务页面只显示“已入队”。

### E. Celery Beat 不调度

```bash
ssh root@139.196.215.51 'docker logs --tail=300 2026-celery_beat-1'
ssh root@139.196.215.51 'cd /root/2026 && docker compose --env-file .deploy.env run --rm web python manage.py showmigrations django_celery_beat'
```

出现 `django_celery_beat_periodictasks doesn't exist` 时执行标准 migration 并验证表，不要清空 Beat 数据库文件来掩盖 MySQL 缺表。

### F. Docker build 卡住

检查资源和网络：

```bash
ssh root@139.196.215.51 'df -h /; free -h; docker system df'
ssh root@139.196.215.51 'docker info | sed -n "/Registry Mirrors/,+8p"'
```

常见根因：Docker Hub/GCR 网络超时、Debian apt 源超时、磁盘不足、内存 swap 压力、旧 buildkit 缓存过大。

不要在构建仍运行时反复启动多个发布。取消旧发布后要确认相关 build 进程确实退出。

### G. 磁盘 100%

优先确认占用：

```bash
ssh root@139.196.215.51 '
  df -h /
  docker system df
  du -sh /var/lib/docker /root/2026/releases /root/2026/uploads /root/2026/build 2>/dev/null
'
```

清理优先级：

1. Docker build cache。
2. 悬空和确认不再使用的镜像。
3. 失败的临时上传目录和未完成 release。
4. 超过保留数量的旧包。

不能删除当前 `current` 指向的 release、最近回滚版本、`shared`、数据库和媒体。

### H. 前端仍是旧版本

- 浏览器缓存或 CDN 缓存。
- 本地构建失败后上传了旧 dist。
- `NEXT_PUBLIC_*` 改了但未重新 build。
- chat standalone 上传后容器没有 recreate。
- Nginx root/volume 仍指向旧目录。

对 `chat_web`：

```bash
ssh root@139.196.215.51 '
  test -s /root/2026/shared/chat-web-standalone/server.js
  cd /root/2026
  docker compose --env-file .deploy.env up -d --force-recreate --no-deps chat_web
'
```

只有在用户要求修复时才执行 recreate；诊断请求只报告原因。

## 4. 回滚决策

立即回滚的典型条件：

- 核心 API 持续 5xx，短时间不能修复。
- 新版本导致大量任务失败或数据错误。
- 新容器无法稳定启动。
- 新配置导致认证、支付、通知等核心链路中断。

先修复而不回滚的典型条件：

- 单个非核心域名 Nginx 配置错误，后端正常。
- 证书续期或静态文件路径问题。
- 可独立恢复的基础设施服务问题。

执行：

```bash
ssh root@139.196.215.51 '/root/2026/bin/rollback.sh'
```

回滚后再次执行 post-release audit。若数据库迁移不可逆，不得假设代码回滚已恢复数据兼容性。

## 5. 环境配置恢复

每次同步 `.env` 前，服务器会生成：

```text
/root/2026/.deploy.env.bak_<时间戳>
```

恢复配置的一般流程：

1. 找到明确的备份文件。
2. 对比键名，不在聊天中打印密钥值。
3. 备份当前错误配置。
4. 以 `600` 权限安装旧配置。
5. recreate 受影响容器。
6. 验证业务。

## 6. 事故结束条件

- 六个服务达到预期状态。
- 四个业务域名通过。
- Celery 能 ping，关键 queues 正常。
- 关键业务链路恢复。
- 30 分钟内没有同类新增错误。
- 已记录根因、影响、恢复动作和防复发措施。
