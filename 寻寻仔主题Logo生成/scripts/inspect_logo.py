"""只读检查 Logo PNG，并输出供人工验收的合成预览；需要 Pillow。"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def inspect(path, preview_dir):
    with Image.open(path) as source:
        file_format = source.format
        has_alpha = "A" in source.getbands() or "transparency" in source.info
        image = source.convert("RGBA")
    alpha = image.getchannel("A")
    histogram = alpha.histogram()
    bbox = alpha.getbbox()
    width, height = image.size
    touches_edge = bool(bbox and (
        bbox[0] == 0 or bbox[1] == 0 or bbox[2] == width or bbox[3] == height
    ))
    errors = []
    if file_format != "PNG":
        errors.append("不是实际 PNG 文件")
    if not has_alpha:
        errors.append("源文件没有透明通道或透明信息")
    if not histogram[0]:
        errors.append("没有全透明像素")
    if not sum(histogram[240:]):
        errors.append("没有足够实的前景像素，可能整体发虚")
    if touches_edge:
        errors.append("非透明内容触及边缘，需要检查是否裁切")
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview = image.copy()
    preview.thumbnail((1024, 1024))
    backgrounds = {
        "白底检查": Image.new("RGBA", preview.size, "#FFFFFF"),
        "深色底检查": Image.new("RGBA", preview.size, "#222222"),
        "棋盘格检查": Image.new("RGBA", preview.size, "#FFFFFF"),
    }
    draw = ImageDraw.Draw(backgrounds["棋盘格检查"])
    for y in range(0, preview.height, 24):
        for x in range(0, preview.width, 24):
            if (x // 24 + y // 24) % 2:
                draw.rectangle((x, y, x + 23, y + 23), fill="#D8D8D8")
    previews = []
    for name, background in backgrounds.items():
        destination = preview_dir / f"{path.stem}-{name}.png"
        Image.alpha_composite(background, preview).convert("RGB").save(destination)
        previews.append(str(destination.resolve()))
    return {
        "file": str(path.resolve()), "format": file_format,
        "size": [width, height], "source_has_alpha": has_alpha,
        "alpha_range": list(alpha.getextrema()), "visible_bbox": bbox,
        "transparent_pixel_fraction": round(histogram[0] / (width * height), 4),
        "structural_errors": errors, "previews": previews,
        "status": "需修正" if errors else "结构检查通过，仍需人工读图验收",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--preview-dir", type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.file, args.preview_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(bool(report["structural_errors"]))
