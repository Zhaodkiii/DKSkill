# 项目发现清单

## 项目级

- [ ] 项目入口和构建入口。
- [ ] 主要语言和框架。
- [ ] 依赖注入/Composition Root。
- [ ] 路由和导航。
- [ ] 环境配置。
- [ ] 网络层和 API 入口。
- [ ] 会话、认证和权限。
- [ ] 数据库、文件和缓存。
- [ ] 后台任务、通知和生命周期。
- [ ] 外部服务和 SDK。
- [ ] 测试结构。
- [ ] 日志和监控。
- [ ] 已有文档。
- [ ] 新旧实现和重复职责。

## 功能级

- [ ] 用户入口或系统触发器。
- [ ] View/Controller/Route。
- [ ] ViewModel/Coordinator。
- [ ] UseCase/Application Service。
- [ ] Domain Model/Protocol。
- [ ] Repository/Gateway。
- [ ] API/Database/Platform Adapter。
- [ ] 输入、输出和错误模型。
- [ ] 状态转换。
- [ ] 持久化和缓存。
- [ ] 权限和敏感数据。
- [ ] 并发、去重和幂等。
- [ ] 失败、重试和清理。
- [ ] 单元和集成测试。
- [ ] 文档与代码差异。

## 最小只读命令参考

```bash
rg --files <project>
find <project> -maxdepth 4 -type d
rg -n "App|main|Router|Coordinator|Container|Repository|UseCase|Service" <project>
rg -n "token|session|cache|retry|error|logout|clear" <project>
```

命令只是发现工具。最终结论必须通过读取关键文件确认。
