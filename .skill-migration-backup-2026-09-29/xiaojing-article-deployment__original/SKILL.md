---
name: 小鲸文章部署
description: 将小鲸健康科普 Markdown 文章部署到 SparkService 内容系统：上传本地图片到阿里云 OSS、回填正文图片 URL、生成并可直接执行 ContentArticle 入库 SQL，写入分类、标签、正文、file_manager 附件与 business_type=content 关联。Use when 用户要求部署/入库小鲸文章、上传文章附件到 OSS、生成 SparkService 内容 SQL、直接落库或把 Markdown 健康文章整理成可执行入库脚本时。
---

# 小鲸文章部署

## Overview

This skill turns a local Markdown article directory into SparkService-ready assets: images are uploaded to Aliyun OSS, Markdown image links are rewritten to public OSS URLs, an upload manifest is saved beside the article, and a MySQL stored-procedure SQL import file is generated for `ContentArticle`, categories, tags, and `file_manager` attachment relations. When the user provides database access or asks to "直接落库/直接插入/执行 SQL", the workflow continues through MySQL execution and post-insert verification.

By default, the generated SQL embeds the full Markdown content inline. The SQL file is therefore self-contained and does not depend on `LOAD_FILE()` or a server-readable Markdown path.

## When to Use

- Use when a Markdown article has local image attachments that must be uploaded to Aliyun OSS.
- Use when the final article must be imported into SparkService `content.models.ContentArticle`.
- Use when attachments must be inserted into `file_manager_managedfile` and related with `business_type='content'` and `business_id=ContentArticle.id`.
- Use when the user asks for a SQL file only, with execution handled later by the user.
- Use when the user asks to directly execute generated SQL into a local or reachable MySQL database.
- Do not use for non-SparkService schemas unless the SQL generator is adapted first.

## Core Process

Default outcome:

- If the user asks only to generate SQL, stop after SQL and manifest generation plus quality checks.
- If the user asks to deploy/import/insert directly and database credentials are available, finish by executing the SQL and verifying the inserted or updated rows in MySQL.

1. Locate the article directory and Markdown file.
2. Inspect the Markdown and confirm image references are local relative paths or already uploaded OSS URLs.
3. Inspect the title, parent folder, and H2 headings before running generation. Decide a production category, category slug, category description, and 3-6 clean tags up front when the path/title makes the defaults likely to be noisy.
4. Run the workflow script. Passing only the article directory is enough for a draft, but production imports should usually pass explicit metadata:

```bash
bash /Users/hua/.codex/skills/xiaojing-article-deployment/scripts/run_content_import_workflow.sh \
  "/path/to/article-directory"
```

Preferred production form:

```bash
bash /Users/hua/.codex/skills/xiaojing-article-deployment/scripts/run_content_import_workflow.sh \
  "/path/to/article-directory-or-article.md" \
  --title "文章标题" \
  --category-name "就医指南与报告解读" \
  --category-slug "medical-guide-report-interpretation" \
  --category-description "就医准备、报告解读、诊疗沟通和治疗决策内容" \
  --tags "胃癌:gastric-cancer,就医指南:medical-guide"
```

5. If optional metadata is missing, infer it automatically:

- `title`: first Markdown H1.
- `slug`: generated as a URL-safe random code, 12-16 characters by default. The generated value is saved into the manifest as `content_article_slug` and reused on later SQL regeneration.
- `category-name`: parent folder of the article directory.
- `category-slug`: dynamically generated from category name.
- `tags`: dynamically inferred from path hierarchy, category folder, article title, and Markdown H2 headings.

6. The workflow uploads local images to OSS using this default short object-key rule:

```text
content/<article-uuid>/<sha256-first-12>-<two-digit-index>.<ext>
```

Example:

```text
content/7f4d1d6e4f7b4ad0a3d77aa2c9e0d211/0e7d6b9e9ead-01.png
```

Do not use long Chinese article titles in the OSS directory segment by default. URL encoding makes them huge and hard to read.

7. The workflow rewrites Markdown image links to OSS public URLs.
8. The workflow writes two files into the article directory:

```text
<article-title-or-directory>-oss-manifest.json
import_content_article.sql
```

