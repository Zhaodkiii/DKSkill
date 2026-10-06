# HarmonyOS 初始构建排障手册

## 目标

把一个华为 HarmonyOS / DevEco Studio 工程，从“打不开、构建失败、部署失败、没有启动 Ability”的状态，推进到最小可验证状态：

```text
DevEco 能识别入口模块 -> 能构建入口 HAP -> 能启动默认 Ability -> 再处理多模块和服务能力
```

## 快速判断

### 默认进入项目修复

用户给出项目路径和问题日志时，默认就是要修复项目。直接进入诊断、修改和验证闭环，不需要再确认是否允许修改。

### 不是项目根目录

项目根目录通常包含：

```text
build-profile.json5
oh-package.json5
AppScope/app.json5
hvigorfile.ts
```

如果用户给的是 `agc-template-market-harmonyos-demos-main`，它通常是模板集合根目录，不是单个可运行工程。需要进入具体模板目录，例如：

```text
LifestyleAndServiceTemplate/Parking
LifestyleAndServiceTemplate/GovernmentService/Application
```

### bundleName 规范化

模板项目里经常会看到占位包名：

```text
com.atomicservice.xxxxxx
```

当用户已经明确给出项目名时，应该直接改成：

```text
cn.ZhaoDK.<项目名称>
```

例子：

- `ShoppingMall` -> `cn.ZhaoDK.ShoppingMall`
- `Parking` -> `cn.ZhaoDK.Parking`
- `GovernmentService` -> `cn.ZhaoDK.GovernmentService`
- `Recycling` -> `cn.ZhaoDK.Recycling`

这类变更通常要同步到 `AppScope/app.json5`，并重新检查 DevEco 缓存和 AGC 配置。

注意：`cn.ZhaoDK.<项目名称>` 是当前用户工程的约定；不要把参考项目 `SupportClientHuawei` 的包名复制到模板项目。

### label / 图标显示与普通应用入口

`SupportClientHuawei` 能在启动后创建一个带 label 的普通应用入口，关键特征是：

```text
AppScope/app.json5 没有 bundleType: atomicService
AppScope/app.json5 有真实 bundleName、icon、label
entry module 的 installationFree=false
EntryAbility 有 icon、label、exported=true
EntryAbility 的 actions 包含 ohos.want.action.home
DevEco 运行配置选择 Application.entry
```

模板项目如 `Parking`、`ShoppingMall` 默认可能是元服务形态，常见差异是：

```text
bundleType: atomicService
bundleName: com.atomicservice.xxxxxx
installationFree=true
选中了 feature/hsp 模块运行，例如 pay 或 business_mine
LAUNCH_ABILITY_CONFIG_TYPE=Nothing/无
```

默认目标是本地普通应用调试，按这些差异逐项修复。若用户明确要求保留元服务形态，不要移除 `atomicService`，只修运行配置和必要 AGC 配置。

### 单入口项目

特征：

- 根 `build-profile.json5` 只有一个模块。
- 模块名常为 `entry`。
- `.idea/workspace.xml` 中 `RunManager selected="Application.entry"`。
- `DEPLOY_MULTI_HAP=false`。

这种项目可参考 `SupportClientHuawei`。

### 多模块模板

特征：

- 根 `build-profile.json5` 中有 `products/phone`、`features/*`、`commons/*`、`components/*`。
- 真正入口通常是 `products/phone`。
- 其他 `pay / home / find / mine / address / detail` 多数不是直接启动入口。

先跑入口模块，不要先跑服务模块。

关键细节：

```text
入口目录不等于入口模块名。
DevEco 的 Application.<name> 使用 build-profile.json5 里的 name。
```

例子：

- `Parking`: `name: "phone"`，`srcPath: "./products/phone"`，运行配置应是 `Application.phone`。
- `ShoppingMall`: `name: "entry"`，`srcPath: "./products/phone"`，运行配置应是 `Application.entry`。

## DevEco 运行配置检查

打开：

```text
.idea/workspace.xml
```

确认：

```xml
<component name="RunManager" selected="Application.phone">
```

这里的 `phone` 只是示例。真实值必须来自 `build-profile.json5` 的入口模块 `name`。

入口模块的 `OhosDebugTask` 应类似：

```xml
<configuration name="phone" type="OhosDebugTask" factoryName="OpenHarmony App">
  <MODULE_NAME>phone</MODULE_NAME>
  <LAUNCH_ABILITY_CONFIG_TYPE>默认 Ability</LAUNCH_ABILITY_CONFIG_TYPE>
  <LAUNCH_ABILITY_CONFIG_VALUE />
  <MULTI_HAP_MODULE_DATA>[]</MULTI_HAP_MODULE_DATA>
  <DEPLOY_MULTI_HAP>false</DEPLOY_MULTI_HAP>
  <ALL_MODULES>false</ALL_MODULES>
</configuration>
```

