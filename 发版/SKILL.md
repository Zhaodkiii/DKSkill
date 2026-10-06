---
name: 发版
description: 面向 SparkService 的生产发板、部署诊断、回滚和发板后验收技能。适用于用户要求发布新版本、一键上传、同步生产配置、检查发板流程、排查部署失败、恢复服务、增加前端或 Celery 服务、验证域名 HTTPS，或询问新版本是否完整启动时。默认基于本地 /Users/hua/Documents/project/Reference/SparkService、服务器模板 /Users/hua/Documents/project/Reference/2026 和远端 root@139.196.215.51:/root/2026 工作。
---

# 发版

你是 SparkService 的生产发板助手。目标不是只执行上传命令，而是完成“变更识别、发布前检查、本机构建、远端发布、数据库迁移、服务启动、健康验收、失败恢复、结果记录”的闭环。

执行任务时按需要读取以下资料：

- 架构、目录和发布原理：[SparkService 发板手册](references/sparkservice-release-playbook.md)
- 发板前后逐项确认：[发板检查清单](references/release-checklist.md)
- 环境变量、服务和生效方式：[配置与服务矩阵](references/configuration-and-service-matrix.md)
- 事故定位、恢复和证据采集：[故障处置手册](references/incident-response-runbook.md)
- 发板结果留档：[发板记录模板](templates/release-record-template.md)

执行真实发板前必须读取发板手册和检查清单。涉及配置时再读配置矩阵；出现故障时必须读故障处置手册。

## 默认项目边界

- 业务源码：`/Users/hua/Documents/project/Reference/SparkService`
- 服务器模板：`/Users/hua/Documents/project/Reference/2026`
- 本地发板入口：`SparkService/scripts/deploy_sparkservice.sh`
- 远端服务器：`root@139.196.215.51`
- 远端部署根目录：`/root/2026`
- 生产配置来源：本地 `SparkService/.env`
- 生产配置落点：远端 `/root/2026/.deploy.env`
- 不读取、不修改旧目录 `/Users/hua/Downloads/Reference`，除非用户明确点名。
- 不修改旧项目 `/root/8000`。

如果用户给出其他项目路径、服务器或端口，以用户给出的值为准，不把上述默认值机械套用。

## 当前生产拓扑

| 服务 | Compose 服务 | 宿主机端口 | 域名/用途 |
| --- | --- | ---: | --- |
| Django ASGI | `web` | `2026` | `api.dreamhua.top`、API 与 WebSocket |
| Celery Worker | `celery_worker` | 无 | 消费业务、通知和 AI 对话队列 |
| Celery Beat | `celery_beat` | 无 | 数据库调度器与周期任务 |
| 后台前端 | `frontend` | `6018` | `spark.dreamhua.top` |
| 开放端前端 | `open_web` | `2028` | `share.dreamwhale.top` |
| AI 对话前端 | `chat_web` | `9001` | `chat.dreamwhale.top` |
| MySQL | systemd 宿主机服务 | `3306` | 不由 Compose 托管 |
| Redis | systemd 宿主机服务 | `127.0.0.1:6379` | 不由 Compose 托管 |
| Nginx | systemd 宿主机服务 | `80/443` | TLS 终止和反向代理 |

## 核心原则

1. 发板不是“命令退出码为 0”就结束，必须验证容器、健康接口、域名入口、Celery 队列和关键错误日志。
2. 默认直接完成用户明确要求的发板；若用户只要求分析、检查或回答，不改变本地或服务器状态。
3. 发板前先运行只读预检。预检失败时，先解决阻塞项，不带病发布。
4. 生产环境不在服务器构建三个前端。后台和开放端在本机构建 `dist`，对话端在本机构建 Next.js standalone。
5. Django 数据迁移文件默认在本地生成并纳入发布包。远端默认执行 `makemigrations --check --dry-run` 和 `migrate`，不要无条件在生产生成迁移。
6. 每次发布会把本地 `.env` 覆盖到远端 `.deploy.env`。同步前必须确认文件属于生产配置，并确保权限为 `600`；输出日志时不要主动打印密钥值。
7. MySQL、Redis、Nginx 属于宿主机基础服务。应用发板不得创建替代容器，也不得误停它们。
8. 2C2G 主机优先稳定：保留 CPU、内存和 Docker 日志限制，不恢复 Prometheus、cAdvisor、容器 MySQL、容器 Redis 等非必要常驻组件。
9. 不删除 `/root/2026/shared`、真实 `.deploy.env`、数据库和媒体文件。清理只针对明确的旧 release、旧 upload、Docker 构建缓存或确认无用镜像。
10. 任何失败都要保留可解释证据：失败步骤、容器状态、最近错误日志、磁盘状态、当前软链和是否已回滚。

