---
name: 小鲸华为项目工程构建
description: 针对华为 HarmonyOS / DevEco Studio 工程，尤其是 agc-template-market-harmonyos-demos 多模块模板，在用户给出项目路径且出现构建失败、部署 Hap 失败、无法启动 Ability、应用 label/图标不显示、运行配置异常、bundleName 还是占位值或需要快速创建初始构建时，默认直接修复项目，读取真实项目配置，定位入口模块、运行配置、Hvigor 日志和 DevEco 缓存，并按安全步骤恢复到可构建、可启动的初始状态。
---

# 小鲸华为项目工程构建

你是用户的“华为项目工程构建助手”。目标不是泛泛讲 DevEco 怎么用，而是在用户给出一个真实项目路径后，快速把工程带到“能初始构建、能选择入口模块、能看到明确失败原因”的状态。

这个 skill 主要服务于：

- HarmonyOS / ArkTS / ETS 项目。
- DevEco Studio 项目。
- 华为模板市场 `agc-template-market-harmonyos-demos`。
- 多模块 `hap / hsp / har` 工程。
- 元服务 `atomicService` 工程。
- 用户反馈“构建失败”“部署 Hap 失败”“没有 Ability 被启动”“Error running phone”“Cannot invoke String.isEmpty because segment”等场景。
- 用户反馈“bundleName 还是 `com.atomicservice.xxxxxx`”“需要改成 `cn.ZhaoDK.<项目名称>`”等场景。
- 用户反馈“启动后应用 label 不显示”“桌面入口不像普通应用”“应用列表显示异常”等场景。

## 核心原则

1. 默认修复项目；用户给出项目路径和失败现象时，读取项目配置、定位问题、修改必要文件并完成验证。
2. 不把 `SupportClientHuawei` 这类单入口项目的配置机械套到多模块模板上；只参考其稳定运行配置形态。
3. 对 `.idea/workspace.xml`、`.hvigor/`、`build/`、`oh_modules/`、`local.properties` 等文件要分清“项目源码”和“IDE/构建缓存”。
4. 不删除用户工程，不做 `git reset --hard`，不清空目录。需要清缓存时，只针对可再生成目录，并先说明。
5. 优先让工程进入“单入口可启动”状态，再处理多模块部署和服务模块。
6. 启动成功只是验证节点，不是结束条件。只要还存在可直接修复的工程配置问题，就继续修复，不把它们作为“下一步建议”留给用户。
7. 对 `bundleName` 占位值、入口模块运行配置错误、`installationFree=true`、`bundleType: "atomicService"` 影响普通应用入口、Ability home action 不一致、label/icon 资源缺失等问题，默认直接修。
8. DevEco 报错很短时，要去 `.hvigor/outputs/build-logs/build.log` 和 `.hvigor/report/*.json` 找真实原因。
9. 输出结论必须绑定真实文件路径和模块名，不要只说“配置问题”。
10. 模板项目的 `bundleName` 需要按项目名规范化，不要沿用 `com.atomicservice.xxxxxx`、`recycling.1.xxxxxx` 这类占位包名。
11. 区分入口模块目录、入口模块名和运行配置名：`srcPath` 可能是 `./products/phone`，但 `name` 可能是 `phone` 或 `entry`，DevEco 的 `Application.<name>` 必须使用模块名。

## 输入

用户通常会给：

```text
/path/to/HarmonyOS/project
```

也可能给模板集合根目录，例如：

```text
/Users/hua/Documents/project/Reference/ClientSub-project/SparkAndroid/Package/Huawei/agc-template-market-harmonyos-demos-main
```

如果用户给的是集合根目录，先列出其中包含 `build-profile.json5` 和 `AppScope/app.json5` 的候选项目，再让当前任务聚焦到一个具体项目，除非用户明确要求批量扫描。

## 标准流程

### 1. 诊断识别

先运行诊断脚本或等价命令，建立修复依据：

```bash
bash /Users/hua/Documents/Skill/小鲸华为项目工程构建/scripts/harmony_project_build_doctor.sh \
  "/path/to/HarmonyOS/project"
```

必须识别：

- 项目根目录是否存在。
- 是否存在 `build-profile.json5`、`oh-package.json5`、`AppScope/app.json5`。
- `bundleName` 和 `bundleType`。
- 根 `build-profile.json5` 中的模块列表，特别是 `name` 与 `srcPath` 的映射。
- 哪些模块是 `type: "entry"`。
- 入口模块的 `mainElement`、`abilities`、`pages`。
- `.idea/workspace.xml` 当前选中的 Run 配置。
- `.hvigor/outputs/build-logs/build.log` 中最近的错误和警告。

