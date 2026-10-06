# SparkService 配置与服务矩阵

## 1. 配置来源和优先级

```text
本地 SparkService/.env
        |
        | 发板脚本覆盖并备份旧文件
        v
/root/2026/.deploy.env
        |
        +-> Docker Compose 变量替换
        +-> web env_file
        +-> celery_worker env_file
        +-> celery_beat env_file
        +-> chat_web env_file
```

`frontend` 和 `open_web` 是静态产物，Vite 配置在构建时写入 JS；运行期 `.deploy.env` 通常不会改变已生成的静态文件。

## 2. 配置变更生效矩阵

| 配置类型 | 主要消费者 | 是否重新构建 | 是否 recreate/restart |
| --- | --- | --- | --- |
| Django settings | `web` | 后端代码变化时构建 | recreate `web` |
| Celery route/beat 代码 | Worker、Beat | 是 | recreate Worker、Beat |
| `CELERY_QUEUES` | Worker | 否 | recreate Worker |
| 数据库/Redis URL | web、Worker、Beat | 否 | recreate 三个后端容器 |
| APNs/短信/邮件/OSS 密钥 | web、Worker | 否 | recreate web、Worker |
| `VITE_*` | Vite 前端 | 是 | 上传新 dist；Nginx 容器通常无需重建 |
| `NEXT_PUBLIC_*` | Next.js 客户端 bundle | 是 | 上传 standalone/static 并 recreate chat_web |
| Next.js 服务端变量 | `chat_web` | 视代码而定 | recreate chat_web |
| Nginx server/location | 宿主机 Nginx | 否 | `nginx -t` 后 reload |
| TLS 证书 | 宿主机 Nginx | 否 | renew 后 reload |
| systemd unit | systemd | 否 | daemon-reload，必要时 restart |
| crontab | cron | 否 | 保存后立即生效，需 `crontab -l` 核对 |

## 3. Django 核心配置

| 变量 | 作用 | 常见错误 |
| --- | --- | --- |
| `DJANGO_DEBUG` | 生产调试开关 | 生产误设 true 泄露错误信息 |
| `DJANGO_ALLOWED_HOSTS` | Host 白名单 | 新域名返回 DisallowedHost |
| `CSRF_TRUSTED_ORIGINS` | CSRF origin 白名单 | 缺少协议或新 Web 域名导致 403 |
| `CORS_ALLOWED_ORIGINS` | 浏览器跨域白名单 | API 正常但浏览器请求被拦截 |
| `DJANGO_SECRET_KEY` | 签名密钥 | 随意更换会影响 session/token 签名 |
| `SECURE_SSL_REDIRECT` | Django HTTPS 跳转 | Nginx 已终止 TLS 时需正确传递 X-Forwarded-Proto |
| `SECURE_HSTS_SECONDS` | HSTS | 开启前必须确认所有子域名支持 HTTPS |

## 4. 数据库与 Redis

| 变量 | 消费者 | 说明 |
| --- | --- | --- |
| `DB_ENGINE` | Django/Celery | 当前 MySQL 后端 |
| `DB_HOST`、`DB_PORT` | Django/Celery | host 网络下通常访问宿主机地址 |
| `DB_NAME`、`DB_USER`、`DB_PASSWORD` | Django/Celery | 不输出真实值 |
| `DB_CONN_MAX_AGE` | Django | 长连接复用时间 |
| `CELERY_BROKER_URL` | Worker/Beat/Web | Redis broker |
| `CELERY_RESULT_BACKEND` | Celery | 任务结果存储 |
| `CHANNEL_REDIS_URL` | Django Channels | WebSocket channel layer |

当前 MySQL 与 Redis 由 systemd 托管。Compose 容器使用 host network 的后端服务能直接访问宿主机，但这也意味着端口冲突与宿主机网络配置会直接影响容器。

## 5. Celery 队列矩阵

| 队列 | 任务类型 | 重要性 |
| --- | --- | --- |
| `celery` | 默认兼容队列 | 基础 |
| `default` | 普通默认任务 | 基础 |
| `deactivation` | 注销/停用流程 | 业务 |
| `cleanup` | 清理任务 | 运维 |
| `monitoring` | 监控任务 | 运维 |
| `notification.security.high` | OTP 等安全通知 | 高 |
| `notification.transactional` | 通知 outbox 投递 | 高 |
| `notification.bulk` | 批量活动通知 | 中 |
| `notification.receipt` | 回执轮询与对账 | 中 |
| `chat.ai` | AI 对话执行 | 高 |
| `chat.events` | 对话事件 outbox | 高 |
| `chat.recovery` | 对话恢复和超时清理 | 高 |
| `subscriptions` | RevenueCat webhook、订阅同步与对账 | 高 |

