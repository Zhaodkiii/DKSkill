# SparkService 发板记录

## 基本信息

| 项目 | 内容 |
| --- | --- |
| 发板时间 | YYYY-MM-DD HH:mm:ss CST |
| 操作人 |  |
| 目标服务器 | `139.196.215.51` |
| 目标目录 | `/root/2026` |
| 发布版本 | `releases/YYYYMMDD_HHMMSS` |
| 发布包 | `uploads/sparkservice_YYYYMMDD_HHMMSS.tgz` |
| Git 分支/提交 |  |
| 变更摘要 |  |

## 影响范围

- [ ] Django API
- [ ] 数据库 schema/data
- [ ] Celery Worker
- [ ] Celery Beat
- [ ] 后台前端
- [ ] 开放端前端
- [ ] AI 对话前端
- [ ] 环境变量
- [ ] Nginx/域名/证书
- [ ] systemd/crontab

## 发布前状态

| 检查 | 结果 |
| --- | --- |
| 预检失败/提醒 |  |
| 磁盘 |  |
| 内存/Swap |  |
| 当前 release |  |
| 数据库备份 |  |
| 回滚版本 |  |

## 数据库

| 项目 | 结果 |
| --- | --- |
| `makemigrations --check --dry-run` |  |
| `migrate --noinput` |  |
| 迁移文件 |  |
| 是否包含不可逆迁移 |  |
| 回退方案 |  |

## 服务状态

| 服务 | 状态 | 说明 |
| --- | --- | --- |
| `web` |  |  |
| `celery_worker` |  |  |
| `celery_beat` |  |  |
| `frontend` |  |  |
| `open_web` |  |  |
| `chat_web` |  |  |

## 域名验收

| 地址 | HTTP | 说明 |
| --- | ---: | --- |
| `https://api.dreamhua.top/health/` |  |  |
| `https://spark.dreamhua.top/` |  |  |
| `https://share.dreamwhale.top/` |  |  |
| `https://chat.dreamwhale.top/login` |  |  |

## Celery 验收

| 检查 | 结果 |
| --- | --- |
| Worker ping |  |
| 新任务 registered |  |
| active queues |  |
| Beat schedule |  |
| RevenueCat 任务 registered |  |
| `subscriptions` active queue |  |
| 最近错误日志 |  |

## 异常和处置

| 时间 | 现象 | 根因 | 处理 | 结果 |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## 最终结论

- 发布结果：成功 / 已回滚 / 部分完成 / 失败
- 最终 release：
- 是否清理旧版本：
- 是否恢复旧配置：
- 遗留风险：
- 后续负责人：