9. Review generated SQL before giving it to the user. By default the SQL embeds Markdown inline and must not require `@ARTICLE_MARKDOWN_PATH`.
10. Run the post-generation quality gate before final delivery.
11. If metadata is noisy, regenerate SQL with the existing manifest and explicit metadata. Do not rerun the upload workflow just to fix category, tags, or description.
12. If the user only asked for SQL, tell them to set `@AUTHOR_USER_ID` to a real `auth_user.id` before executing SQL.
13. If the user asks to directly insert data and provides database credentials, continue to "Direct MySQL Execution" and do not stop at SQL delivery.

## SQL Content Modes

Default mode is inline content:

```bash
bash /Users/hua/.codex/skills/xiaojing-article-deployment/scripts/run_content_import_workflow.sh \
  "/path/to/article-directory"
```

This writes the Markdown body directly into:

```sql
SET v_article_content = '...full markdown...';
```

Use the dedicated inline SQL helper when images have already been uploaded and only SQL needs regeneration:

```bash
bash /Users/hua/.codex/skills/xiaojing-article-deployment/scripts/generate_inline_content_sql.sh \
  "/path/to/article.md" \
  "/path/to/article-oss-manifest.json" \
  --slug "stable-production-slug"
```

The old `LOAD_FILE()` mode is only a fallback for very large articles or when the user explicitly asks for path-based SQL:

```bash
python3 /Users/hua/.codex/skills/xiaojing-article-deployment/scripts/generate_spark_content_sql.py \
  "/path/to/article.md" \
  --manifest "/path/to/article-oss-manifest.json" \
  --content-mode load-file
```

## Real-Run Lessons and Closed Loops

These are problems observed in actual deployments. Treat them as mandatory guardrails.

### Directory-Only Input

Users often pass only the article directory, not the `.md` path. The workflow must:

- Accept either an article directory or a Markdown file.
- If a directory is passed, select the primary `.md` file in that directory.
- Ignore helper docs such as `README.md` or `*流程说明.md`.
- Keep all generated files in the article directory unless the user asks for an additional copy elsewhere.

### Already-Rewritten Markdown

If the Markdown already contains OSS URLs, the upload step may find zero local images. This does not mean there are no attachments.

Closed loop:

- Before writing a new empty manifest, search the article directory for existing `*oss-manifest.json`.
- Reuse an existing manifest that has non-empty `uploads`.
- Never overwrite a good manifest with an empty one.
- SQL attachment records must be generated from the reused manifest.

### No-Image Articles and Stable Slugs

Many article-only Markdown files have no image references. They still need a manifest because the manifest stores `content_article_slug`.

Closed loop:

- An empty `uploads: []` manifest is valid when the Markdown has no image links.
- Never treat `uploads: []` as permission to refresh `content_article_slug`.
- On reruns, reuse the current article's existing manifest even when it has zero uploads.
- In directories with multiple Markdown files, only reuse a manifest whose `markdown` field points to the same Markdown file.
- If a second generation changed the article slug unexpectedly, stop and restore/regenerate from the manifest before executing SQL.

### Metadata Correction Without Reupload

If quality review shows noisy category, tags, or category description, regenerate SQL only:

```bash
python3 /Users/hua/.codex/skills/xiaojing-article-deployment/scripts/generate_spark_content_sql.py \
  "/path/to/article.md" \
  --manifest "/path/to/article-oss-manifest.json" \
  --output "/path/to/import_content_article.sql" \
  --category-name "用药指导与治疗方案" \
  --category-slug "medication-guidance-treatment-plan" \
  --category-description "用药指导、治疗选择、适用人群、禁忌风险和医患沟通内容" \
  --tags "减重用药:weight-loss-medication,司美格鲁肽:semaglutide,替尔泊肽:tirzepatide,肥胖治疗:obesity-treatment,用药禁忌:medication-contraindications"
```

Closed loop:

- Do not rerun `run_content_import_workflow.sh` solely for metadata correction unless images also need upload/rewrite.
- Always pass `--manifest` to preserve `content_article_slug`.
- Always pass `--category-description`; do not let a disease-specific default description leak into another category.
- Prefer compact tags: disease/drug/intervention/risk/scenario labels, not full H2 sentences.
- After regeneration, compare the manifest `content_article_slug` with `SELECT id INTO v_article_id ... slug = ...` in SQL.

### OSS Key Length

Chinese article titles become very long after URL encoding. A path like this is too long for routine use:

```text
content/05_%E8%83%83%E7%99%8C%E6%B2%BB%E7%96%97%E5%90%8E.../0e7d6b9e9ead-01-combined-followup-judgment.png
```

Closed loop:

- Default to UUID article directories, not article-title directories.
- Default to short uploaded filenames: `<sha256-first-12>-<two-digit-index>.<ext>`.
- Preserve original filename in manifest `source` and `markdown_link`; OSS object names do not need to preserve it.
- Reuse `article_uuid` from an existing manifest when regenerating or reusing uploads.
- Use `--key-style slug` only when a human-readable OSS path is explicitly required.

### Slug Quality

Article slugs should not be derived from Chinese titles or embedded English fragments. Example: a title containing `CT` once produced the article slug `ct`, which is too short and collision-prone.

Closed loop:

- Default article slug must be a URL-safe random code, 12-16 characters, compatible with SparkService `SLUG_RE`.
- Use Python-style `secrets.token_urlsafe(12)` entropy, then normalize to lowercase letters, digits, and hyphens.
- Save the generated article slug into manifest field `content_article_slug`.
- Reuse manifest `content_article_slug` on later SQL regeneration so the same article is updated instead of duplicated.
- Explicit `--slug` is allowed when the user provides a production slug.
- Reject accidental title-derived values such as `ct`, `mri`, `report`, `article`, `content`, `test`.
- After SQL generation, inspect the `SELECT id INTO v_article_id ... slug = ...` line and confirm the slug is stable and not a short title fragment.

### Metadata Inference Is a Draft, Not Gospel

Automatic category and tag inference is useful, but it can overfit headings or produce overly long tags.

Closed loop:

- Infer metadata from path, title, and H2 headings.
- Review generated `content_tags` values in SQL.
- If tags are too broad, too long, duplicated, or awkward, regenerate SQL with explicit `--tags`.
- For user-facing production imports, prefer 3-6 clean tags over many noisy tags.
- Category should usually be the immediate content-series folder, such as `疾病与症状科普` or `用药指导与治疗方案`, not a top-level annual project folder such as `2026医疗健康热点深耕专题`.
- Review `content_categories.description`; it must match the category, not a previous topic's default wording.

### OSS Verification

Python `urllib` HEAD checks can fail on local certificate-chain configuration even when OSS URLs are valid.

Closed loop:

- First try Python verification if convenient.
- If Python fails with certificate errors, retry with `curl -I -L -sS`.
- Treat successful `HTTP 200` plus expected `Content-Type` as the verification evidence.
- Do not assume upload failed solely because local Python SSL verification failed.

### SQL Delivery Location

Users expect the generated SQL and manifest beside the article, not only in a temporary thread output folder.

Closed loop:

- Always write `import_content_article.sql` into the article directory.
- Always write or reuse the manifest in the article directory.
- If the task requires thread deliverables, copy the final Markdown, manifest, and SQL to `outputs/` additionally, but do not move them out of the article directory.

## Built-In OSS Configuration

The scripts include these defaults and allow environment variables to override them:

```text
ALIYUN_ACCESS_KEY_ID=<your-access-key-id>
ALIYUN_ACCESS_KEY_SECRET=<your-access-key-secret>
ALIYUN_STS_ROLE_ARN=acs:ram::1589159843550123:role/zhaodoss
ALIYUN_OSS_BUCKET=zhaodkdream
ALIYUN_OSS_REGION=cn-shanghai
ALIYUN_OSS_ENDPOINT=https://oss-cn-beijing.aliyuncs.com
ALIYUN_STS_DURATION_SECONDS=3600
ALIYUN_OSS_PUBLIC_BASE=https://zhaodkdream.oss-cn-beijing.aliyuncs.com
```

Prefer environment variables for production use, but preserve these defaults because this workflow is intentionally fixed for the user's OSS bucket.

## SQL Mapping

Generate SQL for these SparkService tables:

- `content_categories`
- `content_tags`
- `content_articles`
- `content_article_tags`
- `file_manager_managedfile`
- `file_manager_managedfilebusinessrelation`

Use these defaults unless the user provides different metadata:

- `locale`: `zh-CN`
- `content_format`: `markdown`
- `status`: `0` draft
- `visibility`: `1` public
- `source_url`: empty string
- `business_type`: `content`
- `business_id`: saved `ContentArticle.id`