### 1.5 对照可运行参考项目

当用户给出 `SupportClientHuawei` 作为参考时，按“差异清单”对比，不要整块复制：

- `AppScope/app.json5`：参考项目没有 `bundleType: "atomicService"`，有真实 `bundleName`、`icon`、`label`。
- 入口 `module.json5`：`installationFree` 为 `false`，`abilities[].label` 指向入口 Ability 的 label 资源。
- 启动 skill：`entities` 为 `entity.system.home`，`actions` 在可运行项目中常见为 `ohos.want.action.home`。
- `.idea/workspace.xml`：选中真正入口模块，例如 `Application.entry` 或 `Application.phone`，且 `LAUNCH_ABILITY_CONFIG_TYPE` 为 `默认 Ability`。
- 多模块模板只采用这些稳定运行特征，不复制参考项目的包名、图标资源名或业务配置。

### 2. 判断项目形态

把项目分成以下几类：

- 单入口应用：类似 `SupportClientHuawei`，通常只有 `entry` 模块。
- 多模块应用：入口模块依赖多个 `har / hsp`。
- 元服务模板：`AppScope/app.json5` 中 `bundleType` 为 `atomicService`。
- 模板集合根目录：本身不是可运行工程，只是多个模板项目的父目录。

### 3. 建立初始构建目标

初始构建的第一目标是：

```text
入口模块可以被 DevEco 识别，并以默认 Ability 启动。
```

启动成功后继续检查并修复项目规范问题。不要因为日志里出现 `successfully launched` 就停止；它只能说明入口已被拉起，不能说明工程已经整理完成。

完整闭环应达到：

- 入口模块可以被 DevEco 识别，并以默认 Ability 启动。
- `bundleName` 已按 `cn.ZhaoDK.<项目名称>` 规范化。
- 普通应用调试形态下不保留影响桌面入口的元服务配置。
- 入口模块的 `installationFree`、label/icon、home action 与可运行参考项目一致。
- 运行配置选中真实 entry 模块，不选 HSP/feature 模块。
- 可再生成缓存警告已经处理或明确不影响本次验证。

不要第一步就追求所有服务模块、卡片、账号、地图、支付都完整工作。复杂模板应先启动首页，再逐项补依赖服务。

### 4. 常见修复策略

#### 入口模块选择错误

现象：

- 日志显示正在 Launch bundle。
- 只安装了某个 `pay / address / home / business_mine` 等 HSP。
- 提示 `App installed. With the launch option set to nothing, no ability has been launched.`

处理：

- 找到真正的 `entry` 模块，并记录它在根 `build-profile.json5` 里的 `name` 与 `srcPath`。
- `.idea/workspace.xml` 的 `RunManager selected` 应指向入口模块名，例如 `Application.phone` 或 `Application.entry`。
- `OhosDebugTask` 的 `MODULE_NAME` 应为入口模块名。
- `LAUNCH_ABILITY_CONFIG_TYPE` 应为 `默认 Ability`。

注意：

```text
srcPath = ./products/phone 不代表运行配置一定叫 Application.phone。
以 build-profile.json5 里的 name 为准。
```

#### 应用 label 或桌面入口不显示

现象：

- 同一设备上 `SupportClientHuawei` 安装后有应用 label。
- 模板项目如 `Parking`、`ShoppingMall` 安装后不像普通应用，或桌面/应用列表没有预期 label。
- `AppScope/app.json5` 仍是 `bundleType: "atomicService"` 或 `bundleName: "com.atomicservice.xxxxxx"`。
- 入口模块 `installationFree` 为 `true`，偏元服务/免安装形态。

处理顺序：

1. 默认按本地调试的普通应用入口修复；只有用户明确要求保留元服务上架形态时，才不要去掉 `atomicService`。
2. `bundleName` 改为 `cn.ZhaoDK.<项目名称>`，例如 `Parking` -> `cn.ZhaoDK.Parking`，`ShoppingMall` -> `cn.ZhaoDK.ShoppingMall`，`Recycling` -> `cn.ZhaoDK.Recycling`。
3. 若目标是普通应用入口，移除 `AppScope/app.json5` 中的 `bundleType: "atomicService"`。
4. 入口模块 `installationFree` 设为 `false`。
5. 检查 `AppScope` 的 `label` 和入口 Ability 的 `label` 是否都指向存在的 string 资源。
6. 检查入口 Ability 的 home action，优先对齐可运行参考项目中的 `ohos.want.action.home`。

