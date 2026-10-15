#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清晰化兜底脚本：对透明底 PNG 做确定性锐化（UnsharpMask）。

- 只对 RGB 通道做锐化，alpha 通道原样保留（透明区域不受影响）；
- 输出尺寸与输入完全一致（不改变尺寸/分辨率）；
- 用于宿主 agent 无原生增强能力、或原生增强调用失败时的兜底。

用法:
    python enhance_cutout.py --input <cutout.png> --output <enhanced.png> [--strength 1.0]

--strength 0.5~2.0（默认 1.0），越大越锐；过锐时可调低。
"""
import argparse
import sys

from PIL import Image, ImageFilter


def main() -> int:
    ap = argparse.ArgumentParser(description="对透明底 PNG 做清晰化锐化（尺寸不变、alpha 保留）")
    ap.add_argument("--input", required=True, help="输入透明 PNG（抠图结果）")
    ap.add_argument("--output", required=True, help="输出增强 PNG")
    ap.add_argument("--strength", type=float, default=1.0, help="锐化强度 0.5~2.0，默认 1.0")
    args = ap.parse_args()

    strength = max(0.0, min(2.0, args.strength))
    img = Image.open(args.input)
    img = img.convert("RGBA")

    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    # UnsharpMask 参数：radius 决定影响范围，percent 决定锐化幅度，threshold 避免噪声被放大
    radius = 2 if strength >= 1.0 else 1
    percent = int(100 + 50 * strength)  # strength=1.0 -> 150%
    sharp = rgb.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=3))

    out = sharp.convert("RGBA")
    out.putalpha(a)  # alpha 原样保留
    out.save(args.output, "PNG")

    print(f"enhanced: {args.input} -> {args.output} (strength={strength}, size={out.size[0]}x{out.size[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
