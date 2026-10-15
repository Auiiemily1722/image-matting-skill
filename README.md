# image-matting-skill · 抠图技能项目

给具备**多模态抠图能力**的 agent 使用的操作指南项目：用户在对话窗直接发一张图，agent 自动抠图（去背景），并同时交付 **透明底 PNG** + **Photoshop 可直接打开的 PSD**，产物自动归档到 `output/时间戳/`。

> 本项目是**操作指南**，不内置抠图引擎——宿主 agent 必须自带抠图/去背景能力。

## 快速开始（新设备，约 1 分钟）

```powershell
# 1. 克隆仓库
git clone https://github.com/Auiiemily1722/image-matting-skill.git
cd image-matting-skill

# 2. 一键配置（需要 Python 3.9+）
.\scripts\setup.ps1
```

> 在**另一台电脑**用豆包 Work 一键安装：把 `docs/一键安装提示词.md` 里的提示词整段发给 agent 即可（自动克隆+配置+自检）。

## 使用

1. 让 agent 打开 / 接手本项目文件夹；
2. 在对话窗**直接发送一张图片**（无需任何文字）；
3. agent 自动交付 `原图名_cutout.png` + `原图名_cutout.psd`，并归档到 `output/YYYYMMDD_HHMMSS/`。

## 目录地图（详细版见 `docs/PROJECT_MAP.md`）

| 路径 | 用途 |
|---|---|
| `AGENTS.md` | agent 唯一入口：项目定位、必读清单、触发规则、硬性规则 |
| `skill/` | 技能本体：`SKILL.md` + PSD 兜底脚本 `scripts/build_psd.py` |
| `config/skill.config.json` | 机器可读默认值（触发/命名/路径） |
| `docs/PROJECT_MAP.md` | 项目地图与手册（agent 详读） |
| `scripts/setup.ps1` | 一键配置脚本 |
| `input/` | 输入原图留档 |
| `output/` | 产物归档：`output/YYYYMMDD_HHMMSS/` |

## 前置条件

- 宿主 agent 具备图像抠图（去背景/主体分离）能力；
- 本机 Python 3.9+（仅 PSD 兜底脚本需要）；
- 首次运行 setup 时联网安装 `psd-tools`。

## 常见问题

- **PSD 怎么来的？** 优先用 agent 原生 PSD 能力；没有则运行 `skill/scripts/build_psd.py` 由 原图+透明PNG 合成三层 PSD。
- **产物会进 git 吗？** 不会。`input/`、`output/` 默认被 `.gitignore` 忽略，仓库只同步项目本身；需要同步产物请用 git-lfs（见 PROJECT_MAP）。
- **agent 没有抠图能力？** 本项目不可用，AGENTS.md 会明确告知。
