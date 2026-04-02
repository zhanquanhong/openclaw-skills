#!/bin/bash
# 发布到 GitHub Releases 脚本

set -e

REPO="zhanquanhong/openclaw-skills"
VERSION="v1.0.0"
RELEASE_NAME="TeamClaw 代码审查工具 v1.0.0"
RELEASE_NOTES="首发版本

## 🎯 功能特性

- ✅ 自动化代码安全审计（SQL 注入、命令注入、硬编码密码等）
- ✅ 代码规范检查（命名、注释、方法长度等）
- ✅ 性能问题分析（资源泄漏、低效操作等）
- ✅ 多代理并行审查（速度提升 2-3 倍）
- ✅ IDEA 右键集成（一键审查）
- ✅ 跨平台支持（Windows/Mac/Linux）

## 📦 安装包

- **Windows:** teamclaw-code-reviewer-v1.0.0.zip
- **Mac/Linux:** teamclaw-code-reviewer-v1.0.0.tar.gz

## 🚀 快速开始

### Windows
1. 下载并解压 zip
2. 双击 install.bat
3. 重启 IDEA
4. 右键代码 → External Tools → Code Review

### Mac/Linux
\`\`\`bash
tar -xzf teamclaw-code-reviewer-v1.0.0.tar.gz
cd teamclaw-code-reviewer-v1.0.0
chmod +x install.sh
./install.sh
\`\`\`

## 📖 详细文档

见包内 README.md 或 docs/code-review-quickstart.md

## 📞 反馈

遇到问题？提交 Issue: https://github.com/zhanquanhong/openclaw-skills/issues"

DIST_DIR="$HOME/.openclaw/workspace/distribution"
ZIP_FILE="$DIST_DIR/teamclaw-code-reviewer-v1.0.0.zip"
TARGZ_FILE="$DIST_DIR/teamclaw-code-reviewer-v1.0.0.tar.gz"

echo "📤 发布到 GitHub Releases"
echo "=========================="
echo ""
echo "仓库：$REPO"
echo "版本：$VERSION"
echo ""

# 检查 GitHub Token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ 未设置 GITHUB_TOKEN"
    echo ""
    echo "请设置环境变量："
    echo "  export GITHUB_TOKEN=your_github_personal_access_token"
    echo ""
    echo "Token 获取：https://github.com/settings/tokens"
    echo "需要权限：repo (完整控制私有仓库) 或 public_repo (仅公开仓库)"
    exit 1
fi

echo "✅ GitHub Token 已配置"
echo ""

# 检查文件
if [ ! -f "$ZIP_FILE" ]; then
    echo "❌ 找不到文件：$ZIP_FILE"
    exit 1
fi

if [ ! -f "$TARGZ_FILE" ]; then
    echo "❌ 找不到文件：$TARGZ_FILE"
    exit 1
fi

echo "📦 安装包文件:"
echo "   - $ZIP_FILE ($(du -h "$ZIP_FILE" | cut -f1))"
echo "   - $TARGZ_FILE ($(du -h "$TARGZ_FILE" | cut -f1))"
echo ""

# 创建 Release
echo "[1/3] 创建 Release..."
RESPONSE=$(curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$REPO/releases \
  -d "{
    \"tag_name\": \"$VERSION\",
    \"name\": \"$RELEASE_NAME\",
    \"body\": $(echo "$RELEASE_NOTES" | jq -Rs .),
    \"draft\": false,
    \"prerelease\": false
  }")

# 检查是否成功
if echo "$RESPONSE" | grep -q '"id"'; then
    RELEASE_ID=$(echo "$RESPONSE" | jq -r '.id')
    UPLOAD_URL=$(echo "$RESPONSE" | jq -r '.upload_url' | sed 's/{?name,label}//')
    echo "✅ Release 创建成功 (ID: $RELEASE_ID)"
    echo "   URL: https://github.com/$REPO/releases/tag/$VERSION"
else
    echo "❌ Release 创建失败"
    echo "$RESPONSE" | jq .
    exit 1
fi
echo ""

# 上传 ZIP 文件
echo "[2/3] 上传 Windows 安装包..."
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/zip" \
  --data-binary @"$ZIP_FILE" \
  "$UPLOAD_URL?name=teamclaw-code-reviewer-v1.0.0.zip" > /dev/null
echo "✅ Windows 安装包已上传"
echo ""

# 上传 TAR.GZ 文件
echo "[3/3] 上传 Mac/Linux 安装包..."
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/gzip" \
  --data-binary @"$TARGZ_FILE" \
  "$UPLOAD_URL?name=teamclaw-code-reviewer-v1.0.0.tar.gz" > /dev/null
echo "✅ Mac/Linux 安装包已上传"
echo ""

echo "=========================="
echo "✅ 发布完成！"
echo "=========================="
echo ""
echo "🌐 Release 链接:"
echo "   https://github.com/$REPO/releases/tag/$VERSION"
echo ""
echo "📥 下载链接:"
echo "   Windows: https://github.com/$REPO/releases/download/$VERSION/teamclaw-code-reviewer-v1.0.0.zip"
echo "   Mac/Linux: https://github.com/$REPO/releases/download/$VERSION/teamclaw-code-reviewer-v1.0.0.tar.gz"
echo ""