Use category descriptions that match the content category:

- `疾病与症状科普`: `常见疾病、症状识别、风险评估和生活方式干预科普内容`
- `用药指导与治疗方案`: `用药指导、治疗选择、适用人群、禁忌风险和医患沟通内容`
- `筛查与报告解读`: `筛查建议、检查准备、报告解读和后续就医沟通内容`
- If no known category applies, write a concise neutral description instead of reusing a disease-specific default.

For `references_json`, parse the Markdown section headed `参考来源` or `参考文献` when present. If parsing is imperfect, generate structured reference objects with at least `title`, `url`, `source`, and `published_at` keys and leave unknown values as `null`.

## Important SQL Content Rule

The generated SQL must be self-contained by default. It should not contain these lines unless `--content-mode load-file` was explicitly requested:

```sql
SET @ARTICLE_MARKDOWN_PATH := '/absolute/path/to/article.md';
SET v_article_content = CONVERT(LOAD_FILE(@ARTICLE_MARKDOWN_PATH) USING utf8mb4);
```

Why: `LOAD_FILE()` reads from the MySQL server filesystem, not the SQL client's filesystem. Remote MySQL and `secure_file_priv` often make path-based SQL fail. Inline SQL avoids that deployment dependency.

If `LOAD_FILE()` mode is used intentionally, tell the user they must copy the Markdown file to a MySQL server-readable directory and update `@ARTICLE_MARKDOWN_PATH`.

## Direct MySQL Execution

When the user explicitly asks to insert the generated data directly, use the execution helper after SQL generation and review. The helper can auto-detect the target SparkService database by looking for these seven required tables: `auth_user`, `content_articles`, `content_categories`, `content_tags`, `content_article_tags`, `file_manager_managedfile`, and `file_manager_managedfilebusinessrelation`.

For this local environment, the helper already contains the default MySQL connection:

- Host: `localhost`
- Port: `3306`
- User: `root`
- Password: built into the helper for this user's local machine
- MySQL client: `/usr/local/mysql/bin/mysql`
- Database: auto-detected from SparkService tables, usually `sparkservice`

Therefore, the usual direct execution command is just:

```bash
bash /Users/hua/.codex/skills/xiaojing-article-deployment/scripts/execute_content_article_sql.sh \
  "/path/to/import_content_article.sql"
```

Environment variables and command-line options can still override these defaults.

```bash
MYSQL_PWD='password' \
bash /Users/hua/.codex/skills/xiaojing-article-deployment/scripts/execute_content_article_sql.sh \
  --host localhost \
  --port 3306 \
  --user root \
  "/path/to/import_content_article.sql"
```

Pass `--database sparkservice` when multiple candidate schemas exist or when the user names the database explicitly.

Multiple SQL files can be executed in one call:

```bash
MYSQL_PWD='password' \
bash /Users/hua/.codex/skills/xiaojing-article-deployment/scripts/execute_content_article_sql.sh \
  --database sparkservice \
  "/path/to/first-import_content_article.sql" \
  "/path/to/second-import_content_article.sql"
```

Use `--author-user-id <id>` when the SQL default author should be replaced at execution time. The helper writes a temporary SQL copy and leaves the generated SQL file unchanged.

Closed loop:

- In this local environment, run the helper directly; do not ask for the password again unless the connection fails.
- For other environments, prefer `MYSQL_PWD` over `--password` so credentials do not appear in shell history.
- If the database name is missing, run the helper in auto-detect mode instead of asking immediately. It should select the only schema containing all seven required SparkService tables.
- If auto-detection finds zero or multiple matching schemas, ask for or pass `--database` explicitly.
- Confirm the target database contains SparkService tables before execution when the database name is provided.
- Confirm the chosen `auth_user.id` exists before execution, especially when overriding `@AUTHOR_USER_ID`.
- Execute only after checking the SQL is inline by default and has no accidental `LOAD_FILE()` dependency.
- After execution, verify inserted/updated `content_articles` rows by `locale + slug`, including id, title, status, visibility, author_id, category_id, and content length.
- Verify tag relations with `content_article_tags` and `content_tags`.

Example verification:

```bash
MYSQL_PWD='password' mysql -h localhost -P 3306 -u root sparkservice --default-character-set=utf8mb4 -N -e \
  "SELECT id, title, slug, status, visibility, author_id, category_id, CHAR_LENGTH(content)
   FROM content_articles
   WHERE slug IN ('article-slug-1','article-slug-2')
   ORDER BY id;"
```

