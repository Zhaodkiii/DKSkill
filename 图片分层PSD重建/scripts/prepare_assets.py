#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


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


def connected_white_to_alpha(image: Image.Image, threshold: int) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"))
    white = np.all(rgb >= threshold, axis=2).astype(np.uint8)
    _, labels = cv2.connectedComponents(white, connectivity=8)
    border_labels = np.unique(
        np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1]))
    )
    border_labels = border_labels[border_labels != 0]
    background = np.isin(labels, border_labels)
    alpha = np.where(background, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack((rgb, alpha)), "RGBA")


def prepare_transparent_layer(image: Image.Image, threshold: int) -> Image.Image:
    """Preserve real image_gen alpha; only key connected white for opaque sources."""
    rgba = image.convert("RGBA")
    source_alpha = np.asarray(rgba)[:, :, 3]
    if np.any(source_alpha < 255):
        return rgba
    return connected_white_to_alpha(rgba, threshold)


def validate_layer(item):
    if not isinstance(item.get("name"), str) or not item["name"].strip() or any(marker in item["name"] for marker in ("\ufffd", "□")):
        raise ValueError("图层名称无效或包含乱码")
    if not item["name"].startswith("文字图像_"):
        return
    text = item.get("semantic_text", "")
    if not text or any(marker in text for marker in ("?", "\ufffd", "□")):
        raise ValueError(f"文字图像层缺少可靠语义或包含乱码: {item['name']}")
    if item.get("editable", False):
        raise ValueError(f"文字图像层不得标记为可编辑文字: {item['name']}")
    expected = item.get("expected_text", text)
    if expected != text:
        raise ValueError(f"文字语义与原图清单不同: {item['name']}")
    reviewed = item.get("ocr_reviewed_text", item.get("ocr_text"))
    if reviewed is not None and "".join(reviewed.split()) != "".join(expected.split()):
        raise ValueError(f"OCR 与原图清单不同: {item['name']}")


