#!/usr/bin/env python3
"""Download and validate Xiaohongshu note images from xhs_extract.js JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def image_extension(data: bytes, content_type: str = "") -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return ".tif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    if len(data) > 12 and data[4:12] in (b"ftypavif", b"ftypavis"):
        return ".avif"
    if content_type.startswith("image/"):
        subtype = content_type.split(";", 1)[0].split("/", 1)[1]
        return {"jpeg": ".jpg", "svg+xml": ".svg"}.get(subtype, f".{subtype}")
    return None


def load_urls(path: Path) -> tuple[dict, list[str]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    raw = manifest.get("images", manifest) if isinstance(manifest, dict) else manifest
    urls = []
    for item in raw:
        url = item.get("url") if isinstance(item, dict) else item
        if isinstance(url, str) and url.startswith(("https://", "http://")) and url not in urls:
            urls.append(url)
    return manifest if isinstance(manifest, dict) else {}, urls


def fetch(url: str, referer: str, timeout: int, retries: int) -> tuple[bytes, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": referer or "https://www.xiaohongshu.com/",
    }
    last_error = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.headers.get_content_type()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
            if attempt + 1 < retries:
                time.sleep(1 + attempt)
    raise RuntimeError(str(last_error))


def download(args: argparse.Namespace) -> int:
    manifest, urls = load_urls(args.manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"source": str(args.manifest), "noteUrl": manifest.get("url", ""), "files": [], "failed": []}
    content_hashes: set[str] = set()

    for index, url in enumerate(urls, args.start):
        try:
            data, content_type = fetch(url, manifest.get("url", ""), args.timeout, args.retries)
            if len(data) < args.min_bytes:
                raise ValueError(f"文件过小：{len(data)} bytes")
            extension = image_extension(data, content_type)
            if not extension:
                preview = data[:80].lower()
                raise ValueError("响应不是可识别图片" + ("（疑似 HTML）" if b"<html" in preview else ""))
            digest = hashlib.sha256(data).hexdigest()
            if digest in content_hashes:
                report["files"].append({"url": url, "status": "duplicate-content", "sha256": digest})
                continue
            content_hashes.add(digest)

            target = args.output_dir / f"{args.prefix}-{index:02d}{extension}"
            if target.exists() and not args.overwrite:
                raise FileExistsError(f"目标已存在：{target.name}；使用 --overwrite 覆盖")
            temporary = target.with_suffix(target.suffix + ".part")
            temporary.write_bytes(data)
            os.replace(temporary, target)
            report["files"].append({
                "url": url,
                "file": target.name,
                "bytes": len(data),
                "sha256": digest,
                "status": "downloaded",
            })
        except Exception as error:  # keep downloading the remaining note images
            report["failed"].append({"url": url, "error": str(error)})

    report_path = args.output_dir / f"{args.prefix}-下载报告.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["failed"] else 0


def self_test() -> int:
    samples = {
        ".jpg": b"\xff\xd8\xffx",
        ".png": b"\x89PNG\r\n\x1a\nx",
        ".webp": b"RIFF\x00\x00\x00\x00WEBPx",
        ".avif": b"\x00\x00\x00\x18ftypavifx",
    }
    assert all(image_extension(data) == expected for expected, data in samples.items())
    assert image_extension(b"<html>error</html>", "text/html") is None
    print("self-test passed")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, help="xhs_extract.js 输出的 JSON 文件")
    parser.add_argument("output_dir", nargs="?", type=Path, help="图片保存目录")
    parser.add_argument("--prefix", default="小红书", help="文件名前缀")
    parser.add_argument("--start", type=int, default=1, help="起始序号")
    parser.add_argument("--min-bytes", type=int, default=20_000, help="最小有效文件大小")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test and (not args.manifest or not args.output_dir):
        parser.error("必须提供 manifest 和 output_dir")
    return args


if __name__ == "__main__":
    options = parse_args()
    sys.exit(self_test() if options.self_test else download(options))
