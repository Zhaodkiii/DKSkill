---
name: 小红书链接图片下载
description: 下载用户明确提供的一篇或多篇小红书详情笔记、分享短链接中的全部正文图片。仅使用 Codex 内置浏览器 IAB 访问、提取正文图片链接并下载，按内容主题或用户指定合集归档，保存来源、原始提取记录、实际下载路径和完整性报告。适用于“继续下载”“放到合集”“下载到一个分组”；不搜索、不自行选笔记、不创作手账。
---

# 小红书链接图片下载

核心流程：**用户链接 → IAB 详情页 → 正文 DOM → 有序图片链接 → 核对总数 → 页面图片 downloadMedia → 真实本地路径 → 校验落盘 → 来源与报告。**

只处理本次用户明确提供的笔记；下载全部正文图片，保留顺序、内容、水印和实际格式。网页版本不能称为作者上传原图。LIVE 图片保存静态版本，动态片段不属于本技能交付。

## 1. 解析输入与确定归档方式

- 支持 `/explore/<id>`、`/discovery/item/<id>`、分享短链接，以及包含多个详情链接的分享文案。去掉 Markdown 对链接的转义、外围标点和空白，保留完整查询参数，尤其 `xsec_token`、`xsec_source`。同一 noteId 在本批次只处理一次。
- 短链接由 IAB 正常导航解析，记录用户原链接和最终详情链接。搜索、主页、平台合集链接无法确定单篇内容，需提供详情链接；不能下载搜索缩略图充数。
- 照片父目录：用户本次指定 > 会话已知目录。没有可确定的父目录才询问。
- 默认读取标题、正文后按“地点＋场景”创建本篇主题目录，例如 `衢山岛风车与海边日落`。去除表情与路径非法字符。主题目录已有其他笔记时创建 `<主题>-<noteId>`。
- 多篇默认分别按主题归档；“下载到一个组”“放到花鸟合集”表示放进指定分组，每篇保留自己的记录。优先复用明确匹配的已有目录；合集不存在时创建，不擅自搬动旧照片。
- 有指定合集时：`<照片父目录>/<合集>/<主题>-<noteId>/`。明确要求直接存入同一目录时直接保存，图片、原始记录和报告用 noteId 区分，`来源.md` 追加。
- “继续”沿用照片父目录；用户明确指定的合集偏好在后续相关地点笔记中沿用，换到其他地点则恢复主题归档。不要把所有后续笔记都塞进上一合集。
- 同一笔记已有记录时先检查已保存项，只补失败或缺失项；不重复创建目录、不自动覆盖图片或原始记录。

```text
<照片父目录>/
  <主题>/                         # 默认单篇
  <合集>/<主题>-<noteId>/           # 指定合集
    来源.md
    原始记录/<noteId>.json
    原始记录/<noteId>-浏览器下载.json
    <noteId>-01.webp               # 扩展名由文件魔数决定
    <noteId>-02.jpg
    <noteId>-下载报告.json
```

以下 `<保存目录>` 指本篇最终目录。

## 2. 仅通过 Codex 内置浏览器访问

**必须只使用 IAB。** 不绑定或启动 Chrome、Safari、Edge，不使用外部浏览器账号状态。已有 IAB 同篇标签则复用；没有则后台创建。按照 cua_repl 当前文档使用接口，首次调用遵守工具的初始化规则。

```javascript
let noteTab = await cua.createBrowserTab("iab", userUrl, { visible: false });
// 已有对应 IAB 标签时：
// let noteTab = await cua.getTab({ url: observedUrl }, { browser: "iab" });
```

- `userUrl` 来自用户，`observedUrl` 来自已观察到的 IAB 标签信息，不猜测访问参数。
- 打开后读自动返回的页面状态：确认详情页 noteId、标题、作者和轮播 `1/N`。初始还在加载时再做一次有目的的状态检查，不盲目反复刷新。
- 登录、验证码或访问限制阻挡时遵守浏览器工具规则；需要用户接管则指出具体阻挡。不得绕过验证码、读取凭据、关闭证书校验。
- 不读取应用内部状态、隐藏接口、账号数据；只读取当前笔记可见正文与 DOM 中图片属性。

## 3. 从正文 DOM 提取全部图片链接

