# SparkService 发板知识手册

## 1. 发布架构

```text
本地 SparkService 源码
  ├─ backoffice-web -> pnpm build -> shared/frontend-dist
  ├─ open-web       -> pnpm build -> shared/open-web-dist
  ├─ chat-web       -> pnpm build -> shared/chat-web-standalone
  ├─ .env           -> /root/2026/.deploy.env
  └─ Django 源码    -> uploads/sparkservice_*.tgz
                            |
                            v
                     releases/<时间戳>
                            |
                         current
                            |
                      build/current
                            |
                    Docker Compose build/up
```

本地脚本负责准备产物、同步配置和上传；远端脚本负责版本目录、镜像、迁移、启动、健康检查和历史清理。

`current` 是可审计的版本指针，`build/current` 是 Docker 构建上下文。前端产物位于 `shared`，不随 release 软链回滚，这是当前架构的重要边界：代码回滚不会自动回滚三个前端产物。

## 2. 本地发布入口

入口：

```text
/Users/hua/Documents/project/Reference/SparkService/scripts/deploy_sparkservice.sh
```

主要开关：

| 变量 | 默认值 | 作用 |
| --- | --- | --- |
| `REMOTE_HOST` | `root@139.196.215.51` | 远端 SSH |
| `REMOTE_BASE` | `/root/2026` | 服务器部署根目录 |
| `DEPLOY_ENV_FILE` | `SparkService/.env` | 生产配置来源 |
| `SYNC_DEPLOY_ENV` | `1` | 是否覆盖服务器 `.deploy.env` |
| `BUILD_FRONTEND_LOCAL` | `1` | 构建后台前端 |
| `BUILD_OPEN_WEB_LOCAL` | `1` | 构建开放端前端 |
| `BUILD_CHAT_WEB_LOCAL` | `1` | 构建 AI 对话前端 |
| `USE_RSYNC` | `1` | 优先 rsync 上传代码 |
| `CANCEL_RUNNING_DEPLOY` | `1` | 清理未完成旧部署进程 |
| `VITE_API_BASE_URL` | `https://api.dreamhua.top` | 后台前端 API |
| `OPEN_WEB_API_BASE_URL` | 空 | 使用同域 `/api/` |
| `NEXT_PUBLIC_SPARK_WS_BASE_URL` | 空 | 使用对话域名同域 `/ws/` |

本地构建是为了避免 2C2G 服务器同时承受 pnpm、Vite、Next.js 和 Docker 后端构建压力。

## 3. 上传排除规则

发布包应排除：

- `.git`、IDE 配置、虚拟环境。
- Python 缓存、测试缓存、本地日志和 SQLite。
- 所有 `node_modules`。
- 三个前端构建输出。
- 本地 `.env`。
- 旧 `share-web`。
- 本地发板脚本本身。

不要把本地媒体、日志、数据库或运行目录上传为发布代码。

## 4. 远端目录职责

```text
/root/2026/
  bin/                    运维入口
  build/current/          Docker 后端构建快照
  current -> releases/... 当前代码软链
  docker/                 Dockerfile 和容器配置
  releases/               历史代码版本，保留 8 个
  shared/
    backups/              备份
    frontend-dist/        后台前端静态产物
    open-web-dist/        开放端静态产物
    chat-web-standalone/  Next.js standalone 产物
    logs/                 持久日志
    media/                持久媒体
    staticfiles/          Django 静态文件
  uploads/                发布压缩包，保留 8 个
  .deploy.env             真实生产配置，权限 600
  docker-compose.yml
```

`releases` 可重新生成代码版本，`shared` 是持久数据。清理命令不能跨越这个边界。

## 5. 远端发布顺序

`deploy_remote.sh` 的顺序：

