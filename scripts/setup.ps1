# setup.ps1 — 一键配置（Windows PowerShell）
# 用法：
#   .\scripts\setup.ps1                          # 建目录 + 装依赖
#   .\scripts\setup.ps1 -SkillRoot "D:\skills"   # 额外把技能安装到指定 agent 技能根目录
param(
    [string]$SkillRoot = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "== 抠图技能项目 一键配置 ==" -ForegroundColor Cyan

# 1. 检查 Python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[X] 未检测到 Python。请先安装 Python 3.9+ 并勾选 'Add to PATH'。" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python: $($py.Source)"

# 2. 创建目录
New-Item -ItemType Directory -Force -Path (Join-Path $Root "input") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root "output") | Out-Null
Write-Host "[OK] 目录已就绪: input/ output/"

# 3. 虚拟环境 + 依赖
$venv = Join-Path $Root ".venv"
$venvPy = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "[..] 创建虚拟环境 .venv ..."
    python -m venv $venv
}
Write-Host "[..] 安装依赖 (psd-tools) ..."
& $venvPy -m pip install --upgrade pip -q
& $venvPy -m pip install -r (Join-Path $Root "requirements.txt") -q
Write-Host "[OK] 依赖安装完成"

# 4. 可选：安装技能到 agent 技能根目录
if ($SkillRoot) {
    $dest = Join-Path $SkillRoot "image-matting-skill"
    if (Test-Path $dest) {
        Write-Host "[!] 目标已存在，跳过安装: $dest" -ForegroundColor Yellow
    }
    else {
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item -Recurse -Force (Join-Path $Root "skill\*") $dest
        Write-Host "[OK] 技能已安装到: $dest"
    }
}

Write-Host ""
Write-Host "== 配置完成 ==" -ForegroundColor Green
Write-Host "下一步：让 agent 打开本项目文件夹，直接发送图片即可触发抠图。"
