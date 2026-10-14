#!/usr/bin/env python3
"""build_psd.py — 由原图 + 透明底抠图 PNG 合成三层 PSD（PSD 兜底脚本）。

图层结构（自下而上，图层名用英文以避免 PSD 名称编码问题）：
  1. Original（原图）
  2. Cutout（透明底抠图主体）
  3. Mask Reference（抠图蒙版参考，白=保留 / 黑=去除，取自 PNG 的 alpha 通道）

用法：
  python build_psd.py --original original.jpg --cutout cutout.png --output out.psd

依赖：psd-tools（见项目根 requirements.txt）。
抠图尺寸与原图不一致时，脚本自动缩放对齐并在 stderr 告警。
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

try:
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer
except ImportError as exc:  # pragma: no cover
    sys.exit(f"[X] 缺少依赖：{exc}\n    请先运行 scripts/setup.ps1 或 pip install -r requirements.txt")


def load_rgba(path: str) -> Image.Image:
    with Image.open(path) as img:
        return img.convert("RGBA")


def build_mask_layer(cutout: Image.Image) -> Image.Image:
    """把 PNG alpha 通道转成可见的蒙版参考层（白=保留，黑=去除）。"""
    alpha = cutout.split()[-1]
    white = Image.new("L", alpha.size, 255)
    return Image.merge("RGBA", (alpha, alpha, alpha, white))


def main() -> None:
    parser = argparse.ArgumentParser(description="原图 + 透明PNG → 三层 PSD")
    parser.add_argument("--original", required=True, help="原图路径")
    parser.add_argument("--cutout", required=True, help="透明底抠图 PNG 路径")
    parser.add_argument("--output", required=True, help="输出 PSD 路径")
    args = parser.parse_args()

    original = load_rgba(args.original)
    cutout = load_rgba(args.cutout)

    if cutout.size != original.size:
        print(
            f"[warn] 抠图尺寸 {cutout.size} 与原图 {original.size} 不一致，已缩放对齐",
            file=sys.stderr,
        )
        cutout = cutout.resize(original.size, Image.LANCZOS)

    psd = PSDImage.new("RGBA", original.size)
    psd.append(PixelLayer.frompil(original, psd, "Original"))
    psd.append(PixelLayer.frompil(cutout, psd, "Cutout"))
    psd.append(PixelLayer.frompil(build_mask_layer(cutout), psd, "Mask Reference"))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    psd.save(str(out))
    print(f"[ok] PSD 已生成: {out}（3 层：Original 原图 / Cutout 透明底抠图主体 / Mask Reference 蒙版参考）")


if __name__ == "__main__":
    main()
