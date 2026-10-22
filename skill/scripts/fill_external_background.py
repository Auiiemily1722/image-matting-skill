#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fill_external_background.py — 抠图前「白底预处理」：把外部背景连通区染成深色，拉大背景与主体的对比。

背景问题（实测）：纯白/极浅背景 + 主体含大面积白色（白手套、眼白、白裙、白色商品等）时，
抠图模型分不清"背景的白"与"主体上的白"，会把主体白色区域误抠成透明
（实测 general/product 多轮仍漏白，需反复返工）。

本脚本：从图片四边做 BFS 泛洪，找出"外部背景"（与边缘连通且接近白色的区域），
染成深色。染色只发生在输入端——主体白色在深色背景上对比鲜明，抠图模型不再误抠；
模型输出的是 alpha 分割，染色不影响最终透明底，也无需反色恢复。
与 AGENTS.md 黑底反色规则对称（黑底白描 → 反色再抠；白底白主体 → 染深背景再抠）。

用法示例：
  python skill/scripts/fill_external_background.py --input <输入图> --output <input/原图名_bgfilled.png>

参数：
  --input            输入图片（必填）
  --output           输出图片（必填；建议存 input/原图名_bgfilled.png）
  --threshold        背景判定容差：像素到纯白 (255,255,255) 的欧氏距离上限，默认 40
  --color            染色颜色 R,G,B，默认 25,45,95（深蓝，避开主体常见色）
  --min-block-ratio  边缘白色连通块面积占全图比例低于此值不染色（防误染主体触边白块），默认 0.05
  --work-max-edge    内部检测用下采样边长上限（提速 BFS），默认 1024；掩码放大回原图后染色
"""

import argparse
import sys
from collections import deque

from PIL import Image


def build_mask(work, threshold, min_block_pixels):
    """返回 0/1 掩码（与 work 同尺寸）：1 = 外部背景连通区（应染色）。"""
    w, h = work.size
    px = work.load()
    visited = bytearray(w * h)
    mask = bytearray(w * h)
    thr2 = threshold * threshold

    seeds = []
    for x in range(w):
        seeds.append((x, 0))
        seeds.append((x, h - 1))
    for y in range(1, h - 1):
        seeds.append((0, y))
        seeds.append((w - 1, y))

    for sx, sy in seeds:
        idx = sy * w + sx
        if visited[idx]:
            continue
        r, g, b = px[sx, sy]
        if (r - 255) ** 2 + (g - 255) ** 2 + (b - 255) ** 2 > thr2:
            visited[idx] = 1
            continue

        # BFS 泛洪该白色连通块（8 邻域）
        block = []
        dq = deque([(sx, sy)])
        visited[idx] = 1
        while dq:
            x, y = dq.popleft()
            block.append(y * w + x)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if nx < 0 or nx >= w or ny < 0 or ny >= h:
                        continue
                    ni = ny * w + nx
                    if visited[ni]:
                        continue
                    visited[ni] = 1
                    nr, ng, nb = px[nx, ny]
                    if (nr - 255) ** 2 + (ng - 255) ** 2 + (nb - 255) ** 2 <= thr2:
                        dq.append((nx, ny))

        # 只染色面积达标的大块（防误染主体触边的白色小块/大块）
        if len(block) >= min_block_pixels:
            for i in block:
                mask[i] = 1
    return mask


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="输入图片路径")
    ap.add_argument("--output", required=True, help="输出图片路径")
    ap.add_argument("--threshold", type=int, default=40, help="背景判定容差（默认 40）")
    ap.add_argument("--color", default="25,45,95", help="染色颜色 R,G,B（默认 25,45,95 深蓝）")
    ap.add_argument("--min-block-ratio", type=float, default=0.05,
                    help="边缘白色连通块面积占比下限，低于不染色（默认 0.05）")
    ap.add_argument("--work-max-edge", type=int, default=1024,
                    help="内部检测下采样边长上限（默认 1024，提速 BFS）")
    args = ap.parse_args()

    try:
        img = Image.open(args.input).convert("RGB")
    except Exception as e:
        sys.exit(f"cannot open input image: {e}")
    ow, oh = img.size
    total = ow * oh
    scale = min(1.0, args.work_max_edge / float(max(ow, oh)))
    if scale < 1.0:
        work = img.resize((max(1, int(ow * scale)), max(1, int(oh * scale))), Image.BILINEAR)
    else:
        work = img
    w, h = work.size
    min_block_pixels = max(1, int(total * args.min_block_ratio * scale * scale))

    mask = build_mask(work, args.threshold, min_block_pixels)
    n = sum(mask)
    if n == 0:
        print(f"no external background block found (ratio<{args.min_block_ratio}), output = input copy")
        img.save(args.output)
        return

    # 掩码 0/1 -> 0/255，放大回原图尺寸，再与原图合成染色
    if scale < 1.0:
        mask_img = Image.frombytes("L", (w, h), bytes([255 if v else 0 for v in mask])).resize(
            (ow, oh), Image.NEAREST)
    else:
        mask_img = Image.frombytes("L", (w, h), bytes([255 if v else 0 for v in mask]))
    try:
        color = tuple(int(v) for v in args.color.split(","))
        if len(color) != 3:
            raise ValueError
    except ValueError:
        sys.exit("--color must be R,G,B")
    fill = Image.new("RGB", (ow, oh), color)
    out = Image.composite(fill, img, mask_img)
    out.save(args.output)
    print(f"filled external background: {n * 100.0 / (w * h):.1f}% of work image -> {args.output}")


if __name__ == "__main__":
    main()
