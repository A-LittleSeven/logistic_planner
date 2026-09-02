#!/bin/bash
# ─── 物流规划系统 Electron 打包脚本 ───
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔧 项目根目录: $PROJECT_DIR"

# 使用 npmmirror 镜像加速 Electron 下载（解决 GitHub 下载超时问题）
export ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
export ELECTRON_BUILDER_BINARIES_MIRROR="https://npmmirror.com/mirrors/electron-builder-binaries/"

# 1. 构建前端
echo ""
echo "📦 Step 1: 构建前端..."
cd "$PROJECT_DIR/frontend"
npm install
npm run build
echo "✅ 前端构建完成"

# 2. 安装 Electron 依赖
echo ""
echo "📦 Step 2: 安装 Electron 依赖..."
cd "$PROJECT_DIR"
npm install
echo "✅ Electron 依赖安装完成"

# 3. 打包 Electron 应用
echo ""
echo "📦 Step 3: 打包 Electron 应用..."
npx electron-builder --mac
echo ""
echo "✅ 打包完成! 输出目录: $PROJECT_DIR/dist-electron/"
echo ""
ls -la "$PROJECT_DIR/dist-electron/" 2>/dev/null || echo "(等待 electron-builder 输出...)"