Worker 默认并发 `1`。一个 Worker 同时消费所有队列时，长耗时 AI 任务可能影响高优先级通知；当前是资源受限服务器的折中。流量增长后应拆 Worker，而不是盲目提高并发。

### RevenueCat 订阅异步任务

| 任务 | 队列 | 触发方式 |
| --- | --- | --- |
| `subscriptions.tasks.process_revenuecat_webhook_event` | `subscriptions` | RevenueCat webhook 入箱后投递 |
| `subscriptions.tasks.sync_revenuecat_user_task` | `subscriptions` | 用户同步或可重试同步 |
| `subscriptions.tasks.reconcile_revenuecat_subscriptions_task` | `subscriptions` | Beat 每 6 小时 |
| `subscriptions.tasks.retry_pending_revenuecat_webhooks_task` | `subscriptions` | Beat 每 15 分钟 |

新增任务上线必须同时检查：`subscriptions` 已加入 `.env` 的 `CELERY_QUEUES`、Worker `inspect registered` 能看到 4 个任务、`inspect active_queues` 正在消费该队列，且 Beat 日志没有调度表或导入错误。

## 6. 通知配置

### APNs

必须形成一致组合：

```text
APNS .p8 Key + Key ID + Team ID + Topic(Bundle ID) + Sandbox/Production + Device Token
```

`BadDeviceToken` 通常是 token 与 sandbox/production、bundle ID 不匹配，或 token 已失效。任务已入队、Celery 成功执行，并不能证明手机收到通知。

### 邮件、短信、OSS

- 邮件：Host、端口、SSL/TLS 组合和授权码必须匹配。
- 短信：AccessKey、签名、模板代码和参数格式必须匹配供应商控制台。
- OSS/STS：Endpoint、Region、Bucket、Role ARN 必须一致；不要把北京 endpoint 与上海 region 混用。

这些配置通常被 Web 请求和 Celery 任务共同消费，变更后至少 recreate `web` 与 `celery_worker`。

## 7. Apple Web 登录与 chat-web

关键变量：

- `SPARK_WEB_SERVICE_ID`
- `SPARK_APPLE_AUTHORIZE_URL`
- `SPARK_APPLE_WEB_REDIRECT_URI`
- `APPLE_WEB_SERVICE_IDS`
- `APPLE_WEB_ALLOWED_REDIRECT_URIS`
- `APPLE_WEB_JWKS_VERIFY_SSL`
- `WEB_AUTH_SERVICE_ID`
- `NEXT_PUBLIC_SPARK_WS_BASE_URL`
- `CHAT_WEB_PORT`

Apple Developer 控制台的 Service ID、Return URL 与服务端 redirect URI 必须逐字符一致，包括协议、域名、路径和尾斜杠。

## 8. 分享和公开站点

关键变量：

- `MEDICAL_SHARE_WEB_BASE_URL`
- `MEDICAL_SHARE_DOWNLOAD_URL`
- `CONTENT_SHARE_WEB_BASE_URL`
- `CONTENT_TRUSTED_ASSET_HOSTS`
- `CONTENT_PUBLIC_CACHE_MAX_AGE`

分享 URL 必须指向 `share.dreamwhale.top` 的 open-web 页面。Nginx 的 `/api/` 再代理到 Django；不能把整个分享域名直接代理到后端首页。

## 9. 服务依赖和启动顺序

```text
network-online
  ├─ mysqld
  ├─ redis
  ├─ docker
  └─ nginx
       |
       v
sparkservice-2026.service
  ├─ web
  ├─ celery_worker
  ├─ celery_beat
  ├─ frontend
  ├─ open_web
  └─ chat_web
```

systemd unit 当前 `Wants` MySQL 与 Redis，并在 Docker、MySQL、Redis 之后启动应用。`Wants` 不等于依赖一定成功；应用健康检查仍需验证。

## 10. 端口与公网边界

| 端口 | 进程 | 期望公网状态 |
| ---: | --- | --- |
| 22 | SSH | 受控来源开放 |
| 80 | Nginx HTTP/ACME | 开放 |
| 443 | Nginx HTTPS | 开放 |
| 2026 | Daphne | 不直接公网开放 |
| 6018 | 后台 Nginx 容器 | 不直接公网开放 |
| 2028 | open-web Nginx 容器 | 不直接公网开放 |
| 9001 | Next.js | 不直接公网开放 |
| 3306 | MySQL | 不直接公网开放 |
| 6379 | Redis | 仅本机 |

监听 `0.0.0.0` 不自动等于公网可访问，但必须同时检查 firewalld 和阿里云安全组。