读取本技能的 `scripts/xhs_extract.js`，**完整执行原文件代码**，不临时改成“只取已加载的大图片”。使用 `noteTab.playwright.evaluate` 的只读页面能力。若该接口接收函数表达式字符串，可把脚本包在 `() => { return <完整脚本表达式>; }` 中；具体以当前工具文档为准。

```javascript
// extractorSource 必须来自文件工具读取的 scripts/xhs_extract.js 原文。
let record = await noteTab.playwright.evaluate(
  "() => { return " + extractorSource + " }"
);
nodeRepl.write(JSON.stringify(record));
```

提取器做的事：

1. 确认 URL 是单篇详情页，在 `#noteContainer, .note-container` 内读取标题、作者和正文。
2. 按正文 DOM 顺序遍历 `img`，跳过轮播副本、评论、头像、作者区和表情。
3. 依次检查 `currentSrc`、`src`、`data-src`、`data-original`、`srcset`；转换为绝对 URL，只接纳正文的 xhscdn 图片。
4. 已知图片尺寸小于 300 像素的候选不采纳；**尺寸为 0 / null 可能只是懒加载，仍检查其链接**。只取 naturalWidth 大于 300 会漏掉尚未加载的正文图片。
5. 用 URL 末段图片 ID（去掉 `!` 后的转换参数）识别同图，忽略协议、CDN 签名目录和尺寸后缀变化，保留第一次出现的位置。保存原始下载 URL，不能自行裁掉签名或改出“原图”URL。
6. 输出 `schemaVersion`、`extractedAt`、`noteId`、`url`、`title`、`author`、`content`、`pageImageCount`、`images[{index,url,width,height,alt}]`。初始尺寸为空正常，下载后测实际尺寸。

**先核对数量再宣称完整：** 将 `images.length` 与页面 `1/N` 的 N 比较，不能只信提取器读到的数字。`pageImageCount` 是辅助值；缺失时用已观察到的 N 传入 `--expected`。

- 不一致：检查轮播懒加载；按页面实际控件切换轮播，重新执行完整提取器。若 DOM 只保留当前几张，用每张的轮播位置归并，按位置排序并去除重复；不要以首次见到的顺序替代页面顺序。
- 无图片或纯视频：说明类型，视频封面不计作全部正文照片。
- 按文件工具规范原样保存 `record` 为 `原始记录/<noteId>.json`。禁止手工重新拼签名、URL、正文或猜图片 ID。重试重新提取时保存带时间的快照，保留旧原始记录。

## 4. 用提取链接匹配页面图片并批量下载

链接提取和文件下载是两个阶段：**提取链接确定“哪些图片”，DOM locator 确定“下载哪个页面元素”。**

在同一正文容器中获取 img locators，读取每个元素已存在的 URL 属性，匹配 `record.images`。完全匹配优先；懒加载导致属性变化时用同一图片 ID 匹配，并核实属于同篇正文。不能退到推荐流或搜索图。

常见页面 `currentSrc / src` 已可完整匹配，使用如下批量流程；一次调用处理同篇，逐项捕获失败，某张失败不能中断剩余下载。

```javascript
let locators = await noteTab.playwright.locator("#noteContainer img").all();
let candidates = [];
for (let locator of locators) {
  let url = await locator.evaluate(el => el.currentSrc || el.src);
  if (record.images.some(item => item.url === url) &&
      !candidates.some(item => item.url === url)) {
    candidates.push({ url, locator });
  }
}
let downloads = [];
for (let item of record.images) {
  try {
    let match = candidates.find(candidate => candidate.url === item.url);
    if (!match) throw new Error("正文图片尚未匹配到页面元素");
    let path = await match.locator.downloadMedia({ timeoutMs: 120000 });
    downloads.push({ index: item.index, url: item.url, path });
  } catch (error) {
    downloads.push({ index: item.index, url: item.url, path: null,
                     error: String(error) });
  }
}
nodeRepl.write(JSON.stringify(downloads));
```

- 正文根节点只有 `.note-container` 时使用已观察到的实际 selector。
- 返回值是**实际下载路径**，可能含 `(1)`、`(2)`，不能由 URL 文件名猜测。将完整 `downloads` 保存为 `原始记录/<noteId>-浏览器下载.json`。
- 跨工具传递 JSON 时使用文件工具的结构化写入，或安全引用的 here-document；不能把 JSON.stringify 结果直接拼成 shell 命令，也不能把大记录手工重构成缩略版。
- 单篇图片较多时分批，保留原 index，持续保存结果并更新进度。不要为了“一次完成”让用户长时间看不到进展。
- `pageAssets` 仅作为浏览器下载备选：先读其当前接口文档，只导出与本篇正文图片链接匹配的资源，不导出整个页面推荐流。

