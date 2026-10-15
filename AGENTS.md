# AGENTS.md — 抠图技能项目（image-matting-skill）

> 本文件是项目的**唯一入口**。任何 agent 接手本项目，必须最先完整阅读本文件。
> 所有任务都以本文件 + `docs/PROJECT_MAP.md` 为事实来源，不要依赖对话历史中的外部说明。

---

## 一、这个项目是做什么的

用户在本项目的对话窗中**直接发送一张图片**（无需任何文字指令）时：

1. agent 调用**自身内置的图像抠图 / 去背景 / 主体分离能力**，把主体从背景中分离，得到透明底 PNG；
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
- 一次发送多张图片 → 每张图**独立**执行一次完整工作流，各自归档。

## 五、执行步骤（详见 `skill/SKILL.md`）

1. 原图存档：保存到 `input/`（保留原图，便于溯源与重跑）；
2. 抠图：调用自身抠图能力 → 透明底 PNG（**尺寸必须与原图一致**）；
3. PSD：优先 agent 原生 PSD 能力；否则运行
   `python skill/scripts/build_psd.py --original <原图> --cutout <透明PNG> --output <PSD路径>`
4. 交付：对话框同时交付 PNG + PSD 两个文件；
5. 归档：`output/YYYYMMDD_HHMMSS/` 下放置 `原图名_cutout.png` + `原图名_cutout.psd`。

## 六、硬性规则（不得违反）

1. 每次任务**必须**同时交付 PNG + PSD 两份，不允许只给一张。
2. 每次任务**必须**在 `output/` 下新建独立时间戳文件夹，**不允许覆盖**已有产物。
3. 原图**必须**留存到 `input/`。
4. 透明底 PNG 尺寸必须与原图一致；主体边缘干净，发丝、半透明物尽量保留。
5. 产物（`input/`、`output/` 内容）不入 git 仓库（见 `.gitignore`），仓库只同步"项目本身"。

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
