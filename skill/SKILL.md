---
name: image-matting
description: 用户直接发送图片时自动执行抠图（去背景/主体分离），在对话框同时交付透明底 PNG 与 PSD 两个文件，并归档到 output/ 下按时间戳新建的文件夹。触发条件：收到图片且无其他明确任务。
version: 1.0.0
---

# 抠图技能（image-matting）

## 触发条件

- 用户在本项目对话窗**直接发送一张图片**，且未指定其他任务 → 立即执行本技能，无需额外上下文。
- 用户文字中包含"抠图 / 去背景 / 去底色 / 分离背景 / 透明底"等关键词 → 执行本技能。
- 可调配置见项目根目录 `config/skill.config.json`（本技能被安装到技能根目录后，配置仍以项目根 `config/skill.config.json` 为准，路径由 AGENTS.md 必读清单指引）。
- **执行边界**：本技能只调用宿主自身能力与项目现成脚本（`skill/scripts/` 下已有文件），**禁止为任务编写或修改任何脚本 / 项目文件**；需要改动项目本体时，由项目所有者另行处理。

## 输入

- 一张图片（PNG / JPG / JPEG / WEBP / BMP 等常见格式）。
- 多张图片 → 每张独立走完下述完整流程。

## 工作流

### 第 1 步：原图存档
- 把用户发送的图片保存到项目 `input/` 目录，文件名保留原名；重名时追加时间戳后缀（如 `photo_20261014_153000.jpg`）。

### 第 2 步：抠图（核心，调用宿主能力）
- 调用宿主 agent 内置的**图像抠图 / 去背景 / 主体分离**能力，生成透明底 PNG。
- **豆包 Work 环境映射（已验证可用）**：`mediakit-cli image remove-image-background --image-url <原图路径> --scene <general|human|product>`
  - `human`=真人人像；`product`=商品主体；`general`=通用（动漫/二次元、商标/Logo、不确定主体，或前两者效果不佳时改用）；
  - 返回透明 PNG 下载 URL（**有效期 24 小时，须立即下载**），默认输出与原图同尺寸；
  - 若模型输出尺寸与原图不一致，须缩放对齐到原图（build_psd.py 会自动告警并对齐）。
- 质量要求：
  - 输出尺寸与原图**完全一致**；
  - 主体边缘干净，发丝、半透明物（玻璃、纱等）尽量保留；
  - 背景完全透明（alpha=0），不残留白边 / 色边。

### 第 3 步：清晰化增强（统一开启，配置见 `config/skill.config.json` → `enhance`）
- 对第 2 步的透明 PNG 做清晰化处理（用户反馈直接输出可能偏糊；**增强后的 PNG 就是交付与归档的版本，文件名不变**）。
- 优先：调用宿主 agent 原生图像增强 / 锐化能力。
  - 豆包 Work 映射：`mediakit-cli image enhance-image --image-url <透明PNG>`（智能清晰化）；若其改变输出尺寸或效果不佳，改用 `mediakit-cli image sharpen-image --image-url <透明PNG>`（锐化，保持尺寸）。
  - **硬约束：增强后的 PNG 尺寸必须仍与原图一致**——若增强结果改变尺寸，先缩放对齐回原图尺寸再进入下一步。
- 兜底（宿主无增强能力 / 调用失败）：运行脚本（与 SKILL.md 同级目录）：

  ```powershell
  python skill/scripts/enhance_cutout.py --input <透明PNG> --output <增强PNG> --strength 1.0
  ```

  脚本只对 RGB 通道做 UnsharpMask 锐化，alpha 通道原样保留、尺寸不变；`--strength` 0.5~2.0（越大越锐）。
- 若增强环节整体失败：保留第 2 步的原始透明 PNG 继续后续流程（不阻塞交付），并在汇报中说明本次未增强。

### 第 4 步：生成 PSD
- 优先：宿主 agent 有原生 PSD / PS 兼容文件生成能力 → 生成三层 PSD（原图 / 透明主体 / 蒙版参考）。
- 兜底：运行脚本（脚本与 SKILL.md 同级目录）：

  ```powershell
  python skill/scripts/build_psd.py --original <input/原图> --cutout <增强PNG> --output <output/时间戳/原图名_cutout.psd>
  ```

  脚本生成三层（**图层名用英文** Original / Cutout / Mask Reference，保证 Photoshop 等软件跨平台显示兼容）：①原图 ②透明底抠图主体 ③抠图蒙版参考（白=保留 / 黑=去除，取自 PNG 的 alpha 通道）。
  抠图尺寸与原图不一致时，脚本自动缩放对齐并在 stderr 告警。

### 第 5 步：对话框交付
- **必须同时**交付两个文件：`原图名_cutout.png`（清晰化增强版）+ `原图名_cutout.psd`（使用宿主文件交付机制，如 present_files）。
- 交付文件与归档文件为同一份：先归档到 `output/` 再交付，或交付后立即同步归档，保证两边一致。

### 第 6 步：归档
- 在 `output/` 下新建文件夹，命名 `YYYYMMDD_HHMMSS`（本地时间、24 小时制，如 `20261014_153000`）。
- 文件夹内放置：`原图名_cutout.png`、`原图名_cutout.psd`。
- 同一秒内多次任务 → 文件夹名追加 `_1`、`_2`… 防重。

## 多图与异常

- 多张图：按收到顺序**逐张串行**执行完整流程（一张完整走完、交付并归档后再处理下一张），各自归档（一张图一个文件夹）、各自交付。
- agent 无抠图能力：明确说明无法执行，不生成假产物。
- 尺寸不一致：PSD 脚本自动缩放对齐并告警；PNG 应保证与原图一致。
- 任一环节失败：保留 `input/` 原图，向用户说明失败环节与原因。