如果多模块部署为空却开启：

```xml
<MULTI_HAP_MODULE_DATA>[]</MULTI_HAP_MODULE_DATA>
<DEPLOY_MULTI_HAP>true</DEPLOY_MULTI_HAP>
```

容易触发 IDE 解析异常，例如：

```text
Cannot invoke "String.isEmpty()" because "segment"
```

先关掉多模块部署，验证入口 HAP。

## 入口模块检查

入口模块的 `module.json5` 应包含：

```json5
{
  "module": {
    "type": "entry",
    "mainElement": "EntryAbility",
    "abilities": [
      {
        "name": "EntryAbility",
        "srcEntry": "./ets/entryability/EntryAbility.ets",
        "skills": [
          {
            "entities": ["entity.system.home"],
            "actions": ["action.system.home"]
          }
        ]
      }
    ]
  }
}
```

有些项目使用：

```text
ohos.want.action.home
```

能正常启动的现有项目可作为参考，但不要无脑替换；先看当前 SDK 和模板生成方式。

在当前这类模板修复里，如果对照 `SupportClientHuawei` 是为了得到普通应用入口，`ohos.want.action.home` 是优先参考值。

## 构建日志位置

优先看：

```text
.hvigor/outputs/build-logs/build.log
.hvigor/report/*.json
```

常用搜索：

```bash
rg -n "\\[ERROR\\]|ERROR|error|failed|fatal|No signingConfig|Local dependencies|shouldDeduplicateHar|deploy|install|SignHap|PackageHap" \
  .hvigor/outputs/build-logs/build.log .hvigor/report
```

## 常见现象与判断

### 启动成功但仍要继续修

日志：

```text
successfully launched within 1 s 425 ms
aa start ... EntryAbility
```

判断：

- 这说明入口已经能被拉起，但不代表工程已经整理完成。
- 如果仍有占位 `bundleName`、元服务形态、错误入口配置、`installationFree=true`、label/icon 缺失或缓存异常，继续修复。

处理：

- 直接把占位包名改成 `cn.ZhaoDK.<项目名称>`。
- 直接修入口模块的普通应用入口配置。
- 直接修 DevEco 运行配置到真实 entry 模块。
- 能清理的可再生成缓存直接清理并重新验证。
- 只有 `client_id`、地图、支付、签名证书这类需要外部真实资料的配置，才作为未处理项说明。

### 只安装不启动

日志：

```text
App installed. With the launch option set to nothing, no ability has been launched.
```

通常是运行配置没有指定默认 Ability，或选中了非入口模块。

实际例子：

- 日志安装 `features/service/pay/...pay-default-unsigned.hsp`，说明选中了 `pay`，不是入口模块。
- 日志安装 `features/business_mine/...business_mine-default-unsigned.hsp`，说明选中了 `business_mine`，不是入口模块。
- 同时出现 `With the launch option set to nothing`，说明 `LAUNCH_ABILITY_CONFIG_TYPE` 是 `Nothing/无`，不会启动 Ability。

### 部署 Hap 失败

DevEco 只显示：

```text
以下操作中发生错误：部署Hap...
```

不要停在 IDE 面板。去 `.hvigor` 日志和 hdc 输出找真实错误。

### 签名提示

```text
No signingConfig found
```

它可能只是 debug 提示，不一定导致失败。若设备拒绝安装、元服务能力不可用、账号/地图/支付异常，再处理签名和 AGC 证书指纹。

### client_id 占位

```json5
{
  "name": "client_id",
  "value": "******"
}
```

不一定影响首页启动，但会影响账号、地图、支付等服务。

## 初始构建闭环

1. 确认项目根目录。
2. 找入口模块。
3. 从 `build-profile.json5` 记录入口模块 `name` 与 `srcPath`。
4. 修正 DevEco 默认运行配置到 `Application.<入口模块 name>`。
5. 入口模块先用单模块启动。
6. 即使已经启动成功，也继续修复占位 `bundleName`。
7. 处理 `bundleType`、`installationFree`、label/icon、home action。
8. 清理必要的可再生成缓存并重新同步或构建验证。
9. 关闭 DevEco 后重开，避免旧 workspace 状态继续生效。
10. 首页能启动且工程基础配置规范后，再按 README 配置 AGC、client_id、签名、服务器域名、地图和支付。

## 不要做的事

- 不要把服务模块 `pay` 当入口模块运行。
- 不要把 `business_mine` 这类 HSP 模块当入口模块运行。
- 不要在原因不明时批量改所有 `module.json5`。
- 不要删除 `products/`、`features/`、`commons/`、`components/`。
- 不要把 `No signingConfig found` 当作唯一根因。
- 不要让空的 `MULTI_HAP_MODULE_DATA` 配合 `DEPLOY_MULTI_HAP=true` 留在入口运行配置里。