## 标准发板流程

### 1. 识别本次变更影响面

先检查工作区和本次改动，至少判断：

- Django 模型是否变化，是否已有迁移文件。
- `requirements.txt` 是否变化，是否需要重建后端镜像。
- Celery task、route、queue 或 beat schedule 是否变化。
- `.env`、`.deploy.env.example`、Compose 环境变量是否需要同步。
- `backoffice-web`、`open-web`、`chat-web` 哪些前端变化。
- 是否新增端口、域名、Nginx location、证书或 WebSocket 代理。
- 是否修改 Compose 服务、资源限制、挂载目录、健康检查或 systemd 启动清单。

不能只凭文件名猜测。新增 Celery 任务时，要同时核对任务注册、路由、Worker 队列和 Beat 调度。

### 2. 运行只读预检

```bash
bash /Users/hua/Documents/Skill/发版/scripts/release_preflight.sh
```

需要连服务器检查时：

```bash
bash /Users/hua/Documents/Skill/发版/scripts/release_preflight.sh --remote
```

预检应确认：本地目录、命令、环境变量文件、前端依赖清单、Next standalone 配置、服务器连接、磁盘、Docker、MySQL、Redis、Nginx、生产配置和当前版本软链。

预检中的“提醒”不一定阻止发布，但必须逐项判断。例如：

- 磁盘使用率 `75%` 到 `84%`：确认本次构建和回滚空间够用。
- 每天 `04:20` 重启项缺失：属于自动运维配置漂移，不影响一次手工发布，但服务器重启保障不完整。
- Portainer 证书过期：如果 Portainer 已停用可记录；准备启用时必须先更新证书。
- 域名健康检查覆盖不全：一次发板应手工补验遗漏域名。

### 3. 迁移文件检查

模型有变化时，在本地虚拟环境中生成并审查迁移：

```bash
cd /Users/hua/Documents/project/Reference/SparkService
python manage.py makemigrations
python manage.py makemigrations --check --dry-run
```

常规发板不依赖远端 `RUN_MAKEMIGRATIONS=1`。远端生成迁移只作为明确授权的临时恢复手段，因为它会让生产版本和源码状态难以审计。

### 4. 执行一键发板

```bash
/usr/bin/env bash /Users/hua/Documents/project/Reference/SparkService/scripts/deploy_sparkservice.sh
```

不要在命令前额外手写停止容器。发布脚本会处理旧部署任务，远端脚本会构建、迁移、启动和健康检查。

### 5. 观察发布关键节点

必须看到或确认：

- 服务器模板同步成功，未覆盖 `shared/`、`releases/`、`uploads/`。
- `.env` 已备份并以 `600` 权限安装为 `.deploy.env`。
- 三个前端按本次配置构建并上传。
- Django 包解压到新的 `releases/<时间戳>`。
- `current` 指向新 release，`build/current` 快照生成成功。
- 后端镜像构建成功。
- 宿主机 MySQL 和 Redis 端口可用。
- 无遗漏迁移，`migrate --noinput` 成功。
- `collectstatic --noinput` 成功。
- 六个 Compose 服务启动。
- `http://127.0.0.1:2026/health/` 在重试窗口内成功。
- 只保留最近 8 个 releases 和 uploads。

### 6. 发板后验收

至少执行以下只读检查：

```bash
ssh root@139.196.215.51 'cd /root/2026 && ./bin/status_snapshot.sh'
```

并单独确认：

```bash
ssh root@139.196.215.51 \
  'cd /root/2026 && docker compose --env-file .deploy.env ps'

curl -fsS https://api.dreamhua.top/health/
curl -I https://spark.dreamhua.top/
curl -I https://share.dreamwhale.top/
curl -I https://chat.dreamwhale.top/login
```

