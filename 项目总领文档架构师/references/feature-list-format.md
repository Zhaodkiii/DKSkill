# 功能目录清单格式

`create_feature_doc_dirs.sh` 每行接收一个核心功能目录名称。

## 推荐格式

```text
基础工程与运行环境
会话与认证
应用启动链路
主框架与首页 Tab
账号管理
AI 设置
文件与 OSS
OCR
第二相机
```

## 兼容格式

```text
- 基础工程与运行环境
2. 会话与认证
AI 设置 | 模型、Provider、API Key 和运行时配置
文件与 OSS | 上传、下载、STS 和缓存
# 以 # 开头的行会被忽略
```

规则：

- 一行只表示一个一级功能目录。
- 目录名不能包含 `/`、`\\`、`.` 或 `..`。
- 以 `|` 分隔时，脚本只使用左侧目录名。
- 同一批次重复名称只保留一次。
- 已存在目录不会覆盖，会输出 `EXISTS`。
- 脚本只创建目录，不创建空需求文档，也不删除任何文件。

说明：项目总领模式要创建主要功能的空需求文档时，不使用本脚本，而使用
`scripts/create_feature_doc_files.sh`。其输入格式见
`references/feature-doc-files-format.md`。

## 命令示例

```bash
bash scripts/create_feature_doc_dirs.sh \
  --project-root /path/to/MyProject \
  --features-file /path/to/core-features.txt
```

```bash
printf '%s\n' \
  '基础工程与运行环境' \
  '会话与认证' \
  '应用启动链路' \
  '主框架与首页 Tab' | \
  bash scripts/create_feature_doc_dirs.sh \
    --project-root /path/to/MyProject \
    --stdin
```

```bash
bash scripts/create_feature_doc_dirs.sh \
  --project-root /path/to/MyProject \
  --features-file /path/to/core-features.txt \
  --dry-run
```