## 5. 统一校验、复制到主题目录并生成来源与报告

复用现有脚本的浏览器导入模式，不另写一次性复制程序：

```bash
python3 '<技能目录>/scripts/download_xhs_images.py' \
  '<保存目录>/原始记录/<noteId>.json' '<保存目录>' \
  --browser-downloads '<保存目录>/原始记录/<noteId>-浏览器下载.json' \
  --expected <页面核对的总数> \
  --user-url '<用户完整分享链接>'
```

浏览器记录为 `{index,url,path,error?}` 数组，或含 `downloads` / `results` 数组的对象。脚本要求序号和 URL 对应原始提取记录，使用真实 `path` 读取文件；此模式不会再发起 HTTP 下载。

校验与落盘：

- 默认拒绝小于 20,000 bytes 的可疑响应；确认为有效小图片后才显式调整 `--min-bytes`。
- 依文件魔数决定 JPG / PNG / WebP 等实际扩展名，不相信 Content-Type 或下载路径扩展名；用已安装 Pillow 解码并记录格式、实际宽高。缺少解码能力时报告未验证，不能省略检查后宣称通过。
- 临时文件写入后原子创建目标；默认不覆盖。已存在且 SHA-256 相同则复用并标记 `already-verified`，不同则报冲突。
- 链接代表同一图片时提取阶段去重；不同轮播位置内容字节相同时保留对应位置并用 `sameContentAsIndex` 标记，不能为了 hash 去重造成照片数与页面不符。
- 报告包含页面预期数、提取数、方法、成功文件的 index / URL / 实际路径 / 字节数 / SHA-256 / 格式 / 尺寸、失败清单及 `complete`。
- 已有下载报告不覆盖，重试生成带时间的报告。`来源.md` 追加标题、作者、用户链接、最终链接、提取时间、保存时间、图片数、原始记录及报告路径，并保留笔记正文。时间按 Asia/Shanghai。
- 浏览器临时下载文件默认保留；不擅自清理用户 Downloads。

## 6. 失败恢复与多篇处理

- 403 / 签名失效：回到本篇 IAB 详情页重新提取，仅对失败位置重下。不要猜签名。
- 有 URL 但没有匹配元素：检查 `data-src / data-original / srcset` 和同图 ID，操作该篇轮播触发加载后重试。
- 浏览器返回路径但文件不存在：登记失败，重新下载该位置，不能找一个同名旧文件替代。
- 解码失败 / HTML / 过小响应：保留失败记录，重新获取本篇对应图片；不能更换为无关图。
- HTTP 备选：仅当用户指定或 IAB 下载能力不可用时使用下方现有下载器。页面访问仍必须 IAB。保持 TLS 校验；HTTP 失败但 IAB 可访问时恢复浏览器下载。

```bash
python3 '<技能目录>/scripts/download_xhs_images.py' \
  '<保存目录>/原始记录/<noteId>.json' '<保存目录>' \
  --expected <页面核对的总数> --user-url '<用户完整分享链接>'
```

多篇依用户顺序逐篇完成“提取 → 下载 → 校验 → 记录”。一篇受阻继续处理其余明确链接；最终逐篇说明成功数与失败，不把部分完成说成全部完成。

## 7. 完成标准与交付

只有同时满足以下条件才报告“全部完成”：页面 N 已核对；正文提取与 N 一致；N 个位置均有已解码、hash 核验的目标文件；无失败；原始记录、浏览器路径记录、来源和报告已落盘。

最终简短列出每篇/分组图片数和可点击的绝对目录链接，注明尚未完成的项。无需向用户再确认目录、主题、普通下载或记录写入；只在确实缺少必要输入或平台阻挡时说明。

## 技能维护自检

修改脚本后运行一次：

```bash
python3 '<技能目录>/scripts/download_xhs_images.py' --self-test
node '<技能目录>/scripts/test_extract.cjs'
```

这验证脚本逻辑，不能代替真实页面总数与实际下载文件的核对。