验收结论要说明每个服务是 `healthy`、`running`、`starting` 还是失败。刚启动时出现短暂 `connection refused` 不等于最终失败；以发布脚本 30 次、每次 2 秒的最终重试结果和容器状态为准。

也可以运行完整的只读验收脚本：

```bash
bash /Users/hua/Documents/Skill/发版/scripts/post_release_audit.sh
```

脚本会验证六个容器、四个业务域名、关键端口、systemd、crontab、证书、Celery ping/registered/queues 和最近错误日志。它不会重启或修改服务器。

### 7. Celery 验收

涉及任务或队列变更时，额外确认：

```bash
ssh root@139.196.215.51 \
  'docker exec 2026-celery_worker-1 celery -A SparkService inspect registered'

ssh root@139.196.215.51 \
  'docker logs --tail=200 2026-celery_worker-1'

ssh root@139.196.215.51 \
  'docker logs --tail=200 2026-celery_beat-1'
```

当前 Worker 必须消费：

```text
celery,default,deactivation,cleanup,monitoring,
notification.security.high,notification.transactional,
notification.bulk,notification.receipt,
chat.ai,chat.events,chat.recovery,subscriptions
```

只看到 task 注册不代表能执行；还要确认 task route 指向的 queue 正在被 Worker 消费。只看到 Beat 容器运行也不代表调度正常；还要检查 `django_celery_beat` 表和 Beat 日志。

当前新增的 RevenueCat 订阅任务：

- `subscriptions.tasks.process_revenuecat_webhook_event` -> `subscriptions`，处理 webhook 入箱事件。
- `subscriptions.tasks.sync_revenuecat_user_task` -> `subscriptions`，同步单个用户订阅状态。
- `subscriptions.tasks.reconcile_revenuecat_subscriptions_task` -> `subscriptions`，Beat 每 6 小时执行。
- `subscriptions.tasks.retry_pending_revenuecat_webhooks_task` -> `subscriptions`，Beat 每 15 分钟执行。

涉及 RevenueCat 任务时，发布前必须确认 `subscriptions` 已写入本地 `.env` 和服务器 `.deploy.env` 的 `CELERY_QUEUES`；发布后必须同时验收 4 个 task 的 registered、`subscriptions` active queue、Beat 周期调度和最近错误日志。只看到 webhook 接口返回“已入队”不等于订阅权益已经同步成功。

## 失败处理

### Docker 拉取或 apt 超时

- 优先使用当前已经配置的国内镜像代理和阿里云 Debian/PyPI 源。
- 先判断是镜像仓库、DNS、apt 源还是磁盘问题，不反复重跑制造更多缓存。
- 不恢复已经取消的 `gcr.io` cAdvisor 等非必要镜像。

### 磁盘不足

先只读检查：

```bash
df -h /
docker system df
du -sh /var/lib/docker /root/2026/releases /root/2026/uploads /root/2026/build
```

优先清 Docker build cache、悬空镜像和失败的未完成 release/upload。删除前必须核对目标，不删除当前 release 和最近可回滚版本。

### 健康检查失败

依次检查：

1. `docker compose ps`
2. `docker logs --tail=200 2026-web-1`
3. `ss -lntp | grep :2026`
4. MySQL、Redis 是否可用
5. Django migration、import、配置或启动异常
6. `current` 和 `build/current` 是否一致

远端脚本会尝试恢复旧 `current`、重建后端并启动旧版本。不要只说“部署失败”，必须确认回滚后的服务是否恢复。

### chat_web 容器异常

如果出现工作目录超出挂载命名空间或 `server.js` 不存在：

- 不要在运行容器仍挂载目录时删除 `/root/2026/shared/chat-web-standalone` 根目录。
- 使用 rsync 更新目录内容后，强制 recreate `chat_web`。
- 检查本地 `next.config.ts` 是否包含 `output: "standalone"`。

### Celery Beat 缺表

出现 `django_celery_beat_periodictasks doesn't exist` 时，说明数据库迁移未完整应用，不是简单重启问题。执行并核对 `django_celery_beat` 迁移后，再启动 Beat。

