#!/bin/bash
# =============================================================================
# ZhiXing macOS Build Script
# 打包 + 签名 + 公证一站式
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ELECTRON_DIR="$SCRIPT_DIR/electron-app"
RELEASE_DIR="$ELECTRON_DIR/release"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=========================================="
echo "  ZhiXing macOS Build"
echo "  $(date)"
echo "=========================================="

# ── 环境检查 ──────────────────────────────────

echo ""
echo "🔍 环境检查..."

# 证书
CERT_COUNT=$(security find-identity -v -p basic 2>/dev/null | grep -c "Apple Distribution" || true)
if [ "$CERT_COUNT" -eq 0 ]; then
  echo "❌ 未找到 Apple Distribution 证书"
  echo "   请先在 Apple Developer 中下载并安装"
  exit 1
fi
echo "✅  Apple Distribution 证书已安装"

# Apple ID
if [ -z "${APPLE_ID:-}" ] && ! security find-generic-password -s "zhixing-notary" -w &>/dev/null; then
  echo "⚠️  未设置 APPLE_ID 环境变量，也未在 Keychain 中找到公证密码"
  echo "   公证（notarization）将跳过"
  echo "   设置方法:"
  echo "   export APPLE_ID='your@email.com'"
  echo "   security add-generic-password -s 'zhixing-notary' -a 'your@email.com' -w 'app-password'"
  SKIP_NOTARIZE=true
else
  echo "✅  Apple ID 已配置"
  SKIP_NOTARIZE=false
fi

# node_modules
if [ ! -d "$ELECTRON_DIR/node_modules" ]; then
  echo "📦  安装依赖..."
  cd "$ELECTRON_DIR"
  npm install
fi

# ── 版本號 ────────────────────────────────────

VERSION=$(node -e "console.log(require('$ELECTRON_DIR/package.json').version)")
echo ""
echo "📦  构建版本: v$VERSION"

# ── 清理 ──────────────────────────────────────

echo ""
echo "🧹  清理上次构建..."
rm -rf "$RELEASE_DIR"

# ── 选择构建目标 ──────────────────────────────

BUILD_TARGET="${1:-dmg}"
echo ""
echo "🎯  构建目标: $BUILD_TARGET"

case "$BUILD_TARGET" in
  dmg|mac)
    echo "   输出: DMG (notarized) + ZIP"
    echo "   适用于: 官网/GitHub 分发"
    TARGET_FLAG="--mac"
    ;;
  mas)
    echo "   输出: .pkg (Mac App Store)"
    echo "   适用于: App Store 提交"
    TARGET_FLAG="--mac=mas"
    ;;
  mas-dev)
    echo "   输出: .app (MAS Developer ID)"
    echo "   适用于: 本地 MAS 调试"
    TARGET_FLAG="--mac=mas-dev"
    ;;
  all)
    echo "   输出: DMG + MAS"
    TARGET_FLAG="--mac --mac=mas"
    ;;
  *)
    echo "❌  未知目标: $BUILD_TARGET"
    echo "   可用: dmg | mas | mas-dev | all"
    exit 1
    ;;
esac

# ── 构建 ──────────────────────────────────────

echo ""
echo "🏗️  构建中..."
cd "$ELECTRON_DIR"

if [ "$SKIP_NOTARIZE" = true ]; then
  echo "   (跳过公证)"
  npx electron-builder $TARGET_FLAG --config.afterSign=""
else
  npx electron-builder $TARGET_FLAG
fi

echo ""
echo "✅  构建完成！"

# ── 输出 ──────────────────────────────────────

echo ""
echo "📂  输出目录: $RELEASE_DIR"
echo ""
ls -lh "$RELEASE_DIR" 2>/dev/null || echo "   (空)"

# ── 后续步骤 ──────────────────────────────────

echo ""
echo "──────────────────────────────────────"
echo "  后续步骤:"
echo ""

case "$BUILD_TARGET" in
  dmg|mac)
    echo "  1. 验证签名: codesign -dv --verbose=4 \"$RELEASE_DIR\"/*.app"
    echo "  2. 验证公证: spctl -a -t install -v \"$RELEASE_DIR\"/*.app"
    echo "  3. 上传到 GitHub Release"
    ;;
  mas)
    echo "  1. 打开 Xcode -> Window -> Organizer"
    echo "  2. 导入 $RELEASE_DIR/*.pkg"
    echo "  3. 提交到 App Store Connect"
    ;;
esac

echo ""
echo "⏱️  耗时: $(date)"

exit 0
