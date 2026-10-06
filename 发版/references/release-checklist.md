# SparkService 发板检查清单

这份清单用于一次真实生产发板。勾选项不是形式要求，每项都对应曾经出现过的部署风险。

## 一、确认发布范围

- [ ] 本次发布的目标服务器是 `139.196.215.51`，目标目录是 `/root/2026`。
- [ ] 源码来自 `/Users/hua/Documents/project/Reference/SparkService`。
- [ ] 服务器模板来自 `/Users/hua/Documents/project/Reference/2026`。
- [ ] 没有误用旧的 `/Users/hua/Downloads/Reference`。
- [ ] 没有修改 `/root/8000` 或旧项目。
- [ ] 已知道本次变更涉及后端、后台前端、开放端、对话端、Celery、数据库、配置、域名中的哪些部分。
- [ ] 已记录当前 Git 分支、提交或可识别的工作区状态。
- [ ] 已确认用户工作区中的未提交改动属于本次应发布内容。

## 二、代码质量和依赖

- [ ] Django system check 通过。
- [ ] 与本次变更相关的自动化测试通过。
- [ ] `requirements.txt` 与实际 Python import 一致。
- [ ] 三个前端的 `package.json` 与 `pnpm-lock.yaml` 一致。
- [ ] 没有把 `.env`、证书私钥、APNs `.p8` 或数据库导出文件误加入发布包。
- [ ] 新增系统依赖已写入 Dockerfile，并使用服务器可稳定访问的软件源。
- [ ] 新增 Python 包与 Python 3.12 兼容。

建议命令：

```bash
cd /Users/hua/Documents/project/Reference/SparkService
python manage.py check
python manage.py makemigrations --check --dry-run
```

## 三、数据库迁移

- [ ] 模型变化已有本地迁移文件。
- [ ] 已阅读迁移 SQL 或至少审查迁移操作类型。
- [ ] 大表增加非空字段、索引、字段类型变化已评估锁表时间。
- [ ] 数据迁移具备幂等性，重复执行不会产生重复或破坏数据。
- [ ] 删除字段、删除表和不可逆 `RunPython` 已准备回退方案。
- [ ] 重大迁移前已确认数据库备份可用。
- [ ] 没有把 `run_all_migration.sh` 的全量重置流程误当作普通发板迁移。

高风险迁移包括：

- 大表直接增加带默认值的非空字段。
- 修改主键、唯一约束或外键。
- 删除列、改列类型、重命名后立即删除兼容代码。
- 一次性扫描和更新大量历史数据。
- 依赖旧版本代码仍在运行的 schema 变化。

## 四、生产环境变量

- [ ] 本地 `.env` 确认是生产配置，不是本地开发配置。
- [ ] `DJANGO_DEBUG=false`。
- [ ] `DJANGO_ALLOWED_HOSTS` 包含所有业务域名。
- [ ] `CSRF_TRUSTED_ORIGINS` 使用完整 `https://` origin。
- [ ] `CORS_ALLOWED_ORIGINS` 与实际 Web 客户端一致。
- [ ] 数据库、Redis、邮件、短信、OSS、APNs、Apple Web 登录配置完整。
- [ ] `APNS_USE_SANDBOX` 与 App 构建环境匹配。
- [ ] `APNS_TOPIC` 与 App Bundle ID 匹配。
- [ ] `CELERY_QUEUES` 包含代码路由使用的所有 queue。
- [ ] RevenueCat 订阅任务使用的 `subscriptions` queue 已包含在本地 `.env` 和服务器 `.deploy.env`。
- [ ] `SPARK_APPLE_WEB_REDIRECT_URI` 与 Apple Developer 后台配置完全一致。
- [ ] `MEDICAL_SHARE_WEB_BASE_URL`、`CONTENT_SHARE_WEB_BASE_URL` 指向当前分享域名。
- [ ] `.env` 没有重复变量导致后面的值覆盖前面的值。

不要在终端或对话里整体输出 `.env`。检查配置时优先打印键名、布尔值、域名和非敏感开关。

## 五、本地发板预检

- [ ] `ssh`、`scp`、`rsync`、`pnpm`、`tar` 可用。
- [ ] 三个前端锁文件存在。
- [ ] `chat-web/next.config.ts` 已启用 standalone。
- [ ] 服务器 SSH 可免交互连接。
- [ ] 服务器磁盘低于阻断阈值。
- [ ] Docker、MySQL、Redis、Nginx 处于 active。
- [ ] `/root/2026/.deploy.env` 存在且权限为 `600`。
- [ ] `/root/2026/current` 指向有效 release。

