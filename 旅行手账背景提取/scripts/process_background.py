#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手账背景提炼 —— 后处理脚本
负责下载 image_edit 生成的背景图，统一规格并检测白边。
用法:
    python3 process_background.py <图片URL或本地路径> <输出路径> [--width 2185] [--height 3130] [--dpi 300]

流程:
    1. 下载/读取源图（URL 或本地文件）
    2. 检查四边是否有白色边框（>240 阈值），并输出白边范围
    3. 转 PNG、统一尺寸、写入 DPI 元数据
依赖: macOS 自带 sips；纯 Python 标准库（无第三方依赖）。
"""
import os
import re
import struct
import subprocess
import sys
import tempfile
import urllib.request
import zlib


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def download(url: str, dest: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def parse_png(raw: bytes):
    """解析 PNG，返回 (width, height, 未过滤的 RGB 像素 bytearray)。仅支持 8bit RGB/RGBA。"""
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", "不是有效 PNG"
    w = struct.unpack(">I", raw[16:20])[0]
    h = struct.unpack(">I", raw[20:24])[0]
    bit_depth = raw[24]
    color_type = raw[25]
    assert bit_depth == 8, f"仅支持 8bit，当前 {bit_depth}"
    assert color_type in (2, 6), f"仅支持 RGB(2)/RGBA(6)，当前 {color_type}"
    bpp = 3 if color_type == 2 else 4

    offset = 8
    idat = b""
    while offset < len(raw):
        length = struct.unpack(">I", raw[offset:offset + 4])[0]
        ctype = raw[offset + 4:offset + 8]
        cdata = raw[offset + 8:offset + 8 + length]
        if ctype == b"IDAT":
            idat += cdata
        offset += 12 + length
    data = zlib.decompress(idat)

    row_size = w * bpp + 1

    def paeth(a, b, c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        return a if pa <= pb and pa <= pc else (b if pb <= pc else c)

    pixels = bytearray()
    prev = bytearray(w * bpp)
    for y in range(h):
        rs = y * row_size
        ft = data[rs]
        row = bytearray(data[rs + 1:rs + row_size])
        if ft == 1:
            for i in range(bpp, len(row)):
                row[i] = (row[i] + row[i - bpp]) & 0xFF
        elif ft == 2:
            for i in range(len(row)):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(len(row)):
                a = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + (a + prev[i]) // 2) & 0xFF
        elif ft == 4:
            for i in range(len(row)):
                a = row[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + paeth(a, b, c)) & 0xFF
        pixels.extend(row)
        prev = row
    return w, h, pixels, bpp


def detect_white_border(path: str, threshold: int = 240, step: int = 3):
    """检测图片四边的白色边框，返回 dict(top,bottom,left,right)。"""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception:
        return None

    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        # 非 PNG，先用 sips 转成 PNG 再检测
        tmp = path + ".conv.png"
        subprocess.run(["sips", "-s", "format", "png", path, "--out", tmp],
                       capture_output=True)
        with open(tmp, "rb") as f:
            raw = f.read()
        os.remove(tmp)

    w, h, pixels, bpp = parse_png(raw)

    def px(x, y):
        i = (y * w + x) * bpp
        return pixels[i], pixels[i + 1], pixels[i + 2]

    def is_white(r, g, b):
        return r > threshold and g > threshold and b > threshold

    top = 0
    for y in range(h):
        if any(not is_white(*px(x, y)) for x in range(0, w, step)):
            top = y
            break
    bottom = h - 1
    for y in range(h - 1, -1, -1):
        if any(not is_white(*px(x, y)) for x in range(0, w, step)):
            bottom = y
            break
    left = 0
    for x in range(w):
        if any(not is_white(*px(x, y)) for y in range(0, h, step)):
            left = x
            break
    right = w - 1
    for x in range(w - 1, -1, -1):
        if any(not is_white(*px(x, y)) for y in range(0, h, step)):
            right = x
            break

    return {
        "top": top, "bottom": h - 1 - bottom,
        "left": left, "right": w - 1 - right,
        "size": (w, h),
    }


def set_png_dpi(path: str, dpi: int = 300):
    """向 PNG 写入 pHYs DPI 元数据。"""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "仅支持 PNG 写入 DPI"

    offset = 8
    chunks = []
    phys_idx = None
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        ctype = data[offset + 4:offset + 8]
        cdata = data[offset + 8:offset + 8 + length]
        chunks.append((ctype, cdata))
        if ctype == b"pHYs":
            phys_idx = len(chunks) - 1
        offset += 12 + length

    ppm = int(round(dpi / 0.0254))
    new_phys = struct.pack(">IIB", ppm, ppm, 1)
    if phys_idx is not None:
        chunks[phys_idx] = (b"pHYs", new_phys)
    else:
        chunks.insert(1, (b"pHYs", new_phys))

    out = data[:8]
    for ctype, cdata in chunks:
        crc = zlib.crc32(ctype + cdata) & 0xFFFFFFFF
        out += struct.pack(">I", len(cdata)) + ctype + cdata + struct.pack(">I", crc)
    with open(path, "wb") as f:
        f.write(out)


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("用法: process_background.py <URL或路径> <输出路径> [--width W] [--height H] [--dpi D]")
        sys.exit(2)

    src, out = args[0], args[1]
    width = height = dpi = None
    i = 2
    while i < len(args):
        if args[i] == "--width" and i + 1 < len(args):
            width = int(args[i + 1]); i += 2
        elif args[i] == "--height" and i + 1 < len(args):
            height = int(args[i + 1]); i += 2
        elif args[i] == "--dpi" and i + 1 < len(args):
            dpi = int(args[i + 1]); i += 2
        else:
            i += 1

    with tempfile.TemporaryDirectory() as tmp:
        raw_path = os.path.join(tmp, "src_raw.png")
        if is_url(src):
            print(f"[1/4] 下载图片: {src[:80]}...")
            download(src, raw_path)
        else:
            raw_path = src

        # 检测白边
        print("[2/4] 检测白边...")
        border = detect_white_border(raw_path)
        if border:
            w, h = border["size"]
            print(f"      源图尺寸: {w}x{h}")
            if any(border[k] > 3 for k in ("top", "bottom", "left", "right")):
                print(f"      ⚠ 检测到白边: 上{border['top']} 下{border['bottom']} "
                      f"左{border['left']} 右{border['right']}px —— 建议重新生成或裁切")
            else:
                print("      ✓ 无白边（四边均在 3px 内）")

        # 统一尺寸并转 PNG
        print("[3/4] 统一规格...")
        spec = ""
        if width and height:
            spec = f"-z {height} {width}"
        cmd = ["sips", "-s", "format", "png"]
        if spec:
            cmd += spec.split()
        cmd += [raw_path, "--out", out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print("sips 失败:", r.stderr)
            sys.exit(1)

        # 写入 DPI
        if dpi:
            print(f"[4/4] 写入 DPI={dpi}...")
            set_png_dpi(out, dpi)

    print(f"完成: {out}")


if __name__ == "__main__":
    main()
