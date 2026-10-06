# iOS–HarmonyOS 可复用对照知识库

本知识库由“小鲸多客户端互通”技能维护，只收录经过代码或官方资料核验、可泛化且不含私密信息的事实。使用技能时先读此文件；发现新事实时按“新增条目格式”追加。

## 1. 当前已验证的工程与证据

| 主题 | iOS 证据 | HarmonyOS 证据 | 已验证结论 | 验证日期 |
| --- | --- | --- | --- | --- |
| 统一网络组合根 | `SupportClient/SupportClient/Core/Networking/SupportBackend.swift` | HarmonyOS 目标工程当前为空模板 | iOS `SupportBackend` 负责组装 Engine、缓存、TokenProvider 与领域 API；HarmonyOS 应建立同等的 Composition Root，不让页面 new HTTP 客户端。 | 2026-07-18 |
| HTTP 拦截器边界 | iOS `SupportNetworkEngine.swift` / `SupportNetworkTransport.swift` | `.../LiveStreaming/commons/utils/src/main/ets/network/interceptor/CallServerInterceptor.ts` | HTTP 发送应位于调用链的最后一层，API 层不直接发请求；示例使用 `@ohos/axios`，生产可改为系统 HTTP Transport。 | 2026-07-18 |
| 统一 JSON 处理 | iOS `API/Common/SupportAPIResponseDecoder.swift` | `.../LiveStreaming/.../JsonResponseInterceptor.ts` | JSON Header/解析应该集中化；项目必须兼容 JSON 与二进制 body，不能沿用示例“ArrayBuffer 不支持”。 | 2026-07-18 |
| Token Header / 单次重放 | iOS `AuthTokenProvider.swift`、`SupportNetworkEngine.swift` | `.../LiveStreaming/.../TokenHeaderInterceptor.ts`、`TokenRefreshInterceptor.ts` | Header 注入集中；刷新成功后原请求最多重放一次。示例没有安全存储、刷新单飞和失效分类，不能直接生产使用。 | 2026-07-18 |
| 网络状态 | iOS `Foundation/NetworkPathMonitor.swift` | `.../LiveStreaming/commons/utils/src/main/ets/utils/NetConnectionUtil.ts` | HarmonyOS 可用 Network Kit `connection` 的网络连接事件实现监听；必须增加首次评估状态和生命周期注销。 | 2026-07-18 |
| 普通持久化 | iOS `Caching/DeviceCache.swift` | `.../LiveStreaming/.../storage/preference/PreferenceUtil.ts` | Preferences 适合普通设备/账号元数据；示例打印完整 value，生产需移除；凭证禁止保存其中。 | 2026-07-18 |
| 独立网络模块 | iOS `Projects/Core/Networking/` | `.../NewsTemplate/News/commons/network/` | 随业务增长，HarmonyOS 网络底座可作为独立 commons/HAR 模块；先以真实入口模块依赖图为准，不能机械拆分。 | 2026-07-18 |
| 资源与多语言 | iOS `SupportClient/SupportClient/Projects/App/Resources/en.lproj/Localizable.strings`、`zh-Hans.lproj/Localizable.strings`、`InfoPlist.strings` | HarmonyOS `SupportClientHuawei/AppScope/resources/base/element/string.json`、`SupportClientHuawei/entry/src/main/resources/base/element/string.json`、`AppScope/app.json5`、官方 `resource-categories-and-access` / `js-apis-i18n-V5` | iOS 用语言目录拆分文案与应用信息；HarmonyOS 需用资源键 + locale/i18n 管理 + 语言目录/资源分层实现同类效果，页面硬编码文本不可复用。 | 2026-07-18 |
| 资源 JSON 访问 | iOS bundle 内静态配置/种子数据 | HarmonyOS 官方 FAQ：`resources` 下 JSON 推荐放 `rawfile`，并通过 `getRawFileContent` 访问 | 应用静态 JSON 种子应优先放 rawfile；不要假设 `element/string.json` 可以承载任意 JSON 数据。 | 2026-07-18 |
| HarmonyOS 运行时日志 | iOS `Foundation/` 日志职责、项目总览中的可观测性约束 | `.../HouseAndHomeTemplate/RentAndBuy/components/aggregated_login/src/main/ets/common/Logger.ets`、`.../SportTemplate/StepCount/components/module_bmiassess/src/main/ets/components/EditUserInfo.ets` | HarmonyOS ArkTS 运行时日志应以 `hilog` 为底座，统一封装等级、前缀与输出格式；页面级 `hilog` 只可作参考，不应扩散为业务层打印。 | 2026-07-18 |
| 设备日志查看 | iOS 开发态调试与诊断 | `hdc` 官方命令 | HarmonyOS 可通过 `hdc shell hilog -w start/stop` 获取设备端日志，并用 `hdc file recv /data/log/hilog` 导出；适用于开发态诊断，不是应用运行时能力。 | 2026-07-18 |
| 主框架 Navigation+Tabs | iOS `AppCoordinatorView.swift` 中的 `TabView` + `NavigationStack` | `.../HouseAndHomeTemplate/HomeDecoration/products/entry/src/main/ets/pages/MainEntry.ets`、`.../HouseAndHomeTemplate/RentAndBuy/product/entry/src/main/ets/pages/Index.ets` | HarmonyOS 主框架可用 `Navigation` 作为根容器、内部组合 `Tabs` 和 `TabContent`；tab 状态应由局部 controller 或状态对象管理，而非全局单例。 | 2026-07-18 |
| 登录 sheet 与局部路由 | iOS `LoginView.swift` / `PhoneLoginView.swift` 的登录页与 OTP 子页、`sheet` 升级登录 | `.../LifestyleAndServiceTemplate/GovernmentService/Application/components/aggregated_login/src/main/ets/utils/LoginSheetUtils.ets`、`.../LifestyleAndServiceTemplate/GovernmentService/Application/components/aggregated_login/src/main/ets/viewmodel/AggregatedLoginVM.ets` | 半模态登录容器和 `NavPathStack.pushPathByName` 可复用到 HarmonyOS 登录/升级登录场景；第三方 SDK、AppId 和明文测试数据不可复制。 | 2026-07-18 |
| UIAbility 与 Stage 入口 | iOS `SupportClientApp.swift` / `ContentView.swift` 的根壳和路由入口 | `entry/src/main/ets/entryability/EntryAbility.ets`、`entry/src/main/ets/pages/Index.ets` | 入口壳与页面应解耦；业务导航应从根页面状态驱动，不要把生命周期回调直接写成页面路由器。 | 2026-07-18 |
| 日志字段白名单 | iOS `Foundation/Logger.swift` 的 `LogLevel`、`LogModule`、阈值过滤与 200 字符单行截断 | `@kit.PerformanceAnalysisKit` 的 `hilog`，及 `MoneyTrack/.../utils/Logger.ets` | HarmonyOS Logger 应先构造 allowlist 事件再脱敏/截断/输出；禁止将 `JSON.stringify(err)`、请求对象、headers 或 body 作为生产日志。模块枚举、阈值过滤和单行截断应与 iOS 行为对齐。 | 2026-07-18 |
| 路由并发与账号隔离 | iOS `AppCoordinatorView.swift` 的 `preparedAccountID` 门禁与独立 `NavigationStack` | HarmonyOS `Navigation`/`NavPathStack`，`EntryAbility.ets` Stage 入口 | 根路由应以会话 generation 串行消费外部事件；账号切换/失效必须清空账号级页面栈，旧异步回调 generation 不匹配时丢弃。不能从网络/通知回调直接操作任意页面栈。 | 2026-07-18 |
| 资源引用完整性 | iOS App 资源按 `Localizable.strings`、`InfoPlist.strings` 和 Assets 管理 | HarmonyOS `app.json5` / `module.json5` 的 `$string`、`$media`、`$color` 引用 | 配置引用的每一个资源键必须在基线资源存在；基线缺键是构建阻断项，不可用页面硬编码补救。locale 限定目录及应用内语言切换 API 必须以目标 SDK POC 验证。 | 2026-07-18 |
| 应用内通知边界 | iOS `Projects/Core/Notification/`、`App/Notification/NotificationHostView.swift`、`NotificationInboxStore.swift` | HarmonyOS ArkUI `AppStorage` / `PromptAction` / Core File Kit `file.fs` / NotificationManager 官方资料，`SupportClientHuawei/App/NotificationHost.ets` | 前台应用内 toast/banner/alert 应优先用 ArkUI 根 Host + 状态对象 + 本地队列实现；通知历史用应用私有文件并明确账号隔离；系统 `NotificationManager` 属于 Push/后台通知边界，不应为普通应用内提示强制申请系统通知权限。 | 2026-07-18 |
| 同一后端交付契约 | `SparkService/SparkService/urls.py`、`common/response.py`、`common/exception_handlers.py`、`common/middleware/request_id_middleware.py` | iOS/HarmonyOS 客户端网络层及功能方案 | 同一服务端工程的路由、DTO/Serializer、服务、权限、响应包裹、HTTP/业务错误码与 request ID 是多端和后台管理的唯一事实源；客户端只能做平台适配，后台管理不得形成独立业务真相。发现漂移必须显式记录并收敛。 | 2026-07-18 |
| ArkTS 实现编译门 | `SparkClientHarmonyOS` API 24 的 Hvigor `assembleHap` 实测；目标文件 `entry/src/main/ets/Core/AI/**`、`App/AppBootstrapper.ets`、`AISettingsPage.ets` | ArkTS 编译器实际阻断：领域类直接转 `Record`、indexed access type、任意类型 `throw`、catch 后直接重抛、ArkUI `ForEach` 隐式参数类型；修复后 `CompileArkTS` 与 `assembleHap` 均通过 | 领域对象必须通过显式 mapper/fromJson 转换；联合类型用解析函数；异常统一为 `Error` 子类或结果状态；UI 回调显式元素/key 类型；构建前扫描这些模式。完整构建还需确认 `DEVECO_SDK_HOME` 和 DevEco JDK 的 `Contents/Home`，签名警告与编译错误分开记录。 | 2026-07-21 |
| ArkUI Builder 组件树语法 | `AISettingsPage.ets`、`Providers/ProviderEditorPage.ets` 的 HarmonyOS AI 设置页面 | `build/@Builder` 内组件根节点前的局部变量会触发 Rollup `Unexpected token`、`Only UI component syntax can be written here`，并可能级联成多根节点错误 | 路由参数和数据查找移到普通显式类型方法；`build/@Builder` 从 `Navigation`、`Column` 等组件调用开始；`@Entry` 页面保持单一容器根节点。该规则纳入互通技能的实现前静态检查。 | 2026-07-21 |
| 自定义目的地禁止嵌套业务导航 | iOS 设置页的功能跳转语义；HarmonyOS `SettingsPage.ets`、`AISettingsPage.ets` 与设备日志 | HarmonyOS 日志出现 `can't find inner navigation`、`can't find name in config file: ai.settings`、`load page failed`，自定义目的地最终为空；原因是设置页导航目的地内再次创建 AI 业务 `Navigation` | 父导航已有栈时，子功能复用父栈或直接切换为独立根视图；异步加载失败必须将 loading 置为完成并展示错误/重试。修复后 `assembleHap` 通过。 | 2026-07-21 |
| HarmonyOS 设置页 Demo 选型 | `agc-template-market-harmonyos-demos-main/ToolsTemplate/AIOffice/components/business_setting/`、`ShoppingTemplate/Express/components/app_setting/`、`HouseAndHomeTemplate/HomeDecoration/components/module_filter_list/`、`.../module_decoration_form/`、`.../module_feedback/` | Demo 已验证可复用的 UI 模式包括：分组设置卡片、图标/副标题/开关/选择器行、响应式页面边距、Sheet 表单、SelectDialog、Drawer/CommonPicker、loading/list/empty 三态、字段校验 | Demo 只作为 ArkUI 组件和交互参考；静态 SettingItem、Mock 数据、示例接口、日志、资源和业务状态不能直接复制到 AI 设置。已在 HarmonyOS AI UI 文档的附录 A 建立 18 个页面与 Demo 的逐页映射。 | 2026-07-21 |
| HarmonyOS 第三方本地 Vendor | 后端 STS 与客户端依赖必须可审计、不可依赖开发机环境的通用交付约束 | `HomeDecoration/products/entry/oh-package.json5` 的 `file:../../commons/...`；阿里云 Harmony SDK 官方文档 | `file:` 可稳定引用本地源码包；固化第三方 SDK 时必须提交包根 `oh-package.json5`、版本/许可证/校验和、直接与传递依赖及离线构建证据。示例工程的本地模块引用不能替代第三方 SDK 依赖审计。 | 2026-07-21 |
| 登录/刷新设备绑定 | iOS `AuthTokenProvider.swift` 与 `SparkSystemInfo.shared.installationDeviceID`；服务端 `DeviceSessionService.validate_refresh_request` | HarmonyOS `AuthAPI.ets`、`DeviceCredentialStore.ets`、`SparkAssetStore.ets`、`AuthTokenProvider.ets` | 登录和 refresh 请求必须复用同一安装级 `device_id`；固定占位 device ID 会在 access token 正常到期后导致 refresh 401。Token provider 应通过持久化设备凭证注入异步 device ID，并以 mock body 测试验证。 | 2026-07-21 |
| 首页医疗双段式聚合 | iOS `LoadHomeMedicalOverviewUseCase`、`MedicalQueryAPI`；后端 `MemberCompleteDataAPI`（`etag_max_age=86400`） | HarmonyOS `Features/Home` + `API/Medical`（首屏 listMembers/complete-data 已接；写接口仍有桩） | 首页应先拉成员列表再拉 `GET /api/v1/medical/members/{id}/complete-data/`，用单快照驱动卡片与列表首屏；成员列表在 Spark 客户端实际走 `GET /api/v1/medical/resources/?kind=members`。complete-data 失败可降级空卡片，成员列表失败不可吞成空成功态。后台 admin complete-data 是另一套摘要 payload，不能当客户端契约。 | 2026-07-21 |
| 首页医疗内存缓存 | iOS `HomeViewModel.updateMedicalCompleteData`、`HomeMedicalRouteSupport`、列表/药箱/Chat 注入；总领《首页医疗数据缓存》 | HarmonyOS：`updateMedicalCompleteData`、`reloadMembers`、RouteSupport、四列表壳+家庭药箱、QueryAPI list* 已落地（`assembleHap` 通过）；Chat 镜像待 Chat Feature | 权威源仅 `HomeViewModel.dashboard.medical.completeData`；禁止 Disk/Preferences 存健康快照；字段级回写、归档切断；已知缺口：patch 不重算 cards、`syncRemote` 未跳过网络。勿把 `MedicationExecutionRecordCache` / `moduleSetupCache` 当成首页缓存。 | 2026-07-21 |
| 首页成员模块与分区 | iOS `MemberModuleSetupUseCase`、`HomeViewModel` 分区、`Members/MemberSetup`、`SelectedMemberIDPersisting`；后端 `MemberModuleSetting` + unified `kind=member-module-settings`；总领《首页成员模块》 | HarmonyOS：`SelectedMemberIDStore`+Context+list settings+分区壳+`HomeTabPage` 切换已接；DTO 缺 `detail_data`/`extra`；无 create/update；无 SetupFlow；**空 settings 时默认展示 medical（与 iOS「默认不开通」漂移）** | 分区只看 `is_enabled`；选中 Preferences 仅存 memberID；写接口走 unified resources；维护旁路 cache 非首页权威源；先消默认 medical 漂移再做 SetupFlow。 | 2026-07-22 |
| AI Runtime 薄层 vs 聊天编排 | iOS `AIRuntimeService` + `ChatOrchestrator` + `ToolHub`；真 SSE 与取消令牌 | HarmonyOS `Core/AI/Runtime/AIRuntimeService.ets` + `OpenAICompatibleProviderAdapter`（`stream:false`）+ `LocalModelAdapter` 占位；无 Chat/ToolHub | 配置→Snapshot→Runtime→Provider 骨架可复用；聊天多轮必须单独 Orchestrator，不可塞进 Adapter。远程流式应对齐 Network Kit `requestInStream`/`dataReceive`/`destroy`；软取消 Set 不等于中断 HTTP。推理走厂商 endpoint+HUKS Key，配置走 SparkService。 | 2026-07-21 |
| HarmonyOS 通用内置 OCR 包装 | iOS `OCROrchestrator.swift` / `VisionOCREngine` 通过 `OCRTextEngine` 接口被业务编排注入 | HarmonyOS 官方“用文字识别”（更新时间 2026-05-12 17:31，用户提供资料）与 `CoreVisionKit textRecognition`、`ImageKit image`、`CoreFileKit fileIo`；本项目 `HarmonyVisionOCREngine.ets` | 内置 OCR 不应写在页面或业务 ViewModel；应包装成 `OCRTextEngine`。图库/Picker URI 优先按官方路径 `fileIo.open(uri, READ_ONLY)` 后用 fd 创建 `ImageSource`，再生成 `PixelMap` 调 `textRecognition.recognizeText`；`textRecognition.init/release` 建议由 session/生命周期层管理，release 失败不得覆盖识别结果；日志不得打印 OCR 全文。 | 2026-07-24 |
| HarmonyOS 内置 OCR 初始化超时治理 | iOS `OCROrchestrator.swift` 多引擎隔离与上层重试语义 | HarmonyOS 真机日志 `vision_init_failed:Run timed out`；本项目 `HarmonyBuiltInOCRSession.ets` / `OCROrchestrator.ets` | `textRecognition.init()` 是可能超时的系统服务准备阶段，不能等同于“图片无文字”。生产包装应支持上传页/前台预热、init 单飞、失败 reset + 一次重试、短 TTL keepAlive、连续失败 cooldown 熔断和远端/本地 OCR 兜底；`emptyOutput` 包含 `vision_init` 时 UI 文案应优先显示系统 OCR 初始化失败。 | 2026-07-24 |
| 体检报告资源契约 | iOS `HealthExamReports*`、`MedExamDetailLazyLoadViewModel`、`saveHealthExam`；后端 `HealthExamReport`/`MedExamDetail`/`HealthExamWorkflowSaveView` | HarmonyOS：`listHealthExamReportsWithAttachments` + `patchHealthExamReports` + 列表壳；DTO 缺 `medExamDetails`；Workflow 无 save/delete | 同源：`kind=health-exam-reports`、`business_type=health_exam_report`、`POST .../workflows/health-exams/save/`（OCR source=2,status=1）；活跃 list 可 patch 首页缓存，归档切断；明细懒加载与写链路未齐前不得标「已对齐」。列表异常启发式与详情 riskLevel 是两套规则。 | 2026-07-22 |
| HarmonyOS Notification Kit 系统本地通知 | iOS `UNUserNotificationCenter` 本地用药提醒：权限、日历触发、账号前缀清理、payload 点击路由 | HarmonyOS 官方 Notification Kit（用户提供 2026-06-09/2026-06-12 资料）、本地 `BusinessTemplate/DailySchedule/.../NotificationUtil.ets`、官方授权/角标/渠道示例附件 | 系统通知应与应用内 toast/banner 分层；授权用 `isNotificationEnabled` + `requestEnableNotification`，拒绝后用 `openNotificationSettingsWithResult`；健康/用药提醒走 `SERVICE_INFORMATION`；角标用 `setBadgeNumber` 且必须串行；进程终止后本地通知通道关闭，离线云推送另接 Push Kit。 | 2026-07-27 |