```bash
bash /Users/hua/Documents/Skill/发版/scripts/release_preflight.sh --remote
```

## 六、本地构建产物

- [ ] `backoffice-web/dist/index.html` 生成成功。
- [ ] `open-web/dist/index.html` 生成成功。
- [ ] `chat-web/.next/standalone/server.js` 生成成功。
- [ ] `chat-web/.next/static` 已上传。
- [ ] `chat-web/public` 存在时已上传。
- [ ] 构建时使用的 API、WebSocket 地址属于生产环境。
- [ ] 构建失败时没有继续上传上一次残留产物。

## 七、远端发布过程

- [ ] 旧部署进程的取消动作只针对明确的 `deploy_remote.sh`。
- [ ] 服务器模板同步没有覆盖 `.deploy.env` 和 `shared`。
- [ ] 旧 `.deploy.env` 已生成时间戳备份。
- [ ] 新 release 中存在 `manage.py`。
- [ ] 三个共享前端产物检查通过。
- [ ] 后端镜像构建成功。
- [ ] MySQL `3306` 和 Redis `6379` 可连接。
- [ ] `makemigrations --check --dry-run` 通过。
- [ ] `migrate --noinput` 通过。
- [ ] `collectstatic --noinput` 通过。
- [ ] 六个应用服务全部启动。
- [ ] Django 健康检查最终成功。
- [ ] releases、uploads 各保留最近 8 个。

## 八、发板后业务验收

- [ ] `2026-web-1` 为 healthy。
- [ ] `2026-frontend-1` 为 healthy。
- [ ] `2026-open_web-1` 为 healthy。
- [ ] `2026-chat_web-1` 为 healthy。
- [ ] `2026-celery_worker-1` 为 running，日志没有启动异常。
- [ ] `2026-celery_beat-1` 为 running，日志没有数据库表或调度异常。
- [ ] `https://api.dreamhua.top/health/` 返回 2xx。
- [ ] `https://spark.dreamhua.top/` 返回 2xx/3xx。
- [ ] `https://share.dreamwhale.top/` 返回 2xx/3xx。
- [ ] `https://chat.dreamwhale.top/login` 返回 2xx/3xx。
- [ ] 对话域名 `/api/` 能到 Django。
- [ ] 对话域名 `/ws/` 的 Upgrade 代理存在。
- [ ] 分享链接 `/s/<slug>` 能落到 open-web，而不是后台首页。
- [ ] 最近 30 分钟容器日志无新增 Traceback、ProgrammingError、OperationalError。

```bash
bash /Users/hua/Documents/Skill/发版/scripts/post_release_audit.sh
```

## 九、Celery 验收

- [ ] Worker `inspect ping` 有响应。
- [ ] 新 task 出现在 `inspect registered`。
- [ ] 已删除 task 不再出现在 `inspect registered`，避免旧镜像或旧 import 仍在运行。
- [ ] Worker active queues 包含 task route 使用的 queue。
- [ ] Beat schedule 包含新增周期任务。
- [ ] RevenueCat 的每 6 小时对账和每 15 分钟 webhook 重试任务均已注册并可由 Beat 调度。
- [ ] `django_celery_beat_periodictask` 与 `periodictasks` 表存在。
- [ ] Redis broker 可用。
- [ ] 必要时投递一条无副作用的测试任务并确认成功。
- [ ] 通知类任务同时验证供应商返回，不把“已入队”误认为“已送达”。

## 十、自动运维验收

- [ ] `sparkservice-2026.service` enabled，且启动清单包含六个服务。
- [ ] Docker、MySQL、Redis、Nginx 开机自启。
- [ ] 每 10 分钟域名健康检查存在。
- [ ] 每天 `03:20` Certbot 续期检查存在，deploy hook 会 reload Nginx。
- [ ] 每天 `04:20` 项目重启存在，或明确记录未启用原因。
- [ ] 域名健康脚本覆盖当前四个业务域名。
- [ ] 证书没有在 30 天内到期，停用域名除外。
- [ ] 公网安全组原则上只开放 80、443 和受控 SSH。

## 十一、发板结束记录

- [ ] 填写 release 时间戳与 `current` 目标。
- [ ] 记录迁移结果和容器状态。
- [ ] 记录四个域名结果。
- [ ] 记录磁盘、内存和 swap 状态。
- [ ] 记录清理、回滚和异常。
- [ ] 保存本次尚未处理的风险和负责人。

使用 [发板记录模板](../templates/release-record-template.md) 留档。
