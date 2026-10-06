---
name: apple-design-awards-2026
description: >-
  Apple Design Awards 2026 获奖与入围作品设计参考库。用于 iOS/iPadOS/macOS/visionOS/watchOS
  App 或游戏的设计灵感、竞品对标、HIG 方向判断、Liquid Glass/空间计算/辅助功能/Apple 技术选型。
  Use when the user mentions Apple Design Awards, ADA 2026, Apple 设计大奖, award-winning
  Apple app design, visionOS/Liquid Glass references, or wants design inspiration from
  2026 winners and finalists.
---

# Apple 设计大奖 2026 设计参考

来源：[Apple 设计大奖 - 2026 年获奖作品和入围作品](https://developer.apple.com/cn/design/awards/)

本 skill 基于 `/Users/hua/Documents/Skill/Apple设计大奖2026/` 下 33 篇作品文档。内容为整理转述，不是 Apple 原文。

## 何时启用

- 做 Apple 平台产品设计、改版、评审或 pitch 前，需要**有据可查**的标杆参考
- 需要按维度（乐趣、包容、创新、互动、社会影响、视觉）找对标作品
- 需要判断某方向是否契合 Apple 当前推崇的技术或体验（Liquid Glass、visionOS、Foundation Models、辅助功能等）
- 用户点名某获奖 App/游戏，或要求「ADA 级别」「Apple 设计大奖风格」

## 工作流

### 1. 先读场景，再选分类

根据用户任务，从六大分类中选 1–2 个主维度，必要时加副维度：

| 分类 | 核心问题 | 2026 获奖作品（App / 游戏） |
| --- | --- | --- |
| 乐趣横生 | 是否让人愿意反复打开、轻松但不空洞？ | grug / Is This Seat Taken? |
| 多元包容 | 辅助功能、认知负担、代表性是否进核心流程？ | Guitar Wiz / Pine Hearts |
| 创新思维 | 是否用新媒介、新机制或新信息架构？ | NBA: Live Games & Scores / Blue Prince |
| 出色互动 | 输入、反馈、跨设备是否让用户「相信自己在操作」？ | Moonlitt / Sago Mini Jinja's Garden |
| 社会影响 | 议题是否通过机制而非口号表达？ | Primary: News in Depth / Consume Me |
| 视觉图像 | 视觉系统是否与主题、机制互相证明？ | Tide Guide / 赛博朋克 2077：终极版 |

**跨分类作品**（文档内有多角度段落，优先读这些）：
- [Tide Guide](./21-tide-guide-charts-&-tables.md) — 视觉图像 + 出色互动
- [Sago Mini Jinja's Garden](./11-sago-mini-jinja's-garden.md) — 多元包容 + 出色互动
- [TR-49](./18-tr-49.md) — 创新思维 + 出色互动

### 2. 按需读取作品文档

不要一次性加载全部 33 篇。按编号读取对应 Markdown：

```
/Users/hua/Documents/Skill/Apple设计大奖2026/{编号}-{slug}.md
```

完整索引见 [README.md](./README.md)。

每篇文档结构固定：
- 基础信息（类型、身份、分类、平台）
- 一句话概览
- 设计细节
- Apple 技术与平台线索
- 可借鉴点（**输出时优先引用**）
- 资料来源

### 3. 输出设计参考

根据用户任务选择输出形态：

**A. 对标分析**（改版 / 新功能 / 评审）

```markdown
## 设计读
[一句话：你的产品场景 + 目标分类 + 为什么选这些对标]

## 推荐对标（2–4 个）
### [作品名]
- 为什么相关：
- 可迁移的设计决策：
- Apple 技术线索：
- 可借鉴点（来自文档）：

## 建议避免的误读
- [不要把 X 当成 Y]
```

**B. 灵感板**（概念 / 视觉 / 交互探索）

```markdown
## 方向
[分类 + 情绪/机制关键词]

## 参考矩阵
| 作品 | 机制/视觉钩子 | 可借鉴点 | 平台线索 |
| --- | --- | --- | --- |

## 落到当前项目的 3 条具体建议
1.
2.
3.
```

**C. 技术选型**（SwiftUI / visionOS / FM / Metal 等）

先 grep 或阅读相关作品文档中的「Apple 技术与平台线索」，再给出与项目约束匹配的选型建议。不要脱离平台能力空泛推荐。

### 4. 质量守则

- **引用可借鉴点，不要编造 Apple 评审理由**
- **区分获奖 vs 入围**：获奖作品更适合作为该分类首要标杆
- **平台匹配**：visionOS 参考不要硬套到纯 iPhone App；Metal 游戏参考不要套到工具类 App
- **转述而非抄袭**：借鉴机制、信息架构、反馈节奏；不要复制视觉资产或文案
- 需要开发者故事时，读各文档「资料来源」中的 Apple News 链接

## 分类速查与代表原则

### 乐趣横生
- **grug** — 概念够强时，少做功能反而放大性格；幽默与限制一致
- **Is This Seat Taken?** — 生活场景让规则自然浮现；无倒计时、可探索
- 入围延伸：Blippo+（复古媒介感）、Metaballs（创作先好玩）、Ball x Pit（简单输入+复杂成长）、PowerWash Simulator（进度可视化+反馈颗粒度）

### 多元包容
- **Guitar Wiz** — 辅助功能参与核心任务（VoiceOver 读和弦/品位）
- **Pine Hearts** — 开局即辅助选项；主题与机制一致
- **Structured** — 尊重能量与注意力，而不只是塞满日历
- 入围：Hearing Buddy（真实场景+隐私）、文明 VII（内容架构层面的代表性）

### 创新思维
- **NBA** — 空间计算重组「同时发生的信息」，不是放大屏幕
- **Blue Prince** — 地图即谜题；关卡生成与叙事重叠
- 入围：D-Day（亲密历史视角）、Detail（AI 打通创作阻塞环节）、Pickle Pro（MR 从身体动作出发）、TR-49（叙事/谜题/设定共用语法）

### 出色互动
- **Moonlitt** — 专业信息 → 当下可判断、可行动的界面
- **Sago Mini Jinja's Garden** — 不会读字也能玩；删除复杂度
- 入围：The Outsiders（复杂数据 → 单一核心判断）、Grand Mountain Adventure 2（输入像真实动作）

### 社会影响
- **Primary** — 严肃新闻在新媒介里克制；空间帮助理解而非抢叙事
- **Consume Me** — 机制让玩家体验议题的结构性压力
- 入围：Katha Room（文化=视觉+声音+场景）、Harvee（健康建议可信且亲近）、Despelote / Spilled（小行动承载大议题）

### 视觉图像
- **Tide Guide** — 高密度数据也要可读；动态视觉对应真实世界（天空/海洋）
- **赛博朋克 2077** — 视觉标杆 = 引擎 + 硬件特性 + 设备自适应
- 入围：Caradise（可近距离检查的细节）、(Not Boring) Camera（风格+能力并存）、明日方舟终末地 / SILT（视觉与机制互相证明）

## Apple 技术出现频率（2026 集合）

做技术对标时可优先按平台筛选：

| 技术/平台 | 相关作品 |
| --- | --- |
| SwiftUI | Guitar Wiz, Structured, Moonlitt |
| Liquid Glass | Moonlitt, Tide Guide |
| visionOS / 空间计算 | NBA, Primary, D-Day, Caradise, Pickle Pro, Metaballs |
| Foundation Models（设备端） | Structured, Hearing Buddy, Detail, Harvee |
| Apple Watch 健康 | Harvee, The Outsiders |
| Metal / 路径追踪 / MetalFX | 赛博朋克 2077 |
| RealityKit / SharePlay | Pickle Pro |
| 辅助功能（VoiceOver、动态字体、对比度等） | Guitar Wiz, Pine Hearts, Structured |

## 作品完整索引

| # | 作品 | 文件 |
| --- | --- | --- |
| 01 | grug | [01-grug.md](./01-grug.md) |
| 02 | Blippo+ | [02-blippo.md](./02-blippo.md) |
| 03 | Metaballs | [03-metaballs.md](./03-metaballs.md) |
| 04 | Is This Seat Taken? | [04-is-this-seat-taken.md](./04-is-this-seat-taken.md) |
| 05 | Ball x Pit | [05-ball-x-pit.md](./05-ball-x-pit.md) |
| 06 | PowerWash Simulator | [06-powerwash-simulator.md](./06-powerwash-simulator.md) |
| 07 | Guitar Wiz | [07-guitar-wiz.md](./07-guitar-wiz.md) |
| 08 | Hearing Buddy | [08-hearing-buddy.md](./08-hearing-buddy.md) |
| 09 | Structured | [09-structured.md](./09-structured.md) |
| 10 | Pine Hearts | [10-pine-hearts.md](./10-pine-hearts.md) |
| 11 | Sago Mini Jinja's Garden | [11-sago-mini-jinja's-garden.md](./11-sago-mini-jinja's-garden.md) |
| 12 | 文明 VII | [12-文明-vii.md](./12-文明-vii.md) |
| 13 | NBA: Live Games & Scores | [13-nba-live-games-&-scores.md](./13-nba-live-games-&-scores.md) |
| 14 | D-Day: The Camera Soldier | [14-d-day-the-camera-soldier.md](./14-d-day-the-camera-soldier.md) |
| 15 | Detail：AI 视频编辑器 | [15-detail-ai-视频编辑器.md](./15-detail-ai-视频编辑器.md) |
| 16 | Blue Prince | [16-blue-prince.md](./16-blue-prince.md) |
| 17 | Pickle Pro | [17-pickle-pro.md](./17-pickle-pro.md) |
| 18 | TR-49 | [18-tr-49.md](./18-tr-49.md) |
| 19 | Moonlitt | [19-moonlitt-moon-月相月历与月亮位置.md](./19-moonlitt-moon-月相月历与月亮位置.md) |
| 20 | The Outsiders | [20-the-outsiders-运动与健康数据跟踪器.md](./20-the-outsiders-运动与健康数据跟踪器.md) |
| 21 | Tide Guide | [21-tide-guide-charts-&-tables.md](./21-tide-guide-charts-&-tables.md) |
| 22 | Grand Mountain Adventure 2 | [22-grand-mountain-adventure-2.md](./22-grand-mountain-adventure-2.md) |
| 23 | Primary: News in Depth | [23-primary-news-in-depth.md](./23-primary-news-in-depth.md) |
| 24 | Katha Room | [24-katha-room.md](./24-katha-room.md) |
| 25 | Harvee | [25-harvee.md](./25-harvee.md) |
| 26 | Consume Me | [26-consume-me.md](./26-consume-me.md) |
| 27 | Despelote | [27-despelote.md](./27-despelote.md) |
| 28 | Spilled! | [28-spilled.md](./28-spilled.md) |
| 29 | Caradise | [29-caradise.md](./29-caradise.md) |
| 30 | (Not Boring) Camera | [30-not-boring-camera.md](./30-not-boring-camera.md) |
| 31 | 赛博朋克 2077：终极版 | [31-赛博朋克-2077-终极版.md](./31-赛博朋克-2077-终极版.md) |
| 32 | 明日方舟：终末地 | [32-明日方舟-终末地.md](./32-明日方舟-终末地.md) |
| 33 | SILT | [33-silt.md](./33-silt.md) |

## 与其他 skill 的配合

- 落地页/Web 视觉方向 → 配合 `taste-skill` / `design-taste-frontend`
- iOS 原生实现细节 → 配合 `mobile-app-engineer` / `frontend-page-engineer`
- 无障碍专项 → 配合 `accessibility-auditor-cn`
- 产品机会判断 → 配合 `xiaodianzi`（小点子）