上述 HarmonyOS 示例根路径：

```text
/Users/hua/Documents/project/Reference/ClientSub-project/SparkAndroid/Package/Huawei/agc-template-market-harmonyos-demos-main
```

## 2. 官方 HarmonyOS 资料索引

| 能力 | 官方资料 | 该技能中的用途 | 注意 |
| --- | --- | --- | --- |
| 文档总入口 | [HarmonyOS 开发文档中心](https://developer.huawei.com/consumer/cn/doc/) | 按目标 SDK/API Level 查找当前指南和 API 参考。 | 页面会随版本演进，必须复核。 |
| HTTP | [发送网络请求（ArkTS）](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/http-request) | 设计 HTTP 会话、请求、取消、关闭和网络权限的依据。 | 实际方法签名以项目 DevEco SDK 为准。 |
| 密钥库 | [Universal Keystore Kit ArkTS API](https://developer.huawei.com/consumer/cn/doc/harmonyos-references/universal-keystore-arkts) | `SecureTokenStore` 的密钥管理/加密保护依据。 | HUKS 保护密钥，不等于可在 Preferences 存明文 Token。 |

## 3. iOS 网络语义基线

以下能力来自 `SupportClient` 网络模块；在目标客户端迁移时应按行为对齐：

| iOS 能力 | 对等目标行为 |
| --- | --- |
| `SupportNetworkRequest` / `NetworkStrategy` | 每个 API 显式声明方法、path、query、body、timeout、鉴权、ETag、串行 key、幂等性、优先级和重试。 |
| `AuthTokenProvider` | 内存 Token + 安全持久化 + JWT expiry + 并发刷新单飞。 |
| `SupportAuthSessionInvalidation` | 401/明确业务失效先刷新；仅明确刷新失效时清理会话。 |
| `RetryPolicy` | 429/5xx/可恢复网络错误重试；尊重 Retry-After；非幂等写请求默认不重试。 |
| `SerialRequestGate` | 同 `serialKey` 串行，不同 key 并行，优先级/FIFO 可观察。 |
| `SupportCallbackCache` | 相同 GET 合并 in-flight 任务，任务结束立即删除。 |
| `ETagStore` | URL/query/auth scope 隔离，304 用本地 body 合并，无 body 304 为错误。 |
| `NetworkPathMonitor` | 区分“未评估”和“确认无网”，恢复网络不重复启动流程。 |
| `NetworkLogSanitizer` | 可追踪 Request ID，禁止泄露凭证。 |

## 4. 已知模板风险清单

| 示例位置 | 风险 | 生产处理 |
| --- | --- | --- |
| `LiveStreaming/.../CallServerInterceptor.ts` | 使用 `MockAdapter.adapter` | 真实 Transport 必须移除 Mock Adapter。 |
| `LiveStreaming/.../LoggerInterceptor.ts` | 打印完整 request headers/body/response | 只能借鉴计时位置；先经脱敏器再记录。 |
| `LiveStreaming/.../PreferenceUtil.ts` | 打印保存/读取 value | 不打印 value；更不得存 Token/STS。 |
| `LiveStreaming/.../TokenRefreshInterceptor.ts` | 未体现全局 refresh 单飞 | 使用共享 Promise/任务，所有并发请求等待同一次刷新。 |

## 5. 新增条目格式

仅在满足“真实代码或官方资料验证”“可跨项目复用”“不含私密信息”时追加：

```markdown
| 主题 | iOS/后端证据 | HarmonyOS/官方证据 | 已验证结论 | 验证日期 |
| --- | --- | --- | --- | --- |
| ... | 绝对或项目相对代码路径 | 官方 URL 或示例绝对路径 | 可操作的规则与边界 | YYYY-MM-DD |
```

如果结论只适用于一个项目，写入该项目的技术方案，不写入本知识库。
