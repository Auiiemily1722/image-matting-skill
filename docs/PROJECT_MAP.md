# 项目地图与手册（PROJECT_MAP）

> 给 agent 和人类共用的详细手册。接手项目先读 `AGENTS.md`，执行任务读 `skill/SKILL.md`，本文件用于弄清每个路径是干什么的、产物放哪。

## 1. 项目定位

**一句话**：用户在对话窗发图 → agent 用自身抠图能力去背景 → 交付 PNG + PSD → 归档到 `output/`。

**三条铁律**：
1. 交付永远成对（PNG + PSD），不拆单；
2. 每批任务在 `output/` 下新建独立时间戳文件夹（一批图共用一个），不覆盖；
3. 原图必存 `input/`。

## 2. 目录逐项说明

| 路径 | 类型 | 用途 | 谁读写 |
|---|---|---|---|
| `AGENTS.md` | 文档 | 唯一入口：定位、必读清单、触发规则、硬性规则 | agent 必读 |
| `README.md` | 文档 | 人类使用说明 | 人类 |
| `.gitignore` | 配置 | 产物/环境不入库 | git |
| `.gitattributes` | 配置 | LF 行尾统一，跨设备协作 | git |
| `requirements.txt` | 配置 | 依赖清单（仅 psd-tools） | setup.ps1 |
| `config/skill.config.json` | 配置 | **机器可读默认值**：触发开关、命名格式、路径约定 | agent 执行时读 |
| `docs/PROJECT_MAP.md` | 文档 | 本文件 | agent/人类 |
| `skill/SKILL.md` | 技能 | 技能定义 + 6 步执行流程（可被安装为运行时技能） | agent 执行时读 |
| `skill/scripts/build_psd.py` | 脚本 | PSD 兜底：原图+透明PNG → 三层 PSD | agent 调用 |
| `skill/scripts/enhance_cutout.py` | 脚本 | 清晰化兜底：透明PNG → 锐化增强PNG（尺寸不变、alpha 保留） | agent 调用 |
| `scripts/setup.ps1` | 脚本 | 一键配置：建目录、装依赖、可选安装技能 | 人类/agent 首次运行 |
| `input/` | 数据 | **输入原图留档**（原图 + 超分中间图 `原图名_enhanced.png`） | agent 写入 |
| `output/` | 产物 | **生成结果归档**（每批任务一个时间戳子文件夹，含各图 PNG+PSD） | agent 写入 |

## 3. 一次完整任务的路径流（示例）

用户发送 `product.jpg`，本地时间 2026-10-14 15:30:00：

```
用户对话框 ── product.jpg
   │
   ▼
input/product.jpg                          ← 第1步：原图存档
   │
   ▼（宿主 enhance-image 超分，原图长边<1024 时；无能力则用原图+锐化兜底）
input/product_enhanced.png                 ← 第2步：超分清晰化
   │
   ▼（agent 自身抠图能力）
product_cutout.png（透明底，尺寸=超分后）    ← 第3步：抠图
   │
   ▼（build_psd.py 兜底 或 agent 原生能力）
product_cutout.psd                          ← 第4步：PSD
   │
   ├── 对话框交付：product_cutout.png + product_cutout.psd   ← 第5步
   └── output/20261014_153000/（同一批图共用一个文件夹）
          ├── product_cutout.png           ← 第6步：归档
          └── product_cutout.psd
```

同一秒多批任务 → `output/20261014_153000_1/`、`_2/`… 防重。

## 4. 命名规范（与 config/skill.config.json 对应）

| 项 | 规则 | 示例 |
|---|---|---|
| 归档文件夹 | `YYYYMMDD_HHMMSS`（本地时间，24h，无冒号） | `20261014_153000` |
| PNG | `原图名_cutout.png`（原图名=去扩展名的文件名） | `product_cutout.png` |
| PSD | `原图名_cutout.psd` | `product_cutout.psd` |
| 原图留档 | 原名；重名追加时间戳 | `product.jpg` / `photo_20261014_153000.jpg` |
| 超分中间图 | `原图名_enhanced.png`（存 `input/`，供抠图与 PSD 使用） | `product_enhanced.png` |
| 同秒防重 | 文件夹名追加 `_1` `_2` | `20261014_153000_1` |

## 5. 技能安装（可选，让 agent 自动发现技能）

```powershell
.\scripts\setup.ps1 -SkillRoot "C:\路径\到\agent技能根目录"
```

会把 `skill/` 整体复制为 `<技能根目录>/image-matting-skill/`。不安装也不影响使用——agent 读 `AGENTS.md` 就能执行整个流程。

## 6. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| agent 说"无法抠图" | 宿主 agent 无抠图能力 | 本项目不可用，换支持抠图的 agent |
| agent 问"用什么抠图" | 豆包 Work 内置 MediaKit 抠图 | `mediakit-cli image remove-image-background`，场景选择见 skill/SKILL.md 第 2 步（已验证可用） |
| `build_psd.py` 报 ModuleNotFoundError | 未装依赖 | 运行 `scripts/setup.ps1` |
| PSD 打不开 | 产物损坏/未走脚本 | 检查 `output/` 对应文件夹，重跑该任务 |
| 中文文件名乱码 | 终端编码 | PowerShell 用 `chcp 65001` 或 Windows Terminal |
| 增强后过锐 / 不自然 | 兜底锐化强度过高 | 调低 `config/skill.config.json` → `enhance.fallback_strength`（0.5 起步），或改 `mode: on_blur` 仅模糊时增强 |
| 输出很糊 / 分辨率低 | 原图本身分辨率太低 | 流程默认先 AI 超分再抠图（`enhance-image --multiple 2`）；仍不够清晰可调高 `enhance.upscale_multiple` / `target_long_edge`，或换 `--tool-version professional` |
| 执行窗口 agent 想自己写脚本 / 改项目 | 未读 AGENTS.md 或偏离定位 | 明确告知：禁止编写或修改脚本，只准调用 `skill/scripts/` 现成脚本与宿主自身能力（AGENTS.md 硬性规则 6）；需要改动项目由所有者处理 |
| 想在多设备同步产物 | 产物默认不入库 | 见下节 git-lfs |

## 7. git 与产物同步

- **默认**：`input/`、`output/` 被 `.gitignore` 忽略，仓库只同步项目本身（文档/技能/配置/脚本），体积小、clone 快。
- **需要同步产物**（可选）：启用 git-lfs 后，把 `output/` 加入跟踪：
  ```powershell
  git lfs install
  git lfs track "output/**"
  git add .gitattributes output
  git commit -m "track outputs with lfs"
  ```

## 8. 修改默认行为的入口

所有可调项集中在 `config/skill.config.json`：
- `trigger.ask_first`：改 `true` 后，仅发图不说话时会先询问再执行（默认直接执行）；
- `trigger.keywords`：增减触发关键词；
- `output.*`：改文件夹/文件命名格式；
- `enhance.enabled`：`true`=每次抠图前统一超分增强 / `false`=关闭增强；
- `enhance.mode`：`uniform`=全部增强（当前）；`on_blur`=仅模糊时增强（备选，暂未启用）；
- `enhance.upscale_multiple`：超分倍数（standard 1~8，默认 2）；
- `enhance.target_long_edge`：目标长边 px（原图长边小于该值才超分，默认 1024）；
- `enhance.fallback_strength`：无宿主增强能力时的兜底锐化强度（0.5~2.0）；
- `psd.layers`：增删 PSD 图层。

改完配置无需重新安装，agent 每次执行都会重新读取。
