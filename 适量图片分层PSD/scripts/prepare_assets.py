#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def validate_logos(layers):
    logos = [item for item in layers if item.get("role") == "brand_logo"]
    if not logos:
        raise ValueError("每份成品必须有独立主题 Logo 层：role=brand_logo")
    for item in logos:
        if not item.get("name", "").startswith("品牌Logo_"):
            raise ValueError("Logo 图层名称必须以 品牌Logo_ 开头")
        if item.get("transparent", True) is not True or not item.get("box"):
            raise ValueError("Logo 必须是带目标位置 box 的透明素材")
        if item.get("visible", True) is not True or float(item.get("opacity", 100)) <= 0:
            raise ValueError("Logo 必须可见，不能用隐藏层或零透明度充数")


def validate_text(item):
    if not item["name"].startswith("文字图像_"):
        return
    text = item.get("semantic_text", "")
    if not text or any(marker in text for marker in ("?", "\ufffd", "□")):
        raise ValueError(f"文字图像层缺少可靠语义或包含乱码: {item['name']}")
    if item.get("editable", False):
        raise ValueError(f"文字图像层不得标记为可编辑文字: {item['name']}")


def trim_alpha(image, threshold=4):
    alpha = np.asarray(image.getchannel("A"))
    ys, xs = np.where(alpha > threshold)
    if not len(xs):
        raise ValueError("透明素材没有可见像素")
    return image.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))


def fit_component(image, box):
    box_width = int(box["width"])
    box_height = int(box["height"])
    scale = min(box_width / image.width, box_height / image.height)
    width = max(1, round(image.width * scale))
    height = max(1, round(image.height * scale))
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    x = round(float(box["x"]) + (box_width - width) / 2)
    y = round(float(box["y"]) + (box_height - height) / 2)
    return resized, x, y


def validate_box(box, canvas_width, canvas_height):
    x, y = float(box["x"]), float(box["y"])
    width, height = int(box["width"]), int(box["height"])
    if width <= 0 or height <= 0:
        raise ValueError("目标 box 的宽高必须大于 0")
    if x < 0 or y < 0 or x + width > canvas_width or y + height > canvas_height:
        raise ValueError(f"目标 box 超出画布: {box}")


def validate_aspect_ratio(image, box, tolerance=0.15, name="组件"):
    source_ratio = image.width / image.height
    target_ratio = float(box["width"]) / float(box["height"])
    mismatch = max(source_ratio / target_ratio, target_ratio / source_ratio) - 1
    if mismatch > tolerance:
        raise ValueError(
            f"{name}的素材与目标 box 宽高比不匹配: 素材 {source_ratio:.3f}, "
            f"目标 {target_ratio:.3f}, 偏差 {mismatch:.1%}；请重生成素材或修正 box"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job")
    parser.add_argument("--manifest")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        source = Image.new("RGBA", (20, 10), (0, 0, 0, 0))
        source.paste((10, 20, 30, 255), (5, 2, 15, 8))
        trimmed = trim_alpha(source)
        assert trimmed.size == (10, 6)
        fitted, x, y = fit_component(trimmed, {"x": 100, "y": 200, "width": 50, "height": 50})
        assert fitted.size == (50, 30) and (x, y) == (100, 210)
        validate_box({"x": 0, "y": 0, "width": 50, "height": 30}, 100, 100)
        validate_aspect_ratio(trimmed, {"width": 50, "height": 30})
        try:
            validate_aspect_ratio(trimmed, {"width": 50, "height": 50})
        except ValueError:
            pass
        else:
            raise AssertionError("宽高比失配未被拒绝")
        validate_text({"name": "文字图像_标题_山坳里的两村", "semantic_text": "山坳里的两村", "editable": False})
        logo = {"name": "品牌Logo_池水倒影", "role": "brand_logo", "box": {"x": 0, "y": 0, "width": 50, "height": 30}}
        validate_logos([logo])
        for invalid in ([], [dict(logo, visible=False)], [dict(logo, opacity=0)], [dict(logo, transparent=False)]):
            try:
                validate_logos(invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("缺失或不可见的 Logo 未被拒绝")
        print("ok")
        return

    if not args.job or not args.manifest:
        parser.error("--job 和 --manifest 为必填参数")

    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    if job.get("texts"):
        raise ValueError("不允许 texts/Type Layer；文字必须是透明图像组件")
    validate_logos(job["layers"])

    canvas = job["canvas"]
    canvas_width = int(canvas["width"])
    canvas_height = int(canvas["height"])
    assets_dir = Path(job["assets_dir"])
    assets_dir.mkdir(parents=True, exist_ok=True)
    layers = []

    for index, item in enumerate(job["layers"]):
        validate_text(item)
        source = Image.open(item["path"])
        transparent = bool(item.get("transparent", True))
        if item.get("role") == "brand_logo" and (source.format != "PNG" or "A" not in source.getbands()):
            raise ValueError(f"Logo 必须是含 Alpha 通道的 PNG: {item['name']}")

        if transparent:
            image = source.convert("RGBA")
            alpha = np.asarray(image.getchannel("A"))
            if not np.any(alpha < 255):
                raise ValueError(f"组件没有透明背景，必须重新生成: {item['name']}")
            if item.get("role") == "brand_logo" and not np.any(alpha == 0):
                raise ValueError(f"Logo 缺少全透明区域: {item['name']}")
            image = trim_alpha(image, int(item.get("alpha_threshold", 4)))
            box = item.get("box")
            if not box:
                raise ValueError(f"透明组件缺少目标 box: {item['name']}")
            source_ratio = image.width / image.height
            target_ratio = float(box["width"]) / float(box["height"])
            validate_box(box, canvas_width, canvas_height)
            if not item.get("allow_ratio_mismatch", False):
                validate_aspect_ratio(
                    image,
                    box,
                    float(item.get("ratio_tolerance", job.get("ratio_tolerance", 0.15))),
                    item["name"],
                )
            image, x, y = fit_component(image, box)
        else:
            image = source.convert("RGB").resize(
                (canvas_width, canvas_height), Image.Resampling.LANCZOS
            )
            x = y = 0

        output = assets_dir / f"{index:02d}.png"
        image.save(output)
        layer = {
            "name": item["name"],
            "path": str(output.resolve()),
            "x": x,
            "y": y,
            "width": image.width,
            "height": image.height,
        }
        if transparent:
            layer.update({
                "source_ratio": round(source_ratio, 6),
                "target_ratio": round(target_ratio, 6),
                "ratio_mismatch": round(max(source_ratio / target_ratio, target_ratio / source_ratio) - 1, 6),
            })
        if "semantic_text" in item:
            layer["semantic_text"] = item["semantic_text"]
        if "editable" in item:
            layer["editable"] = bool(item["editable"])
        if item.get("role") == "brand_logo":
            layer["role"] = "brand_logo"
        layers.append(layer)

    manifest = {
        "canvas": {
            "width": canvas_width,
            "height": canvas_height,
            "resolution": int(canvas.get("resolution", 300)),
            "colorMode": "RGB",
        },
        "layers": layers,
        "output": job["output"],
        "overwrite": bool(job.get("overwrite", False)),
        "photoshop_app": job.get("photoshop_app", "Adobe Photoshop 2026"),
    }
    if job.get("preview"):
        manifest["preview"] = job["preview"]
    Path(args.manifest).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(Path(args.manifest).resolve())


if __name__ == "__main__":
    main()
