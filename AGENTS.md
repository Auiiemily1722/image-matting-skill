# AGENTS.md — 抠图技能项目（image-matting-skill）

> 本文件是项目的**唯一入口**。任何 agent 接手本项目，必须最先完整阅读本文件。
> 所有任务都以本文件 + `docs/PROJECT_MAP.md` 为事实来源，不要依赖对话历史中的外部说明。

---

## 一、这个项目是做什么的

用户在本项目的对话窗中**直接发送一张图片**（无需任何文字指令）时：

1. agent 调用**自身内置的图像抠图 / 去背景 / 主体分离能力**，把主体从背景中分离，得到透明底 PNG，并做**超分清晰化**（**先对原图做 AI 超分增强再抠图**，输出高清版；优先宿主原生能力，脚本兜底）；
2. 在对话框**同时交付两个文件**：`原图名_cutout.png`（透明底）+ `原图名_cutout.psd`（Photoshop 可直接打开，三层：原图 / 透明主体 / 蒙版参考，图层名为英文 Original / Cutout / Mask Reference）；
3. 两份文件同时归档到 `output/YYYYMMDD_HHMMSS/`（每次任务新建一个时间戳文件夹，互不覆盖）。

## 二、前置条件（硬性）

- 宿主 agent **必须具备图像抠图（去背景 / 主体分离）能力**。本项目是"操作指南"，不内置抠图引擎，也不提供离线抠图工具。
  - 在豆包 Work 环境中，该能力 = 内置 MediaKit 云端抠图 `mediakit-cli image remove-image-background`（已验证可用），调用细节见 `skill/SKILL.md` 第 2 步。
- 本地唯一软件依赖：Python 3.9+ 与 `psd-tools`（仅用于 PSD 兜底脚本 `skill/scripts/build_psd.py`）。
- 一键配置：`scripts/setup.ps1`（Windows PowerShell）。

## 三、必读清单（按任务类型）

| 场景 | 必读文件 |
|---|---|
| 任何任务（接手项目、被询问项目） | 本文件（AGENTS.md） |
| 执行抠图任务 | `skill/SKILL.md`（操作流程）→ `config/skill.config.json`（可调默认值） |
| 需要目录/路径/细节 | `docs/PROJECT_MAP.md` |
| 人类阅读 | `README.md`（agent 可跳过） |

## 四、触发规则（重要）

- 用户**直接发送一张图片**、且未给出其他明确任务 → **立即执行抠图工作流**，不要反问、不要等待额外指令。
- 用户发送图片并附带"抠图 / 去背景 / 去底色 / 分离背景 / 透明底"等文字 → 同样执行。
- 用户发送图片但明确要求其他操作（如"分析这张图""翻译图中文字"）→ 按用户要求执行，不触发抠图。
- 一次发送多张图片 → 每张图**独立**执行一次完整工作流，按收到顺序**逐张串行处理**（一张完整走完、交付并归档后再处理下一张）；**同一批任务的产物共用一个 `output/时间戳/` 文件夹**（靠 `原图名_cutout.*` 文件名区分），同一秒多批用 `_1/_2` 后缀防重。

## 五、执行步骤（详见 `skill/SKILL.md`）

