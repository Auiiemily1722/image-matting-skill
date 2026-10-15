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
- 多张图片 → 每张独立走完下述完整流程；**同一批任务共用一个 `output/时间戳/` 文件夹**（文件名 `原图名_cutout.*` 区分）。

## 工作流

### 第 1 步：原图存档
- 把用户发送的图片保存到项目 `input/` 目录，文件名保留原名；重名时追加时间戳后缀（如 `photo_20261014_153000.jpg`）。

### 第 2 步：超分清晰化（对原图，优先；配置见 `config/skill.config.json` → `enhance`）
- 用户反馈直接抠图输出偏糊、分辨率低（原图本身多是小图）。因此**先对原图做 AI 超分增强，再抠图**——输出分辨率随超分提升，而不是锐化一张小图。
- 优先：调用宿主 agent 原生图像增强能力。
  - 豆包 Work 映射：`mediakit-cli image enhance-image --image-url <原图> --multiple 2`
    - `--multiple` 超分倍数（standard 支持 1~8，默认 2）；`--tool-version professional` 效果更好（可选）；
    - 规则：原图长边 < `enhance.target_long_edge`（默认 1024）时才超分；增强图保存为 `input/原图名_enhanced.png`，作为后续抠图与 PSD 的输入；
    - 下载增强结果 URL 用 `curl.exe -L -o "<保存路径>" "<URL>"`（见下方「下载约定」）。
- 兜底（宿主无增强能力 / 调用失败）：跳过超分，直接用原图抠图；抠图完成后对透明 PNG 运行锐化脚本（不增加分辨率，仅改善观感）：

  ```powershell
  python skill/scripts/enhance_cutout.py --input <透明PNG> --output <增强PNG> --strength 1.0
  ```

  脚本只对 RGB 通道做 UnsharpMask 锐化，alpha 通道原样保留、尺寸不变；`--strength` 0.5~2.0（越大越锐）。并在此次汇报中说明"本次未超分，仅锐化"。

### 第 3 步：抠图（核心，调用宿主能力）
- 对**第 2 步的输出图（超分原图或原图）**调用宿主 agent 内置的**图像抠图 / 去背景 / 主体分离**能力，生成透明底 PNG。
- **豆包 Work 环境映射（已验证可用）**：`mediakit-cli image remove-image-background --image-url <超分原图或原图> --scene <general|human|product>`
  - `human`=真人人像；`product`=商品主体；`general`=通用（动漫/二次元、商标/Logo、不确定主体，或前两者效果不佳时改用）；
  - 返回透明 PNG 下载 URL（**有效期 24 小时，须立即下载**），默认输出与输入同尺寸（即 ≥ 原图）；
  - 若模型输出尺寸与输入不一致，须缩放对齐到输入尺寸（build_psd.py 会自动告警并对齐）。
- **下载约定**：所有云端结果 URL 一律用 `curl.exe -L -o "<保存路径>" "<URL>"` 下载；**禁止**用 `Invoke-WebRequest -OutFile` 或裸 `curl`（PowerShell 里 `curl` 是 Invoke-WebRequest 的别名，两者都会触发系统确认弹窗）。
- 质量要求：
  - 输出尺寸与抠图输入尺寸**一致**（≥ 原图尺寸）；
  - 主体边缘干净，发丝、半透明物（玻璃、纱等）尽量保留；
  - 背景完全透明（alpha=0），不残留白边 / 色边。

### 第 4 步：生成 PSD
- 优先：宿主 agent 有原生 PSD / PS 兼容文件生成能力 → 生成三层 PSD（原图 / 透明主体 / 蒙版参考），原图层用第 2 步的超分原图。
- 兜底：运行脚本（脚本与 SKILL.md 同级目录）：

  ```powershell
  python skill/scripts/build_psd.py --original <超分原图或原图> --cutout <透明PNG> --output <output/时间戳/原图名_cutout.psd>
  ```

  脚本生成三层（**图层名用英文** Original / Cutout / Mask Reference，保证 Photoshop 等软件跨平台显示兼容）：①原图 ②透明底抠图主体 ③抠图蒙版参考（白=保留 / 黑=去除，取自 PNG 的 alpha 通道）。
  抠图尺寸与输入不一致时，脚本自动缩放对齐并在 stderr 告警。

### 第 5 步：对话框交付
- **必须同时**交付两个文件：`原图名_cutout.png`（超分高清版）+ `原图名_cutout.psd`（使用宿主文件交付机制，如 present_files）。
- 交付文件与归档文件为同一份：先归档到 `output/` 再交付，或交付后立即同步归档，保证两边一致。

### 第 6 步：归档
- 在 `output/` 下新建文件夹，命名 `YYYYMMDD_HHMMSS`（本地时间、24 小时制，如 `20261014_153000`）。
- **同一批任务（一次发送的多张图）共用一个文件夹**：文件夹内按 `原图名_cutout.png` / `原图名_cutout.psd` 区分各图。
- 同一秒内多批任务 → 文件夹名追加 `_1`、`_2`… 防重。

## 多图与异常

- 多张图：按收到顺序**逐张串行**执行完整流程（一张完整走完、交付并归档后再处理下一张）；**同一批任务的产物共用一个 `output/时间戳/` 文件夹**（靠 `原图名_cutout.*` 文件名区分），各自交付。
- agent 无抠图能力：明确说明无法执行，不生成假产物。
- 尺寸不一致：PSD 脚本自动缩放对齐并告警；PNG 应保证与抠图输入尺寸一致（≥ 原图）。
- 任一环节失败：保留 `input/` 原图，向用户说明失败环节与原因。