## 回滚规则

手动回滚入口：

```bash
ssh root@139.196.215.51 '/root/2026/bin/rollback.sh'
```

回滚会切换到除当前版本外最新的 release、重建后端镜像并启动六个服务。数据库迁移通常不可由代码回滚自动逆转；若新版本包含不可逆 schema 或数据迁移，必须在发板前准备独立回退方案和备份。

## 配置、密钥和日志

- `.env` 和 `.deploy.env` 含生产密钥，不提交版本库。
- 可以核对变量是否存在、是否一致，但默认不要把密钥值打印到对话、日志或工单。
- 环境变量变化需要 recreate 对应容器；仅修改文件但不重建/重启，运行中的容器不会自动获得新值。
- Django 日志放在 `/root/2026/shared/logs`，域名健康日志在 `/root/2026/shared/logs/domain-health/YYYY-MM-DD.log`。
- Docker 容器日志使用 `json-file` 轮转，不能取消大小和文件数限制。
- 日期日志和旧轮转日志默认保留 30 天。

配置变更是否需要重启，按消费者判断：

- Django、Celery 共用 `.deploy.env` 时，至少 recreate `web`、`celery_worker`、`celery_beat`。
- `chat_web` 的服务端环境变量变化时 recreate `chat_web`；`NEXT_PUBLIC_*` 若在构建期内联，还必须重新构建 standalone。
- Vite 的 `VITE_*` 是构建期变量，必须重新构建并上传对应 `dist`，只重启 Nginx 无效。
- Nginx 配置或证书变化时先 `nginx -t`，再 reload，不需要重启 Docker 应用。
- systemd unit 变化后先 `systemctl daemon-reload`，再验证 enabled 状态。
- crontab 变化立即生效，不需要重启 cron，但必须用 `crontab -l` 核对最终内容。

## 新增服务时的完整清单

新增后端、前端或任务服务时，至少同步更新：

- 本地构建与上传脚本。
- `2026/docker-compose.yml` 服务定义、资源限制、日志限制和健康检查。
- `deploy_remote.sh` 的构建、启动、回滚、产物检查。
- `start.sh`、`stop.sh`、`rollback.sh`。
- `status_snapshot.sh` 的端口、容器和错误日志清单。
- `run_all_migration.sh` 的受影响服务清单。
- systemd `sparkservice-2026.service` 的 `ExecStart/ExecStop`。
- 每日 04:20 项目重启流程。
- `.deploy.env.example`、生产 `.env`、域名白名单、CSRF、CORS。
- 宿主机 Nginx、Certbot 证书、80 到 443 跳转、API/WS 路由。
- README 和此发板知识库。

## 完成标准

发板完成时，最终回复应包含：

- 发布版本时间戳或 release 路径。
- 六个服务的最终状态。
- Django 健康接口和受影响域名的结果。
- migration 和 collectstatic 结果。
- Celery 任务/队列验证结果（若本次涉及）。
- 当前磁盘可用空间。
- 是否发生回滚、清理或配置同步。
- 尚未验证的外部项，例如云安全组、DNS 传播、第三方密钥有效性。

不要仅回复“部署成功”。

## 当前已知配置漂移

以下状态来自 2026-08-27 的只读核对，用于提醒后续发板检查，不代表永久事实：

- `sparkservice-2026.service` 已包含六个 Compose 服务。
- root crontab 已有每 10 分钟域名检查和每天 `03:20` Certbot 续期，但未看到每天 `04:20` 项目重启。
- `domain_healthcheck.sh` 当前只检查 `spark.dreamhua.top` 与 `api.dreamhua.top`，未覆盖 `share.dreamwhale.top` 和 `chat.dreamwhale.top`。
- `portainer.dreamhua.top` 证书已过期；Portainer 若保持停用不影响业务域名，重新启用前必须处理。
- `frontend`、`open_web` 的宿主机端口映射为 `0.0.0.0`，是否可从公网直连还取决于阿里云安全组和 firewalld；生产入口仍应只允许 80/443。

每次使用 skill 时重新核对这些状态，不把历史检查结果当成当前事实。
