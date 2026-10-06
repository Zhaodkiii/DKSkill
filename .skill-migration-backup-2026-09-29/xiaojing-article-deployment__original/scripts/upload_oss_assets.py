#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import sys
import uuid
from pathlib import Path
from urllib.parse import quote, urlparse

try:
    import oss2
except ImportError as exc:
    raise SystemExit("Missing dependency: oss2. Install with `python3 -m pip install oss2`.") from exc


DEFAULTS = {
ALIYUN_ACCESS_KEY_ID=<your-access-key-id>
ALIYUN_ACCESS_KEY_SECRET=<your-access-key-secret>
    "ALIYUN_STS_ROLE_ARN": "acs:ram::1589159843550123:role/zhaodoss",
    "ALIYUN_OSS_BUCKET": "zhaodkdream",
    "ALIYUN_OSS_REGION": "cn-shanghai",
    "ALIYUN_OSS_ENDPOINT": "https://oss-cn-beijing.aliyuncs.com",
    "ALIYUN_STS_DURATION_SECONDS": "3600",
    "ALIYUN_OSS_PUBLIC_BASE": "https://zhaodkdream.oss-cn-beijing.aliyuncs.com",
}

IMAGE_LINK_RE = re.compile(r"(!\[[^\]]*\]\()([^)]+)(\))")


def cfg(name: str) -> str:
    return os.getenv(name, DEFAULTS[name]).strip()


def slugify(value: str, max_len: int = 96) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", value, flags=re.UNICODE)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-._")
    return cleaned[:max_len] or "article"


def sha256_short(path: Path, length: int = 12) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:length]


def is_remote_or_anchor(link: str) -> bool:
    parsed = urlparse(link)
    return bool(parsed.scheme or parsed.netloc or link.startswith("#"))


def iter_local_markdown_images(markdown: str, base_dir: Path):
    for match in IMAGE_LINK_RE.finditer(markdown):
        raw_link = match.group(2).strip()
        link_path = raw_link.split("#", 1)[0].split("?", 1)[0]
        if is_remote_or_anchor(link_path):
            continue
        asset_path = (base_dir / link_path).resolve()
        if asset_path.is_file():
            yield raw_link, asset_path


def public_url(base_url: str, key: str) -> str:
    return f"{base_url.rstrip('/')}/{quote(key, safe='/')}"


def read_existing_manifest(path: Path, article_dir: Path, markdown_path: Path, require_uploads: bool = False) -> tuple[Path, dict] | None:
    candidates = [path] if path.exists() else []
    candidates.extend(sorted(article_dir.glob("*oss-manifest.json")))
    for candidate in candidates:
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        manifest_markdown = data.get("markdown")
        if manifest_markdown and Path(manifest_markdown).expanduser().resolve() != markdown_path:
            continue
        if not manifest_markdown and candidate != path:
            continue
        if require_uploads and not data.get("uploads"):
            continue
        return candidate, data
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--prefix", default="content")
    parser.add_argument("--article-slug", default=None)
    parser.add_argument("--article-uuid", default=None)
    parser.add_argument("--key-style", choices=("uuid", "slug"), default="uuid")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    # Accepted by the orchestrator; ignored here and consumed by SQL generator.
    parser.add_argument("--title", default=None)
    parser.add_argument("--slug", default=None)
    parser.add_argument("--locale", default=None)
    parser.add_argument("--category-name", default=None)
    parser.add_argument("--category-slug", default=None)
    parser.add_argument("--category-description", default=None)
    parser.add_argument("--tags", default=None)
    parser.add_argument("--author-user-id", default=None)
    args = parser.parse_args()

    markdown_path = args.markdown.expanduser().resolve()
    if not markdown_path.is_file():
        raise SystemExit(f"Markdown file not found: {markdown_path}")

    bucket_name = cfg("ALIYUN_OSS_BUCKET")
    endpoint = cfg("ALIYUN_OSS_ENDPOINT")
    public_base = cfg("ALIYUN_OSS_PUBLIC_BASE")
    manifest_path = (args.manifest or (markdown_path.parent / f"{slugify(markdown_path.stem)}-oss-manifest.json")).resolve()
    article_slug = slugify(args.article_slug or markdown_path.parent.name)
    existing_manifest_result = read_existing_manifest(
        manifest_path,
        markdown_path.parent,
        markdown_path,
        require_uploads=False,
    )
    existing_manifest_path = existing_manifest_result[0] if existing_manifest_result else None
    existing_manifest = existing_manifest_result[1] if existing_manifest_result else None
    article_uuid = (
        args.article_uuid
        or (existing_manifest or {}).get("article_uuid")
        or (existing_manifest or {}).get("article_id")
        or uuid.uuid4().hex
    )
    prefix = args.prefix.strip("/")
    original = markdown_path.read_text(encoding="utf-8")

    replacements: dict[str, str] = {}
    uploads = []
    bucket = None
    if not args.dry_run:
ALIYUN_ACCESS_KEY_ID=<your-access-key-id>
        bucket = oss2.Bucket(auth, endpoint, bucket_name)

    local_images = list(iter_local_markdown_images(original, markdown_path.parent))
    for index, (raw_link, asset_path) in enumerate(local_images, start=1):
        if raw_link in replacements:
            continue
        digest = sha256_short(asset_path)
        ext = asset_path.suffix.lower() or mimetypes.guess_extension(mimetypes.guess_type(asset_path.name)[0] or "") or ""
        if args.key_style == "uuid":
            filename = f"{digest}-{index:02d}{ext}"
            key = f"{prefix}/{article_uuid}/{filename}"
        else:
            filename = slugify(asset_path.name, max_len=120)
            key = f"{prefix}/{article_slug}/{digest}-{filename}"
        url = public_url(public_base, key)
        content_type = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"

        if bucket is not None:
            bucket.put_object_from_file(key, str(asset_path), headers={"Content-Type": content_type})

        replacements[raw_link] = url
        uploads.append(
            {
                "source": str(asset_path),
                "markdown_link": raw_link,
                "oss_key": key,
                "oss_filename": filename,
                "url": url,
                "content_type": content_type,
                "sha256_12": digest,
                "index": index,
            }
        )

    rewritten = original
    for old, new in replacements.items():
        rewritten = rewritten.replace(f"]({old})", f"]({new})")

    if not uploads and existing_manifest:
        existing_uploads = existing_manifest.get("uploads", [])
        print(
            json.dumps(
                {
                    "status": "ok",
                    "manifest": str((existing_manifest_path or manifest_path).resolve()),
                    "uploads": len(existing_uploads),
                    "reused_existing_manifest": True,
                },
                ensure_ascii=False,
            )
        )
        return 0

    if not args.dry_run and rewritten != original:
        markdown_path.write_text(rewritten, encoding="utf-8")

    manifest = {
        "markdown": str(markdown_path),
        "bucket": bucket_name,
        "endpoint": endpoint,
        "public_base": public_base,
        "prefix": prefix,
        "article_slug": article_slug,
        "article_uuid": article_uuid,
        "key_style": args.key_style,
        "dry_run": args.dry_run,
        "uploads": uploads,
    }
    if existing_manifest and existing_manifest.get("content_article_slug"):
        manifest["content_article_slug"] = existing_manifest["content_article_slug"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "manifest": str(manifest_path), "uploads": len(uploads)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
