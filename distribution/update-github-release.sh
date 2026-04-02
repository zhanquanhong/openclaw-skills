#!/bin/bash
# 更新 GitHub Releases 脚本

set -e

REPO="zhanquanhong/openclaw-skills"
VERSION="v1.0.0"
DIST_DIR="$HOME/.openclaw/workspace/distribution"
ZIP_FILE="$DIST_DIR/teamclaw-code-reviewer-v1.0.0.zip"
TARGZ_FILE="$DIST_DIR/teamclaw-code-reviewer-v1.0.0.tar.gz"

echo "📤 更新 GitHub Releases"
echo "=========================="
echo ""
echo "仓库：$REPO"
echo "版本：$VERSION"
echo ""

# 检查 GitHub Token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ 未设置 GITHUB_TOKEN"
    exit 1
fi

echo "✅ GitHub Token 已配置"
echo ""

# 获取 Release ID
echo "[1/4] 获取 Release 信息..."
RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$REPO/releases/tags/$VERSION)

if echo "$RESPONSE" | grep -q '"id"'; then
    RELEASE_ID=$(echo "$RESPONSE" | jq -r '.id')
    echo "✅ 找到现有 Release (ID: $RELEASE_ID)"
else
    echo "❌ 未找到 Release: $VERSION"
    exit 1
fi
echo ""

# 删除旧资产
echo "[2/4] 删除旧资产..."
ASSETS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$REPO/releases/$RELEASE_ID/assets)

# 删除每个资产
for asset_id in $(echo "$ASSETS" | jq -r '.[].id'); do
    curl -s -X DELETE -H "Authorization: token $GITHUB_TOKEN" \
      https://api.github.com/repos/$REPO/releases/assets/$asset_id > /dev/null
    echo "   删除资产 ID: $asset_id"
done
echo "✅ 旧资产已清理"
echo ""

# 上传新资产 - ZIP
echo "[3/4] 上传 Windows 安装包..."
UPLOAD_URL=$(echo "$RESPONSE" | jq -r '.upload_url' | sed 's/{?name,label}//')
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/zip" \
  --data-binary @"$ZIP_FILE" \
  "$UPLOAD_URL?name=teamclaw-code-reviewer-v1.0.0.zip" > /dev/null
echo "✅ Windows 安装包已上传"
echo ""

# 上传新资产 - TAR.GZ
echo "[4/4] 上传 Mac/Linux 安装包..."
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/gzip" \
  --data-binary @"$TARGZ_FILE" \
  "$UPLOAD_URL?name=teamclaw-code-reviewer-v1.0.0.tar.gz" > /dev/null
echo "✅ Mac/Linux 安装包已上传"
echo ""

echo "=========================="
echo "✅ 更新完成！"
echo "=========================="
echo ""
echo "🌐 Release 链接:"
echo "   https://github.com/$REPO/releases/tag/$VERSION"
echo ""
echo "📥 下载链接:"
echo "   Windows: https://github.com/$REPO/releases/download/$VERSION/teamclaw-code-reviewer-v1.0.0.zip"
echo "   Mac/Linux: https://github.com/$REPO/releases/download/$VERSION/teamclaw-code-reviewer-v1.0.0.tar.gz"
echo ""