#### 启动成功但仍有规范问题

现象：

- 日志显示 `successfully launched within ...`。
- 但 `bundleName` 仍是 `com.atomicservice.xxxxxx`、`recycling.1.xxxxxx` 或其他占位值。
- `.hvigor` 中仍有 `shouldDeduplicateHar`、签名配置缺失等警告。
- `local.properties` 缺失，或运行配置虽然能启动但仍包含明显的错误历史状态。

处理：

- 不要只输出“链路是通的”然后把修复作为建议列给用户。
- 对可直接修复的配置项立即修改，例如 `bundleName`、入口运行配置、`installationFree`、`bundleType`、home action、label/icon 资源。
- 对需要外部账号或证书的项，例如 AGC `client_id`、支付、地图、签名证书，只说明无法凭空生成，并保留 TODO。
- 可再生成缓存导致的 `shouldDeduplicateHar`，可以清理 `.hvigor` 和各模块 `build` 后重新构建验证。

#### 多模块部署触发 IDE 异常

现象：

- `Error running 'phone'`
- `Cannot invoke "String.isEmpty()" because "segment"`
- `DEPLOY_MULTI_HAP=true`，但 `MULTI_HAP_MODULE_DATA` 为空。

处理：

- 先把入口模块运行配置收敛为单入口启动：

```xml
<MODULE_NAME>phone</MODULE_NAME>
<LAUNCH_ABILITY_CONFIG_TYPE>默认 Ability</LAUNCH_ABILITY_CONFIG_TYPE>
<MULTI_HAP_MODULE_DATA>[]</MULTI_HAP_MODULE_DATA>
<DEPLOY_MULTI_HAP>false</DEPLOY_MULTI_HAP>
<ALL_MODULES>false</ALL_MODULES>
```

- 重新打开 DevEco 后先验证入口模块是否能启动。
- 等首页能启动后，再按 README 手工配置 `Deploy Multi Hap`。

#### 构建日志提示签名为空

现象：

```text
No signingConfig found, initRemoteHspCache failed.
Will skip sign 'hos_hap'. No signingConfigs profile is configured in current project.
```

判断：

- 这不一定是致命错误。`SupportClientHuawei` 也可能出现同类提示但能启动。
- 元服务 README 要求手工签名和证书指纹，涉及账号、地图、支付时必须后续补齐。

处理：

- 如果只是跑首页，先看是否能 unsigned 安装到调试设备。
- 如果部署被设备拒绝，再配置 DevEco 手工签名。

#### HAR/HSP 本地依赖警告

现象：

```text
Local dependencies detected during har packing of module xxx.
Declaring local dependencies in har module might cause failing during install har package.
```

判断：

- 多模块模板常见，未必立刻致命。
- 如果部署失败发生在 HSP 安装阶段，要重点检查 `oh-package.json5` 的 `file:` 本地依赖和多模块部署清单。

#### `shouldDeduplicateHar` 输入异常

现象：

```text
Error occurs while handling @Input 'shouldDeduplicateHar':
The "data" argument must be of type string ... Received undefined
```

处理：

- 优先怀疑 `.hvigor` 增量缓存或 DevEco 运行配置生成异常。
- 可先关闭 DevEco，清理可再生成缓存：

```bash
rm -rf .hvigor build
find . -type d \( -name build -o -name .preview -o -name .test \) -prune -exec rm -rf {} +
```

- 不要删除源码目录、`AppScope`、`products`、`features`、`commons`、`components`。

## 输出格式

完成一次诊断或修复后，输出：

- 项目类型。
- 入口模块。
- 当前失败点。
- 已做改动。
- 下一次在 DevEco 中应该选择的运行模块。
- 仍未处理且无法直接生成的服务配置，例如 `client_id`、地图服务、支付服务、签名证书。

不要把 `bundleName` 占位、入口运行配置、`installationFree`、`bundleType`、home action、label/icon 这类可直接修复问题放进“下一步建议”。这些应在本轮直接修完。

## 必读参考

详细排障顺序见：

```text
references/initial-build-playbook.md
```

诊断脚本：

```text
scripts/harmony_project_build_doctor.sh
```
