#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fill_external_background.py — 抠图前「背景染色预处理」：把外部背景连通区染成对比色，拉大背景与主体的对比。

背景问题（实测）：主体/图案内含与背景同色的大面积区域时（白背景+白主体、黑T恤+图案内黑色填充等），
抠图模型分不清"背景的颜色"与"主体上的同色"，会把主体同色区域误抠成透明。

本脚本：从图片四边做 BFS 泛洪，找出"外部背景"（与边缘连通且接近目标背景色的区域），
染成指定对比色。染色只发生在输入端——主体在对比色背景上边界分明，抠图模型不再误抠；
模型输出的是 alpha 分割，染色不影响最终透明底，也无需反色恢复。

用法示例：
  # 白背景 + 主体含大片白色（白贴白）：背景判定白色，染深色（默认）
  python skill/scripts/fill_external_background.py --input <输入图> --output <input/原图名_bgfilled.png>
  # 黑T恤/深底 + 图案内含深色填充（黑贴黑）：背景判定黑色，染图案中没有的亮色
  python skill/scripts/fill_external_background.py --input <输入图> --output <input/原图名_bgfilled.png> --target-color 0,0,0 --color 0,180,80

参数：
  --input            输入图片（必填）
  --output           输出图片（必填；建议存 input/原图名_bgfilled.png）
  --target-color     背景判定色 R,G,B，默认 255,255,255（白背景场景）；深底场景传 0,0,0
  --threshold        背景判定容差：像素到目标背景色的欧氏距离上限，默认 40
  --color            染色颜色 R,G,B，默认 25,45,95（深蓝）；深底场景传图案中不存在的亮色（避开图案主色）
  --min-block-ratio  边缘连通块面积占全图比例低于此值不染色（防误染主体触边块），默认 0.05
  --work-max-edge    内部检测用下采样边长上限（提速 BFS），默认 1024；掩码放大回原图后染色
"""

import argparse
import sys
from collections import deque

from PIL import Image


def build_mask(work, target, threshold, min_block_pixels, mode="edge"):
    """返回 0/1 掩码（与 work 同尺寸）：1 = 外部背景连通区（应染色）。

    mode="edge"   ：从图片四边泛洪，染与边缘连通的目标色大块（默认，白贴白/常规背景）
    mode="largest"：全图扫描，染图中面积最大的目标色连通块（整件衣物照片：T恤/物品不触边时，
                    最大色块通常就是衣物本体，染色后与图案内同色填充区分）
    """
    w, h = work.size
    px = work.load()
    visited = bytearray(w * h)
    mask = bytearray(w * h)
    tr, tg, tb = target
    thr2 = threshold * threshold

    if mode == "edge":
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
            if (r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2 > thr2:
                visited[idx] = 1
                continue

            # BFS 泛洪该目标色连通块（8 邻域）
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
                        if (nr - tr) ** 2 + (ng - tg) ** 2 + (nb - tb) ** 2 <= thr2:
                            dq.append((nx, ny))

            # 只染色面积达标的大块（防误染主体触边的白色小块/大块）
            if len(block) >= min_block_pixels:
                for i in block:
                    mask[i] = 1
        return mask

    # mode == "largest"：全图扫描目标色连通块，只染色面积最大的一块
    best = []
    for y in range(h):
        for x in range(w):
            idx = y * w + x
            if visited[idx]:
                continue
            r, g, b = px[x, y]
            if (r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2 > thr2:
                visited[idx] = 1
                continue
            block = []
            dq = deque([(x, y)])
            visited[idx] = 1
            while dq:
                cx, cy = dq.popleft()
                block.append(cy * w + cx)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = cx + dx, cy + dy
                        if nx < 0 or nx >= w or ny < 0 or ny >= h:
                            continue
                        ni = ny * w + nx
                        if visited[ni]:
                            continue
                        visited[ni] = 1
                        nr, ng, nb = px[nx, ny]
                        if (nr - tr) ** 2 + (ng - tg) ** 2 + (nb - tb) ** 2 <= thr2:
                            dq.append((nx, ny))
            if len(block) > len(best):
                best = block
    if len(best) >= min_block_pixels:
        for i in best:
            mask[i] = 1
    return mask


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="输入图片路径")
    ap.add_argument("--output", required=True, help="输出图片路径")
    ap.add_argument("--target-color", default="255,255,255", help="背景判定色 R,G,B（默认 255,255,255 白底；深底传 0,0,0）")
    ap.add_argument("--threshold", type=int, default=40, help="背景判定容差（默认 40）")
    ap.add_argument("--color", default="25,45,95", help="染色颜色 R,G,B（默认 25,45,95 深蓝）")
    ap.add_argument("--min-block-ratio", type=float, default=0.05,
                    help="边缘白色连通块面积占比下限，低于不染色（默认 0.05）")
    ap.add_argument("--mode", default="edge", help="染色模式：edge=四边泛洪染外部背景（默认）；largest=染图中最大目标色连通块（整件衣物/物品照片不触边时用）")
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

    try:
        target = tuple(int(v) for v in args.target_color.split(","))
        if len(target) != 3:
            raise ValueError
    except ValueError:
        sys.exit("--target-color must be R,G,B")

    mask = build_mask(work, target, args.threshold, min_block_pixels, mode=args.mode)
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
