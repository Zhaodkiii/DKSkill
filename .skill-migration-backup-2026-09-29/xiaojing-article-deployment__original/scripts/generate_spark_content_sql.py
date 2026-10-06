#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sys
from pathlib import Path


def q(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


def kebab_slug(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "content-article"


def transliterate_to_ascii(value: str) -> str:
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        lazy_pinyin = None

    if lazy_pinyin is None:
        return value

    parts: list[str] = []
    for char in value:
        if re.match(r"[A-Za-z0-9]", char):
            parts.append(char.lower())
        elif "\u4e00" <= char <= "\u9fff":
            parts.extend(lazy_pinyin(char, errors="ignore"))
        else:
            parts.append("-")
    return "-".join(part for part in parts if part)


def smart_slug(value: str, fallback_prefix: str = "content-article") -> str:
    raw = value.strip()
    has_cjk = any("\u4e00" <= char <= "\u9fff" for char in raw)
    lowered = kebab_slug(raw)
    if lowered != "content-article" and not has_cjk and len(lowered) >= 8:
        return lowered[:255]
    slug = kebab_slug(transliterate_to_ascii(raw))
    if slug == "content-article" or len(slug) < 8:
        import hashlib

        slug = f"{fallback_prefix}-{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:10]}"
    return slug[:255]


def random_urlsafe_article_slug(length: int = 16) -> str:
    """Generate a SparkService-valid URL-safe article slug.

    ContentArticle.slug allows lowercase letters, digits, and hyphens.
    Python's token_urlsafe may include underscores and uppercase letters, so
    normalize to the model's stricter slug format while keeping URL safety.
    """
    while True:
        token = secrets.token_urlsafe(12).lower().replace("_", "-")
        token = re.sub(r"[^a-z0-9-]", "", token).strip("-")
        token = re.sub(r"-{2,}", "-", token)
        if len(token) >= 12 and re.match(r"^[a-z0-9]", token):
            return token[:length]


def resolve_article_slug(args_slug: str | None, manifest: dict, manifest_path: Path) -> str:
    if args_slug:
        return args_slug
    existing = str(manifest.get("content_article_slug") or "").strip()
    if existing:
        return existing
    slug = random_urlsafe_article_slug()
    manifest["content_article_slug"] = slug
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return slug


def chinese_slug(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", value, flags=re.UNICODE)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-._")
    return cleaned or "article"


def title_from_markdown(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def summary_from_markdown(markdown: str, max_len: int = 480) -> str:
    lines = markdown.splitlines()
    capture = False
    chunks: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if capture:
                break
            capture = "先说结论" in stripped
            continue
        if capture and stripped and not stripped.startswith("!") and not stripped.startswith(">"):
            chunks.append(stripped)
    text = re.sub(r"\s+", "", "".join(chunks))
    if not text:
        body = [line.strip() for line in lines if line.strip() and not line.startswith("#") and not line.startswith("!") and not line.startswith(">")]
        text = re.sub(r"\s+", "", "".join(body))
    return text[:max_len]


def parse_references(markdown: str):
    lines = markdown.splitlines()
    capture = False
    refs = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            capture = any(name in stripped for name in ("参考来源", "参考文献"))
            continue
        if not capture or not stripped.startswith("- "):
            continue
        item = stripped[2:].strip()
        urls = re.findall(r"https?://\S+", item)
        url = urls[0].rstrip(")。）") if urls else None
        title = re.sub(r"\*\*", "", item)
        title = re.sub(r"链接[:：].*$", "", title).strip()
        title = re.sub(r"PubMed[:：].*$", "", title).strip()
        refs.append({"title": title, "url": url, "source": None, "published_at": None})
    return refs


def parse_tags(raw: str | None):
    if not raw:
        return [
            ("健康科普", "health-education", "健康科普相关内容"),
            ("疾病认知", "disease-awareness", "疾病识别、风险判断和健康管理内容"),
            ("就医指导", "medical-guidance", "就诊准备、问诊和治疗沟通内容"),
        ]
    rows = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        bits = [item.strip() for item in part.split(":")]
        name = bits[0]
        slug = bits[1] if len(bits) > 1 and bits[1] else kebab_slug(name)
        desc = bits[2] if len(bits) > 2 and bits[2] else f"{name}相关内容"
        rows.append((name, slug, desc))
    return rows


def split_tag_phrase(value: str) -> list[str]:
    value = re.sub(r"^\d+[_-]*", "", value.strip())
    value = re.sub(r"\.[^.]+$", "", value)
    value = re.sub(r"[：:（(].*$", "", value)
    parts = re.split(r"[、,/|]|与|和|及|或", value)
    cleaned = []
    for part in parts:
        part = re.sub(r"^(基础知识|基础认知|基础|内容|文章)$", "", part.strip())
        part = part.strip("-_ ")
        if 2 <= len(part) <= 12 and part not in cleaned:
            cleaned.append(part)
    return cleaned


def heading_tag_candidates(markdown: str) -> list[str]:
    candidates = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("## "):
            continue
        heading = stripped[3:].strip()
        if heading in {"先说结论", "参考来源", "参考文献", "自查问题"}:
            continue
        for item in split_tag_phrase(heading):
            if item not in candidates:
                candidates.append(item)
    return candidates


def infer_category_name(markdown_path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    parent = markdown_path.parent.parent.name
    if parent and parent != markdown_path.parent.name:
        return parent
    return "内容科普"


def infer_tags(markdown: str, markdown_path: Path, raw: str | None):
    if raw:
        return parse_tags(raw)
    title = title_from_markdown(markdown, markdown_path.stem)
    path_parts = [part for part in markdown_path.parts if part and part not in {"/", "Users", "hua", "Downloads"}]
    names: list[str] = []

    if "基础知识" in path_parts:
        idx = path_parts.index("基础知识")
        if idx + 1 < len(path_parts):
            names.extend(split_tag_phrase(path_parts[idx + 1]))

    for item in split_tag_phrase(markdown_path.parent.parent.name):
        names.append(item)
    for item in split_tag_phrase(title):
        names.append(item)
    for item in heading_tag_candidates(markdown):
        names.append(item)

    unique = []
    for name in names:
        if name and name not in unique:
            unique.append(name)

    if not unique:
        unique = ["健康科普"]

    return [(name, smart_slug(name, fallback_prefix="tag"), f"{name}相关内容") for name in unique[:6]]


def upload_meta(item):
    source = Path(item["source"])
    size = source.stat().st_size if source.exists() else 0
    md5 = hashlib.md5(source.read_bytes()).hexdigest() if source.exists() else ""
    return {
        "original_name": source.name,
        "file_ext": source.suffix.lstrip(".").lower(),
        "mime_type": item.get("content_type") or "application/octet-stream",
        "file_size": size,
        "file_md5": md5,
        "object_key": item["oss_key"],
        "file_path": item["url"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--title", default=None)
    parser.add_argument("--slug", default=None)
    parser.add_argument("--locale", default="zh-CN")
    parser.add_argument("--category-name", default=None)
    parser.add_argument("--category-slug", default=None)
    parser.add_argument("--category-description", default="健康科普、疾病认知、就医指导和治疗沟通内容")
    parser.add_argument("--tags", default=None)
    parser.add_argument("--author-user-id", default="1")
    parser.add_argument(
        "--content-mode",
        choices=("inline", "load-file"),
        default="inline",
        help="inline embeds Markdown directly in SQL; load-file uses MySQL LOAD_FILE(@ARTICLE_MARKDOWN_PATH).",
    )
    parser.add_argument("--inline-content", dest="content_mode", action="store_const", const="inline")
    parser.add_argument("--load-file-content", dest="content_mode", action="store_const", const="load-file")
    args = parser.parse_args()

    markdown_path = args.markdown.expanduser().resolve()
    manifest_path = args.manifest.expanduser().resolve()
    markdown = markdown_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    title = args.title or title_from_markdown(markdown, markdown_path.stem)
    slug = resolve_article_slug(args.slug, manifest, manifest_path)
    locale = args.locale
    summary = summary_from_markdown(markdown)
    uploads = [upload_meta(item) for item in manifest.get("uploads", [])]
    cover_image = uploads[0]["file_path"] if uploads else ""
    references_json = json.dumps(parse_references(markdown), ensure_ascii=False)
    category_name = infer_category_name(markdown_path, args.category_name)
    category_slug = args.category_slug or smart_slug(category_name, fallback_prefix="category")
    tag_rows = infer_tags(markdown, markdown_path, args.tags)
    output = (args.output or (markdown_path.parent / "import_content_article.sql")).resolve()

    sql = []
    sql.append("-- Import ContentArticle, category, tags, OSS attachments, and business relations.")
    sql.append("-- Target DB: MySQL / MariaDB, generated for SparkService Django models.")
    sql.append("-- Before executing:")
    sql.append("--   1. Set @AUTHOR_USER_ID to an existing auth_user.id.")
    if args.content_mode == "inline":
        sql.append("--   2. Markdown content is embedded inline; this SQL does not depend on external article files.")
    else:
        sql.append("--   2. Ensure MySQL LOAD_FILE can read @ARTICLE_MARKDOWN_PATH, or change it to a server-readable path.")
        sql.append("--      If secure_file_priv is enabled, put the .md file under that directory first.")
    sql.append("SET NAMES utf8mb4;")
    sql.append(f"SET @AUTHOR_USER_ID := {args.author_user_id};")
    if args.content_mode == "load-file":
        sql.append(f"SET @ARTICLE_MARKDOWN_PATH := {q(str(markdown_path))};")
    sql.append("")
    sql.append("DROP PROCEDURE IF EXISTS import_spark_content_article;")
    sql.append("DELIMITER $$")
    sql.append("CREATE PROCEDURE import_spark_content_article()")
    sql.append("BEGIN")
    sql.append("  DECLARE v_category_id BIGINT DEFAULT NULL;")
    sql.append("  DECLARE v_article_id BIGINT DEFAULT NULL;")
    sql.append("  DECLARE v_file_id BIGINT DEFAULT NULL;")
    sql.append("  DECLARE v_tag_id BIGINT DEFAULT NULL;")
    sql.append("  DECLARE v_article_content LONGTEXT DEFAULT NULL;")
    sql.append("  DECLARE EXIT HANDLER FOR SQLEXCEPTION")
    sql.append("  BEGIN")
    sql.append("    ROLLBACK;")
    sql.append("    RESIGNAL;")
    sql.append("  END;")
    sql.append("")
    sql.append("  IF @AUTHOR_USER_ID IS NULL OR NOT EXISTS (SELECT 1 FROM auth_user WHERE id = @AUTHOR_USER_ID) THEN")
    sql.append("    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Please set @AUTHOR_USER_ID to an existing auth_user.id before executing this SQL.';")
    sql.append("  END IF;")
    sql.append("")
    if args.content_mode == "inline":
        sql.append(f"  SET v_article_content = {q(markdown)};")
    else:
        sql.append("  SET v_article_content = CONVERT(LOAD_FILE(@ARTICLE_MARKDOWN_PATH) USING utf8mb4);")
    sql.append("  IF v_article_content IS NULL OR CHAR_LENGTH(TRIM(v_article_content)) = 0 THEN")
    if args.content_mode == "inline":
        sql.append("    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Embedded Markdown content is empty.';")
    else:
        sql.append("    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'LOAD_FILE failed. Check @ARTICLE_MARKDOWN_PATH, MySQL file permissions, and secure_file_priv.';")
    sql.append("  END IF;")
    sql.append("")
    sql.append("  START TRANSACTION;")
    sql.append("")
    sql.append("  INSERT INTO content_categories")
    sql.append("    (name, slug, parent_id, description, sort_order, is_active, created_at, updated_at)")
    sql.append(f"  VALUES ({q(category_name)}, {q(category_slug)}, 0, {q(args.category_description)}, 20, 1, NOW(), NOW())")
    sql.append("  ON DUPLICATE KEY UPDATE")
    sql.append("    name = VALUES(name), description = VALUES(description), sort_order = VALUES(sort_order), is_active = VALUES(is_active), updated_at = NOW();")
    sql.append(f"  SELECT id INTO v_category_id FROM content_categories WHERE slug = {q(category_slug)} LIMIT 1;")
    sql.append("")
    for name, tag_slug, desc in tag_rows:
        sql.append("  INSERT INTO content_tags")
        sql.append("    (name, slug, description, article_count, is_active, created_at, updated_at)")
        sql.append(f"  VALUES ({q(name)}, {q(tag_slug)}, {q(desc)}, 0, 1, NOW(), NOW())")
        sql.append("  ON DUPLICATE KEY UPDATE")
        sql.append("    name = VALUES(name), description = VALUES(description), is_active = VALUES(is_active), updated_at = NOW();")
        sql.append("")
    sql.append("  INSERT INTO content_articles")
    sql.append("    (title, slug, locale, translation_group_id, summary, cover_image, content, content_format,")
    sql.append("     author_id, last_editor_id, category_id, status, visibility, is_top, is_recommended, sort_order,")
    sql.append("     view_count, read_count, reading_time_seconds, seo_title, seo_description, source_url, references_json,")
    sql.append("     published_at, offline_at, created_at, updated_at, deleted_at)")
    sql.append("  VALUES")
    sql.append(f"    ({q(title)}, {q(slug)}, {q(locale)}, NULL, {q(summary)}, {q(cover_image)}, v_article_content, 'markdown',")
    sql.append("     @AUTHOR_USER_ID, @AUTHOR_USER_ID, v_category_id, 0, 1, 0, 0, 0,")
    sql.append(f"     0, 0, 0, {q(title)}, {q(summary)}, '', CAST({q(references_json)} AS JSON),")
    sql.append("     NULL, NULL, NOW(), NOW(), NULL)")
    sql.append("  ON DUPLICATE KEY UPDATE")
    sql.append("    title = VALUES(title), translation_group_id = COALESCE(content_articles.translation_group_id, content_articles.id),")
    sql.append("    summary = VALUES(summary), cover_image = VALUES(cover_image), content = VALUES(content),")
    sql.append("    content_format = VALUES(content_format), last_editor_id = VALUES(last_editor_id), category_id = VALUES(category_id),")
    sql.append("    status = VALUES(status), visibility = VALUES(visibility), is_top = VALUES(is_top),")
    sql.append("    is_recommended = VALUES(is_recommended), sort_order = VALUES(sort_order), seo_title = VALUES(seo_title),")
    sql.append("    seo_description = VALUES(seo_description), source_url = VALUES(source_url), references_json = VALUES(references_json),")
    sql.append("    deleted_at = NULL, updated_at = NOW();")
    sql.append(f"  SELECT id INTO v_article_id FROM content_articles WHERE locale = {q(locale)} AND slug = {q(slug)} LIMIT 1;")
    sql.append("  UPDATE content_articles SET translation_group_id = v_article_id WHERE id = v_article_id AND translation_group_id IS NULL;")
    sql.append("")
    sql.append("  DELETE FROM content_article_tags WHERE article_id = v_article_id;")
    for _, tag_slug, _ in tag_rows:
        sql.append(f"  SELECT id INTO v_tag_id FROM content_tags WHERE slug = {q(tag_slug)} LIMIT 1;")
        sql.append("  INSERT IGNORE INTO content_article_tags (article_id, tag_id, created_at) VALUES (v_article_id, v_tag_id, NOW());")
    sql.append("")
    for item in uploads:
        sql.append("  SET v_file_id = NULL;")
        sql.append(f"  SELECT id INTO v_file_id FROM file_manager_managedfile WHERE user_id = @AUTHOR_USER_ID AND object_key = {q(item['object_key'])} AND is_deleted = 0 LIMIT 1;")
        sql.append("  IF v_file_id IS NULL THEN")
        sql.append("    INSERT INTO file_manager_managedfile")
        sql.append("      (user_id, file_uuid, file_path, original_name, file_ext, mime_type, file_size, file_md5,")
        sql.append("       is_public, object_key, storage_type, is_deleted, deleted_at, created_at, updated_at)")
        sql.append(f"    VALUES (@AUTHOR_USER_ID, REPLACE(UUID(), '-', ''), {q(item['file_path'])}, {q(item['original_name'])}, {q(item['file_ext'])}, {q(item['mime_type'])}, {item['file_size']}, {q(item['file_md5'])},")
        sql.append(f"            1, {q(item['object_key'])}, 'oss', 0, NULL, NOW(), NOW());")
        sql.append("    SET v_file_id = LAST_INSERT_ID();")
        sql.append("  END IF;")
        sql.append("  INSERT IGNORE INTO file_manager_managedfilebusinessrelation")
        sql.append("    (file_id, user_id, business_type, business_id, created_at, updated_at)")
        sql.append("  VALUES (v_file_id, @AUTHOR_USER_ID, 'content', CAST(v_article_id AS CHAR), NOW(), NOW());")
        sql.append("")
    for _, tag_slug, _ in tag_rows:
        sql.append(f"  UPDATE content_tags SET article_count = (SELECT COUNT(*) FROM content_article_tags WHERE tag_id = content_tags.id) WHERE slug = {q(tag_slug)};")
    sql.append("")
    sql.append("  COMMIT;")
    sql.append("  SELECT v_article_id AS content_article_id;")
    sql.append("END$$")
    sql.append("DELIMITER ;")
    sql.append("")
    sql.append("CALL import_spark_content_article();")
    sql.append("DROP PROCEDURE IF EXISTS import_spark_content_article;")
    sql.append("")

    output.write_text("\n".join(sql), encoding="utf-8")
    print(json.dumps({"status": "ok", "sql": str(output), "article_slug": slug}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
