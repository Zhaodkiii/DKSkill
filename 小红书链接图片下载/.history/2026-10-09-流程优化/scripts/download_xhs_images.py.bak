#!/usr/bin/env python3
"""Download and validate Xiaohongshu note images from xhs_extract.js JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo
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
    from PIL import Image  # 使用已安装的 Pillow；缺失时明确报错，不跳过解码检查。

    browser_items = {}
    if args.browser_downloads:
        entries = json.loads(args.browser_downloads.read_text(encoding="utf-8"))
        entries = entries.get("downloads", entries.get("results", [])) if isinstance(entries, dict) else entries
        for entry in entries:
            index = entry.get("index")
            if index in browser_items:
                raise ValueError(f"浏览器下载记录序号重复：{index}")
            browser_items[index] = entry
    expected = args.expected or manifest.get("pageImageCount")
    prefix = args.prefix or manifest.get("noteId")
    if not prefix or Path(prefix).name != prefix or prefix in (".", ".."):
        raise ValueError("需要有效的 noteId 或不含路径的 --prefix")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"source": str(args.manifest), "noteId": manifest.get("noteId", ""),
              "title": manifest.get("title", ""), "noteUrl": manifest.get("url", ""),
              "method": "browser downloadMedia" if args.browser_downloads else "HTTP",
              "expected": expected, "extracted": len(urls), "files": [], "failed": []}
    if not urls:
        report["failed"].append({"error": "没有正文图片；请检查是否为视频笔记或提取未完成"})
    if expected and len(urls) != expected:
        report["failed"].append({"error": f"提取 {len(urls)} 张与页面 {expected} 张不一致"})
    if not expected:
        report["failed"].append({"error": "缺少页面总数，不能确认全部完成；核对轮播后传入 --expected"})
    content_hashes: dict[str, int] = {}

    for index, url in enumerate(urls, args.start):
        try:
            browser_path = None
            if args.browser_downloads:
                entry = browser_items.get(index)
                if not entry or entry.get("url") != url:
                    raise ValueError("浏览器记录缺失或 URL 与原始提取记录不匹配")
                browser_path = entry.get("path")
                if not browser_path:
                    raise ValueError(entry.get("error") or "浏览器未返回下载路径")
                source = Path(browser_path)
                if not source.is_absolute() or not source.is_file():
                    raise ValueError("浏览器返回路径不是可读取的绝对文件路径")
                data, content_type = source.read_bytes(), ""
            else:
                data, content_type = fetch(url, manifest.get("url", ""), args.timeout, args.retries)
            if len(data) < args.min_bytes:
                raise ValueError(f"文件过小：{len(data)} bytes")
            extension = image_extension(data, content_type)
            if not extension:
                preview = data[:80].lower()
                raise ValueError("响应不是可识别图片" + ("（疑似 HTML）" if b"<html" in preview else ""))
            import io
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                width, height = image.size
                actual_format = image.format
            digest = hashlib.sha256(data).hexdigest()
            target = args.output_dir / f"{prefix}-{index:02d}{extension}"
            status = "downloaded"
            if target.exists() and not args.overwrite:
                if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                    raise FileExistsError(f"目标已存在且内容不同：{target.name}；禁止自动覆盖")
                status = "already-verified"
            else:
                with tempfile.NamedTemporaryFile(dir=args.output_dir, suffix=".part", delete=False) as temp:
                    temporary = Path(temp.name)
                    temp.write(data)
                try:
                    if args.overwrite:
                        os.replace(temporary, target)
                    else:
                        os.link(temporary, target)  # 原子创建；不会覆盖并发写入的文件。
                finally:
                    temporary.unlink(missing_ok=True)
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError("落盘后的 SHA-256 与下载内容不一致")
            item = {
                "index": index, "url": url, "file": str(target.resolve()),
                "bytes": len(data),
                "sha256": digest, "format": actual_format, "width": width, "height": height,
                "status": status,
            }
            if browser_path:
                item["browserDownloadPath"] = browser_path
            if digest in content_hashes:
                item["sameContentAsIndex"] = content_hashes[digest]
            content_hashes.setdefault(digest, index)
            report["files"].append(item)
        except Exception as error:  # keep downloading the remaining note images
            report["failed"].append({"index": index, "url": url, "error": str(error)})

    report["complete"] = bool(expected and len(report["files"]) == expected and not report["failed"])
    stamp = datetime.now(ZoneInfo("Asia/Shanghai"))
    report_path = args.output_dir / f"{prefix}-下载报告.json"
    if report_path.exists():
        report_path = args.output_dir / f"{prefix}-下载报告-{stamp.strftime('%Y%m%d-%H%M%S-%f')}.json"
    with report_path.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    source_path = args.output_dir / "来源.md"
    with source_path.open("a", encoding="utf-8") as source:
        source.write(f"\n## {manifest.get('title', prefix)}\n\n"
                     f"- 笔记 ID：{manifest.get('noteId', prefix)}\n"
                     f"- 作者：{manifest.get('author', '')}\n"
                     f"- 用户链接：{args.user_url or manifest.get('url', '')}\n"
                     f"- 最终详情链接：{manifest.get('url', '')}\n"
                     f"- 读取时间：{manifest.get('extractedAt', '')}\n"
                     f"- 保存时间：{stamp.isoformat()}（Asia/Shanghai）\n"
                     f"- 页面总数：{expected}；已校验保存：{len(report['files'])}；失败项：{len(report['failed'])}\n"
                     f"- 原始记录：{args.manifest.resolve()}\n"
                     f"- 下载报告：{report_path.name}\n"
                     "- 图片为网页提供版本，保留水印；LIVE 仅保存静态图片，不含动态片段。\n\n"
                     f"### 原笔记正文\n\n{manifest.get('content', '')}\n")
    print(json.dumps({"report": str(report_path), "saved": len(report["files"]),
                      "failed": report["failed"], "complete": report["complete"]}, ensure_ascii=False, indent=2))
    return 1 if report["failed"] else 0


def self_test() -> int:
    samples = {
        ".jpg": b"\xff\xd8\xffx",
        ".png": b"\x89PNG\r\n\x1a\nx",
        ".webp": b"RIFF\x00\x00\x00\x00WEBPx",
        ".avif": b"\x00\x00\x00\x18ftypavifx",
    }
    assert all(image_extension(data) == expected for expected, data in samples.items())
    assert image_extension(b"<html>error</html>", "image/webp") is None
    from PIL import Image
    from contextlib import redirect_stdout
    import io
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        image_path = root / "browser (1).png"
        Image.new("RGB", (32, 48), "blue").save(image_path)
        manifest = root / "raw.json"
        manifest.write_text(json.dumps({"noteId": "test", "pageImageCount": 1,
                                        "images": [{"url": "https://example.com/photo"}]}))
        paths = root / "paths.json"
        paths.write_text(json.dumps([{"index": 1, "url": "https://example.com/photo", "path": str(image_path)}]))
        args = argparse.Namespace(manifest=manifest, output_dir=root / "output", browser_downloads=paths,
                                  expected=None, prefix=None, start=1, min_bytes=1, overwrite=False, user_url=None)
        with redirect_stdout(io.StringIO()):
            assert download(args) == 0
            assert download(args) == 0  # 同内容复用，不覆盖既有报告。
            image_path.write_bytes(b"<html>error</html>")
            assert download(args) == 1
        assert (args.output_dir / "test-01.png").exists()
        assert len(list(args.output_dir.glob("*下载报告*.json"))) == 3
    print("self-test passed")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, help="xhs_extract.js 输出的 JSON 文件")
    parser.add_argument("output_dir", nargs="?", type=Path, help="图片保存目录")
    parser.add_argument("--prefix", help="文件名前缀，默认使用 noteId")
    parser.add_argument("--browser-downloads", type=Path, help="浏览器实际下载路径 JSON；提供后不发起 HTTP 下载")
    parser.add_argument("--expected", type=int, help="已在页面核对的正文图片总数")
    parser.add_argument("--user-url", help="用户原始分享链接，完整保留访问参数")
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