def fit_generated_layer(image, box):
    if len(box) != 4 or any(type(v) is not int for v in box):
        raise ValueError("target_bbox 必须为四个整数 [left, top, right, bottom]")
    left, top, right, bottom = box
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise ValueError("target_bbox 越界或尺寸无效")
    # ponytail: trim nearly invisible fringe; regenerate if faint artwork loses detail.
    alpha = np.asarray(image)[:, :, 3]
    ys, xs = np.where(alpha >= 16)
    if not len(xs):
        raise ValueError("生成素材为空或完全透明")
    cropped = image.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    fitted = ImageOps.contain(cropped, (right - left, bottom - top), Image.Resampling.LANCZOS)
    result = Image.new("RGBA", image.size)
    result.alpha_composite(fitted, (left + (right - left - fitted.width) // 2, top + (bottom - top - fitted.height) // 2))
    return result


def prepare_logo(image, item, canvas_size):
    if image.format != "PNG" or "A" not in image.getbands():
        raise ValueError("Logo 必须是含 Alpha 通道的 PNG")
    alpha = np.asarray(image.getchannel("A"))
    if not np.any(alpha == 0):
        raise ValueError("Logo 缺少全透明区域")
    ys, xs = np.where(alpha > 4)
    if not len(xs):
        raise ValueError("Logo 没有可见像素")
    image = image.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    box = item["box"]
    x, y = float(box["x"]), float(box["y"])
    width, height = int(box["width"]), int(box["height"])
    if width <= 0 or height <= 0 or x < 0 or y < 0 or x + width > canvas_size[0] or y + height > canvas_size[1]:
        raise ValueError("Logo 目标 box 越界或尺寸无效")
    source_ratio, target_ratio = image.width / image.height, width / height
    mismatch = max(source_ratio / target_ratio, target_ratio / source_ratio) - 1
    if mismatch > float(item.get("ratio_tolerance", 0.15)):
        raise ValueError("Logo 与目标 box 宽高比失配，不得拉伸")
    image = ImageOps.contain(image, (width, height), Image.Resampling.LANCZOS)
    return image, round(x + (width - image.width) / 2), round(y + (height - image.height) / 2), {
        "source_ratio": source_ratio, "target_ratio": target_ratio, "ratio_mismatch": mismatch,
    }


def verify_photoshop(manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_logos(manifest["layers"])
    folder = manifest_path.parent / "verification"
    report = json.loads((folder / "photoshop-check.json").read_text(encoding="utf-8-sig"))
    if report.get("output") != manifest["output"] or report.get("textLayers") != 0 or report.get("layers") != len(manifest["layers"]) or report.get("names") != [layer["name"] for layer in reversed(manifest["layers"])]:
        raise ValueError("Photoshop 校验报告不是本次图层或存在文字层")
    if any(report.get(key) != manifest["canvas"][key] for key in ("width", "height", "resolution")):
        raise ValueError("Photoshop 校验报告画布或 DPI 不同")
    if report.get("logoLayers") != sum(item.get("role") == "brand_logo" for item in manifest["layers"]) or report.get("logosVisible") is not True:
        raise ValueError("Photoshop 校验报告缺少实际可见 Logo")
    size = (manifest["canvas"]["width"], manifest["canvas"]["height"])
    expected = Image.new("RGBA", size)
    foreground = Image.new("RGBA", size)
    for layer in manifest["layers"]:
        image = Image.open(layer["path"]).convert("RGBA")
        expected.alpha_composite(image, (layer["x"], layer["y"]))
        if layer.get("transparent", not layer["name"].startswith("背景")):
            foreground.alpha_composite(image, (layer["x"], layer["y"]))
    actual = Image.open(report["preview"]).convert("RGBA")
    actual_foreground = Image.open(report["foreground"]).convert("RGBA")
    if actual.size != size or actual_foreground.size != size:
        raise ValueError("Photoshop 导出画布尺寸不同")
    difference = np.abs(np.asarray(expected).astype(int) - np.asarray(actual).astype(int))
    alpha_difference = np.abs(np.asarray(foreground)[:, :, 3].astype(int) - np.asarray(actual_foreground)[:, :, 3].astype(int))
    if int(difference.max()) > 2 or int(alpha_difference.max()) > 1:
        raise ValueError("Photoshop 合成或 alpha 与准备素材不同")
    print(json.dumps({"max_channel_difference": int(difference.max()), "max_alpha_difference": int(alpha_difference.max())}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job")
    parser.add_argument("--manifest")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--verify-photoshop", type=Path)
    args = parser.parse_args()

    if args.self_test:
        test = Image.new("RGB", (5, 5), "white")
        test.putpixel((2, 2), (10, 20, 30))
        alpha = np.asarray(connected_white_to_alpha(test, 246))[:, :, 3]
        assert alpha[0, 0] == 0 and alpha[2, 2] == 255
        transparent = Image.new("RGBA", (5, 5), (0, 0, 0, 0))
        transparent.putpixel((2, 2), (10, 20, 30, 255))
        preserved = np.asarray(prepare_transparent_layer(transparent, 246))
        assert preserved[0, 0, 3] == 0 and preserved[2, 2, 3] == 255
        assert tuple(preserved[2, 2, :3]) == (10, 20, 30)
        validate_layer({"name": "文字图像_正文_山在那里", "semantic_text": "山在那里", "editable": False})
        fitted = fit_generated_layer(transparent, [0, 0, 2, 2])
        assert fitted.getbbox() == (0, 0, 2, 2)
        try:
            validate_layer({"name": "文字图像_地点_衢山岛", "semantic_text": "衢山岛", "ocr_text": "衡山島"})
        except ValueError:
            pass
        else:
            raise AssertionError("wrong glyphs were accepted")
        try:
            fit_generated_layer(transparent, [0, 0, 6, 6])
        except ValueError:
            pass
        else:
            raise AssertionError("out-of-canvas placement was accepted")
        logo = {"name": "品牌Logo_验证", "role": "brand_logo", "box": {"x": 0, "y": 0, "width": 10, "height": 10}}
        validate_logos([logo])
        for invalid in ([], [dict(logo, visible=False)], [dict(logo, opacity=0)]):
            try:
                validate_logos(invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("missing/hidden Logo accepted")
        print("ok")
        return

    if args.verify_photoshop:
        verify_photoshop(args.verify_photoshop)
        return

    if not args.job or not args.manifest:
        parser.error("--job 和 --manifest 为必填参数")

    job_path = Path(args.job)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    if job.get("texts"):
        raise ValueError("当前模式不允许 texts/Type Layer；请将全部文字放入 layers")
    validate_logos(job["layers"])
    job["layers"] = sorted(job["layers"], key=lambda item: item.get("role") == "brand_logo")
    canvas = job["canvas"]
    width, height = int(canvas["width"]), int(canvas["height"])
    resolution = int(canvas.get("resolution", 300))
    if width <= 0 or height <= 0 or resolution <= 0 or not job["layers"]:
        raise ValueError("画布尺寸或图层清单无效")
    names = [item["name"] for item in job["layers"]]
    if len(names) != len(set(names)):
        raise ValueError("图层名称重复")
    threshold = int(job.get("white_threshold", 246))
    default_min_transparent_ratio = float(job.get("min_transparent_ratio", 0.55))
    assets_dir = Path(job["assets_dir"])
    assets_dir.mkdir(parents=True, exist_ok=True)

    layers = []
    preview = Image.new("RGBA", (width, height))
    for index, item in enumerate(job["layers"]):
        validate_layer(item)
        image = Image.open(item["path"])
        source_size = image.size
        source_has_alpha = bool(np.any(np.asarray(image.convert("RGBA"))[:, :, 3] < 255))
        x = y = 0
        logo_geometry = {}
        if item.get("role") == "brand_logo":
            image, x, y, logo_geometry = prepare_logo(image, item, (width, height))
        else:
            if abs((image.width / image.height) / (width / height) - 1) > float(job.get("max_aspect_error", 0.04)):
                raise ValueError(f"生成画布比例不同，不得拉伸纠正: {item['name']}")
            if item.get("require_source_alpha") and not source_has_alpha:
                raise ValueError(f"白色细节或闭合线稿要求真实透明源图: {item['name']}")
            image = image.resize((width, height), Image.Resampling.LANCZOS)
            if item.get("transparent", True):
                image = prepare_transparent_layer(image, threshold)
                alpha = np.asarray(image)[:, :, 3]
                if not np.any(alpha):
                    raise ValueError(f"隔离素材为空: {item['name']}")
                transparent_ratio = float(np.mean(alpha == 0))
                min_transparent_ratio = float(
                    item.get("min_transparent_ratio", default_min_transparent_ratio)
                )
                if transparent_ratio < min_transparent_ratio:
                    raise ValueError(f"透明区域不足，疑似混层: {item['name']}")
                opaque_ratio = float(np.mean(alpha > 0))
                max_opaque_ratio = item.get("max_opaque_ratio")
                if max_opaque_ratio is not None and opaque_ratio > float(max_opaque_ratio):
                    raise ValueError(f"不透明内容过多，疑似混入相框或相邻元素: {item['name']}")
                if item.get("target_bbox") is not None:
                    image = fit_generated_layer(image, item["target_bbox"])
            else:
                if source_has_alpha:
                    raise ValueError(f"背景源图必须完整不透明: {item['name']}")
                if item.get("target_bbox") is not None:
                    raise ValueError("完整背景不得通过 target_bbox 缩放局部内容")
                image = image.convert("RGB")
        output = assets_dir / f"{index:02d}.png"
        image.save(output)
        preview.alpha_composite(image.convert("RGBA"), (x, y))
        layer = {
                "name": item["name"],
                "path": str(output.resolve()),
                "x": x,
                "y": y,
                "width": image.width,
                "height": image.height,
                "transparent": bool(item.get("transparent", True)),
                "source_path": str(Path(item["path"]).resolve()),
                "source_size": list(source_size),
                "source_has_alpha": source_has_alpha,
            }
        if item.get("role") == "brand_logo":
            layer.update(logo_geometry)
            layer["role"] = "brand_logo"
            layer["box"] = item["box"]
        if "target_bbox" in item:
            layer["target_bbox"] = item["target_bbox"]
        if "semantic_text" in item:
            layer["semantic_text"] = item["semantic_text"]
        if "editable" in item:
            layer["editable"] = bool(item["editable"])
        if item["name"].startswith("文字图像_"):
            layer["editable"] = False
        for key in ("expected_text", "ocr_text", "ocr_reviewed_text"):
            if key in item:
                layer[key] = item[key]
        layers.append(layer)

    manifest = {
        "canvas": {
            "width": width,
            "height": height,
            "resolution": resolution,
            "colorMode": "RGB",
        },
        "layers": layers,
        "output": job["output"],
        "photoshop_app": job.get("photoshop_app", "Adobe Photoshop 2026"),
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path = manifest_path.with_suffix(".preview.png")
    preview.save(preview_path)
    manifest["preview"] = str(preview_path.resolve())
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(Path(args.manifest).resolve())


if __name__ == "__main__":
    main()