Known local default from prior successful runs:

- Host: `localhost`
- Port: `3306`
- User: `root`
- Password: available in `execute_content_article_sql.sh` for this local machine.
- Database: auto-detected as `sparkservice` when it is the only schema with all required tables.
- Default author: `auth_user.id=1` (`Zhaodk`) when present.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The SQL should use LOAD_FILE because it is cleaner." | Path-based SQL fails when MySQL cannot read the local file. Inline Markdown is the default because the user wants a self-contained SQL file. |
| "The OSS filename can be the original filename." | Original names collide across articles. Use article slug plus content hash. |
| "Only Markdown links matter; file_manager records are optional." | SparkService attachment UI and business lookup depend on `file_manager` records and business relations. |
| "The user can fix metadata later." | Generate category, tags, summary, references, cover image, and attachment relations now so the import is coherent. |
| "The title-derived slug is probably fine." | Article slug should default to a persisted URL-safe random code; title-derived slugs can be too long, unstable, or collide. |
| "Zero uploads means there are no attachments." | It may mean the Markdown was already rewritten. Reuse the existing non-empty manifest before generating SQL. |

## Red Flags

- SQL uses `@ARTICLE_MARKDOWN_PATH` or `LOAD_FILE()` even though the user asked for a self-contained SQL file.
- SQL does not contain an inline `SET v_article_content = ...` assignment in default mode.
- OSS object keys omit the content hash or article UUID/slug directory.
- OSS object keys contain long URL-encoded Chinese article titles in default mode.
- OSS filenames preserve full original names when short names would be enough.
- The manifest is saved only in a temporary workspace instead of the article directory.
- A new manifest has `uploads: []` while the article clearly has OSS images or older manifest files.
- The article slug is title-derived by default instead of a persisted URL-safe random code.
- The article slug is too short or generic, especially values like `ct`, `mri`, `report`, or `article`.
- Auto-generated tags are long H2 phrases rather than clean classification tags.
- Category is the annual project folder instead of the article's immediate content category.
- Category description mentions an unrelated disease/topic, such as a gastric-cancer description on a medication article.
- A metadata-only regeneration unexpectedly changes `content_article_slug`.
- `business_type` is not `content`.
- `business_id` is blank instead of the saved `ContentArticle.id`.
- `@AUTHOR_USER_ID` is not called out in the final response.
- The Markdown still contains local image paths after upload.

## Verification

After completing the workflow, confirm:

- [ ] Markdown image links point to `https://zhaodkdream.oss-cn-beijing.aliyuncs.com/...`.
- [ ] Each uploaded OSS URL responds with `HTTP 200` and the expected content type.
- [ ] Manifest JSON exists in the article directory and lists all uploaded images.
- [ ] New OSS object keys use `content/<article_uuid>/<hash>-NN.<ext>` unless slug mode was explicitly requested.
- [ ] SQL file exists in the article directory.
- [ ] SQL embeds Markdown inline by default and does not contain `@ARTICLE_MARKDOWN_PATH` or `LOAD_FILE(`.
- [ ] Article slug in SQL is a persisted URL-safe random code, or an explicit user-provided slug.
- [ ] Manifest contains `content_article_slug` when the slug was auto-generated.
- [ ] Manifest `markdown` matches the current article, especially in directories with multiple Markdown files.
- [ ] Manifest `content_article_slug` matches the slug used by SQL.
- [ ] SQL inserts or updates category and tags.
- [ ] Category is the immediate content category, not a broad annual project folder.
- [ ] Category description matches the category/topic and contains no stale default wording.
- [ ] Generated tags are reviewed; regenerate SQL with explicit tags if they are noisy.
- [ ] SQL inserts or updates the article by `locale + slug`.
- [ ] SQL inserts `file_manager_managedfile` records.
- [ ] SQL inserts `file_manager_managedfilebusinessrelation` with `business_type='content'` and `business_id=ContentArticle.id`.
- [ ] If direct execution was requested, `execute_content_article_sql.sh` completed successfully and the imported article ids/slugs were verified in the target database.
- [ ] Final response links the generated files and either reminds the user to set `@AUTHOR_USER_ID` or states which author id was used for direct execution.