1. 原图存档：保存到 `input/`（保留原图，便于溯源与重跑）；**大图预处理**：原图 >10MB 或长边 >4096 时先 `mediakit-cli image resize-image` 压到长边 2048 再存；
2. 清晰化：**先对原图做清晰化再抠图**：**默认全图先走 seedream 4K 高清重绘**（豆包 Work 走 doubao-creative-design 流程 image_edit 参考生成，prompt=“4k，保持图片中图案原本的颜色，平面插画效果，内容完全不变，让图片变清晰”，目标长边 2048，结果临时存 `input/原图名_seedream_raw.png`，再做一次 RGB 锐化（`enhance_cutout.py --strength 1.2`）后存 `input/原图名_enhanced.png`）；**自检（必须）**：seedream 结果**已清晰、无**明显乱码/错字、内容崩坏、材质/风格明显改变（变毛绒/3D/涂抹）→ **直接抠图（省掉超分）**；否则**回退超分+线条锐化**保字路线（`enhance-image --multiple <m>`，m=min(8,max(2,round(2048/原图长边)))，校验尺寸放大，未放大用 `--target-width/--target-height` 重试，超分后再跑 `enhance_cutout.py --strength 1.2`；**超分结果同样自检**，出现明显乱码/错字再降级锐化兜底或原图抠图并说明）；**自检标准**：只认**明显乱码/错字、内容崩坏、材质/风格明显改变**，**轻微文字补全（如 PLANE→PLANET）不算改写**；**一次只走一条路线，禁止两条都生成**；professional 超分（会重写个别字符，含文字图禁用）；超分不可用时原图直接抠图+锐化兜底（汇报说明）；
3. 抠图：对（超分后）原图调用自身抠图能力 → 透明底 PNG（**尺寸=抠图输入尺寸，必须 ≥ 原图**）；
4. PSD：优先 agent 原生 PSD 能力；否则运行
   `python skill/scripts/build_psd.py --original <超分原图或原图> --cutout <透明PNG> --output <PSD路径>`
5. 交付：对话框同时交付 PNG（AI 高清清晰化版）+ PSD 两个文件；
6. 归档：`output/YYYYMMDD_HHMMSS/` 下放置各图 `原图名_cutout.png` + `原图名_cutout.psd`（**同一批图共用一个文件夹**）。

## 六、硬性规则（不得违反）

1. 每次任务**必须**同时交付 PNG + PSD 两份，不允许只给一张。
2. 每批任务**必须**在 `output/` 下新建独立时间戳文件夹（同一批多张图共用一个），**不允许覆盖**已有产物。
3. 原图**必须**留存到 `input/`。
4. 透明底 PNG 尺寸以**抠图输入尺寸**为准（必须 ≥ 原图尺寸）；主体边缘干净，发丝、半透明物尽量保留；交付版为超分增强后的高清版本。
5. 产物（`input/`、`output/` 内容）不入 git 仓库（见 `.gitignore`），仓库只同步"项目本身"。
6. 执行窗口**禁止编写 / 修改任何脚本或项目文件**，只准调用项目现成脚本（`build_psd.py` / `enhance_cutout.py`）与宿主自身能力；需要改动项目本体时，由项目所有者另行处理。

## 七、目录地图（速览，详见 `docs/PROJECT_MAP.md`）

```
抠图测试/                ← git 仓库根（远程：image-matting-skill）
├── AGENTS.md            ← 本文件（唯一入口）
├── README.md            ← 人类使用说明（agent 可跳过）
├── .gitignore           ← 产物/环境不入库
├── .gitattributes       ← LF 行尾统一（跨设备）
├── requirements.txt     ← 仅 psd-tools
├── config/              ← 机器可读默认值（触发/命名/路径/开关）
│   └── skill.config.json
├── docs/
│   └── PROJECT_MAP.md   ← 项目地图与手册（详细）
├── skill/               ← 技能本体（可整体安装到 agent 技能根目录）
│   ├── SKILL.md         ← 技能定义 + 执行流程
│   └── scripts/
│       └── build_psd.py ← PSD 兜底：原图+透明PNG → 三层PSD
├── scripts/
│   └── setup.ps1        ← 一键配置（Windows PowerShell）
├── input/               ← 输入原图留档
└── output/              ← 产物归档（output/YYYYMMDD_HHMMSS/）
```

## 八、失败处理

- agent 无抠图能力 → 明确告知"本技能需要宿主 agent 具备抠图能力"，**不假装完成**。
- 抠图或 PSD 生成失败 → 保留 `input/` 原图，向用户说明失败环节与原因。
- 环境缺依赖（psd-tools 未安装）→ 提示运行 `scripts/setup.ps1`。