1. 读取 `.deploy.env`。
2. 合并必须存在的 Celery queues。
3. 创建新 release 并解压包。
4. 检查 `manage.py`。
5. 切换 `current`。
6. 复制到 `build/current`。
7. 检查三个前端产物。
8. 构建 `web`、`celery_worker`、`celery_beat` 后端镜像。
9. 检查宿主机 MySQL 和 Redis。
10. 检查是否遗漏迁移文件。
11. 执行数据库迁移。
12. 收集 Django 静态文件。
13. 启动六个应用服务并移除孤儿容器。
14. 强制 recreate `chat_web`，使新 standalone 产物生效。
15. 最多等待约 60 秒验证 Django 健康接口。
16. 清理超过 8 个的 release 和 upload。
17. 打印 Compose 状态。

## 6. 生产迁移原则

常规流程：

```text
本地 makemigrations -> 审查迁移文件 -> 跟随代码上传
远端 makemigrations --check --dry-run -> migrate --noinput
```

`makemigrations` 不是每次生产发布都必须执行的写操作；必须做的是检查模型变化是否已有迁移文件，以及执行 `migrate`。在生产自动生成迁移会带来不可重复和难审计风险。

历史全量迁移 `run_all_migration.sh` 与常规发板是两种流程。全量迁移可能重置数据库并停止服务，不能混入普通发布。

## 7. Celery 完整性

Celery 由两个容器承担不同职责：

- `celery_worker`：真正执行任务。
- `celery_beat`：产生周期任务消息，使用 `django_celery_beat.schedulers:DatabaseScheduler`。

任务上线要同时满足四层：

1. task 模块被 Celery autodiscover/import。
2. `CELERY_TASK_ROUTES` 把 task 路由到正确 queue。
3. `CELERY_QUEUES` 和 Worker `--queues` 包含该 queue。
4. 周期任务同时出现在代码 beat schedule 或 `django_celery_beat_periodictask` 数据中。

Web AI 当前任务：

- `run_chat`、`resume_chat_run` -> `chat.ai`
- `relay_chat_event_outbox` -> `chat.events`
- `recover_chat_runs`、`expire_chat_interactions` -> `chat.recovery`

RevenueCat 订阅任务：

- `process_revenuecat_webhook_event`、`sync_revenuecat_user_task` -> `subscriptions`
- `reconcile_revenuecat_subscriptions_task`、`retry_pending_revenuecat_webhooks_task` -> `subscriptions`，分别由 Beat 每 6 小时、每 15 分钟触发

知识库已收敛为客户端 Push/Pull 同步，以下异步索引任务必须不再注册：

- `index_document_task`
- `rebuild_index_version_task`
- `extract_document_task`

它们此前复用 `chat.ai` 队列；删除任务不等于删除 `chat.ai`，因为 `run_chat` 和 `resume_chat_run` 仍依赖该队列。远端发布脚本会同时验证“保留任务存在”和“旧任务不存在”。

Beat 容器运行但缺 `django_celery_beat_periodictasks` 表时，会持续失败；应修复迁移，不能靠重启掩盖。

## 8. 前端发布差异

### backoffice-web

- Vite 静态站点。
- 本地产出 `dist/`。
- 上传到 `shared/frontend-dist`。
- Nginx 容器监听宿主机 `6018`。

### open-web

- Vite 静态站点。
- 本地产出 `dist/`。
- 上传到 `shared/open-web-dist`。
- Nginx 容器监听宿主机 `2028`。
- `share.dreamwhale.top` 页面到 `2028`，`/api/` 到后端 `2026`。

### chat-web

- Next.js 服务端应用，不是普通静态 dist。
- `next.config.ts` 必须 `output: "standalone"`。
- 上传 `.next/standalone`、`.next/static` 和可选 `public`。
- Node 容器以 `node server.js` 运行，宿主机端口 `9001`。
- `chat.dreamwhale.top` 页面到 `9001`，`/api/`、`/ws/` 到后端 `2026`。
- 更新挂载目录内容后需要 recreate 容器。

## 9. Nginx 与 HTTPS

宿主机 Nginx 是唯一公网入口，公网原则上只开放 `80/443`。应用端口不应通过云安全组直接暴露。

域名映射：

