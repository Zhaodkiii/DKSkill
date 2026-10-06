#!/usr/bin/env python3
"""Create a compact source inventory for iOS-to-Android ports."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path


SKIP_DIRS = {
    ".git",
    ".gradle",
    ".idea",
    ".swiftpm",
    ".build",
    "build",
    "DerivedData",
    "Pods",
    "node_modules",
    "__pycache__",
    ".venv",
    "dist",
}

IOS_EXTS = {".swift", ".storyboard", ".xib", ".plist", ".json", ".xcassets"}
SERVER_EXTS = {".py", ".md", ".json", ".yaml", ".yml", ".toml"}
ANDROID_EXTS = {".kt", ".java", ".xml", ".kts", ".toml", ".md", ".json", ".pro"}
API_HINTS = ("url", "endpoint", "request", "response", "route", "path", "api", "http")
IOS_SCREEN_HINTS = ("view", "screen", "controller", "page", "flow")
ANDROID_SCREEN_HINTS = ("screen", "viewmodel", "route", "nav", "activity", "fragment", "composer")
ANDROID_ARCH_NAMES = (
    "settings.gradle.kts",
    "settings.gradle",
    "build.gradle.kts",
    "build.gradle",
    "libs.versions.toml",
    "AndroidManifest.xml",
    "architecture.md",
    "module-dependencies.md",
)
SERVER_ROUTE_NAMES = ("urls.py", "views.py", "serializers.py", "models.py", "permissions.py")


def iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def top_files(root: Path, exts: set[str], limit: int = 80) -> list[Path]:
    files = [p for p in iter_files(root) if p.suffix in exts or p.name.endswith(".xcassets")]
    return sorted(files, key=lambda p: (len(p.parts), str(p)))[:limit]


def grep_names(root: Path, terms: tuple[str, ...], exts: set[str], limit: int = 80) -> list[Path]:
    hits = []
    for path in iter_files(root):
        name = path.name.lower()
        if path.suffix not in exts and not path.name.endswith(".xcassets"):
            continue
        if any(term in name for term in terms):
            hits.append(path)
    return sorted(hits, key=lambda p: (len(p.parts), str(p)))[:limit]


def count_suffixes(root: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in iter_files(root):
        suffix = path.suffix or "<none>"
        counts[suffix] += 1
    return counts


def write_section(lines: list[str], title: str, items: list[str]) -> None:
    lines.append(f"## {title}")
    lines.append("")
    if not items:
        lines.append("- No obvious matches found.")
    else:
        lines.extend(f"- `{item}`" for item in items)
    lines.append("")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ios", required=True, type=Path, help="iOS project root")
    parser.add_argument("--server", required=True, type=Path, help="Server project root")
    parser.add_argument("--android", type=Path, help="Existing Android project root")
    parser.add_argument("--out", type=Path, help="Markdown report path")
    args = parser.parse_args()

    ios_root = args.ios.resolve()
    server_root = args.server.resolve()
    android_root = args.android.resolve() if args.android else None
    if not ios_root.exists():
        raise SystemExit(f"iOS root does not exist: {ios_root}")
    if not server_root.exists():
        raise SystemExit(f"Server root does not exist: {server_root}")
    if android_root and not android_root.exists():
        raise SystemExit(f"Android root does not exist: {android_root}")

    ios_counts = count_suffixes(ios_root)
    server_counts = count_suffixes(server_root)
    android_counts = count_suffixes(android_root) if android_root else None
    lines: list[str] = [
        "# iOS To Android Source Audit",
        "",
        f"- iOS root: `{ios_root}`",
        f"- Server root: `{server_root}`",
        f"- Android root: `{android_root}`" if android_root else "- Android root: `<none provided>`",
        "",
    ]

    write_section(
        lines,
        "iOS File Types",
        [f"{suffix}: {count}" for suffix, count in ios_counts.most_common(20)],
    )
    write_section(
        lines,
        "Server File Types",
        [f"{suffix}: {count}" for suffix, count in server_counts.most_common(20)],
    )
    if android_counts:
        write_section(
            lines,
            "Android File Types",
            [f"{suffix}: {count}" for suffix, count in android_counts.most_common(20)],
        )
    write_section(
        lines,
        "Likely iOS Screens And App Files",
        [rel(p, ios_root) for p in grep_names(ios_root, IOS_SCREEN_HINTS, IOS_EXTS)],
    )
    write_section(
        lines,
        "Likely iOS API Or Config Files",
        [rel(p, ios_root) for p in grep_names(ios_root, API_HINTS, IOS_EXTS)],
    )
    write_section(
        lines,
        "Likely Server Routes And Schemas",
        [rel(p, server_root) for p in iter_files(server_root) if p.name in SERVER_ROUTE_NAMES][:120],
    )
    if android_root:
        write_section(
            lines,
            "Likely Android Screens And Navigation",
            [rel(p, android_root) for p in grep_names(android_root, ANDROID_SCREEN_HINTS, ANDROID_EXTS)],
        )
        write_section(
            lines,
            "Likely Android API Or Config Files",
            [rel(p, android_root) for p in grep_names(android_root, API_HINTS, ANDROID_EXTS)],
        )
        write_section(
            lines,
            "Android Architecture And Requirement Docs",
            [rel(p, android_root) for p in iter_files(android_root) if p.name in ANDROID_ARCH_NAMES or p.name.startswith("ANDROID-") or p.name.endswith("需求文档.md")][:120],
        )
    write_section(
        lines,
        "Important iOS Files To Inspect",
        [rel(p, ios_root) for p in top_files(ios_root, IOS_EXTS)],
    )
    write_section(
        lines,
        "Important Server Files To Inspect",
        [rel(p, server_root) for p in top_files(server_root, SERVER_EXTS)],
    )
    if android_root:
        write_section(
            lines,
            "Important Android Files To Inspect",
            [rel(p, android_root) for p in top_files(android_root, ANDROID_EXTS)],
        )

    report = "\n".join(lines)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