| 域名 | 上游 |
| --- | --- |
| `spark.dreamhua.top` | `127.0.0.1:6018` |
| `api.dreamhua.top` | `127.0.0.1:2026` |
| `share.dreamwhale.top` | 页面 `127.0.0.1:2028`，API `127.0.0.1:2026` |
| `chat.dreamwhale.top` | 页面 `127.0.0.1:9001`，API/WS `127.0.0.1:2026` |

新增域名的顺序：DNS A 记录生效、HTTP ACME challenge、Certbot 申请证书、配置 HTTPS server、`nginx -t`、reload、外部验证。证书续期后必须 reload Nginx。

## 10. 资源限制

当前 2C2G 服务器的 Compose 限制：

| 服务 | CPU | 内存 |
| --- | ---: | ---: |
| `web` | `0.80` | `768m` |
| `celery_worker` | `0.60` | `512m` |
| `celery_beat` | `0.25` | `256m` |
| `frontend` | `0.25` | `128m` |
| `open_web` | `0.25` | `128m` |
| `chat_web` | `0.35` | `256m` |

总限制高于物理内存不代表会立即耗尽，但峰值仍可能触发 swap。Worker 并发默认 `1`，不要在没有压测和内存评估时增加。

容器日志必须轮转，单文件约 `10m` 或 `20m`，保留 `3` 个。基础设施服务使用 systemd，避免额外容器常驻开销。

## 11. 自动恢复和定时任务

- Compose 服务使用 `restart: unless-stopped`。
- `sparkservice-2026.service` 应在开机后启动六个应用服务。
- 项目每天 `04:20` 自动重启。
- 域名健康检查建议每 10 分钟运行。
- Certbot 每天 `03:20` 检查续期，续期后 reload Nginx。
- 日志默认保留 30 天。

发板新增服务时，只改 Compose 不够；systemd、定时重启、start/stop/rollback/status 脚本都要同步。

## 12. 回滚边界

自动回滚能恢复：

- `current` 代码软链。
- 后端 Docker 构建上下文和镜像。
- 六个服务的运行。

自动回滚不能天然恢复：

- 已执行的数据库 schema/data 迁移。
- 已覆盖的 `.deploy.env`，只能使用 `.deploy.env.bak_<时间戳>` 手动恢复。
- 已覆盖的三个 `shared` 前端产物。
- 外部 DNS、证书和 Nginx 配置。

因此重大版本需要数据库备份、环境配置备份和前端产物版本化。当前脚本已有配置备份，但前端产物仍是共享目录覆盖式发布，这是需要持续优化的点。

## 13. 常见误判

- `Container ... Started`：只代表进程已拉起，不代表健康。
- `health: starting`：启动窗口内正常，最终必须变成 healthy。
- 首两次 `curl connection refused`：Daphne 尚未监听时可能正常，看最终重试。
- Beat `Up`：不代表数据库调度表存在或消息成功发出。
- APNs `BadDeviceToken`：属于设备 token/环境/bundle 组合问题，不是 Celery 容器是否运行的问题。
- HTTPS 可访问：不代表内部端口没有被安全组额外暴露。
- 代码回滚成功：不代表数据库和前端也已回滚。

## 14. 建议的后续工业化优化

按优先级：

1. 前端产物按 release 版本保存，让回滚覆盖前后端。
2. 发布前自动备份数据库，并为危险迁移写可执行回退脚本。
3. 将本地 `.env` 整体覆盖改为受控变量清单或密钥管理服务。
4. 给发布包、前端产物和镜像记录同一版本号与校验和。
5. 健康检查从单一 Django `/health/` 扩展到六个服务和关键依赖。
6. 发板后自动检查 Celery registered、active queues 和 Beat schedule。
7. 对磁盘使用率设置硬门槛，例如超过 85% 禁止开始 Docker build。
8. 发布锁改为可靠的单实例锁和明确的人工 `--cancel-running`，避免默认终止合法发布。
9. 增加结构化发布日志和发布结果清单，方便审计。
10. 有条件时使用 CI runner 构建不可变产物，减少对开发者 Mac 环境的依赖。
