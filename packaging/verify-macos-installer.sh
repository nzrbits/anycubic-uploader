#!/bin/bash
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true ]] || { echo 'Run installer verification on a disposable GitHub runner' >&2; exit 1; }
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cat "$PROJECT_ROOT/packaging/version.txt")"
PACKAGE="$PROJECT_ROOT/dist/AnycubicUploader-macOS-$(uname -m).pkg"
APP='/Applications/Anycubic Uploader.app'
DATA_DIR="$HOME/Library/Application Support/AnycubicUploader"
[[ ! -e "$APP" && ! -e "$DATA_DIR/config.json" ]] || { echo 'Test app or settings already exist' >&2; exit 1; }
mkdir -p "$DATA_DIR"
echo '{"token":"installer-test","watch_folders":[],"watch_extensions":[".pm4u"]}' > "$DATA_DIR/config.json"
CONFIG_HASH="$(shasum -a 256 "$DATA_DIR/config.json")"
sudo installer -pkg "$PACKAGE" -target /
test "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP/Contents/Info.plist")" = "$VERSION"
file "$APP/Contents/MacOS/Anycubic Uploader" | grep -q "$(uname -m)"
echo obsolete | sudo tee "$APP/Contents/Resources/installer-test-obsolete.txt" >/dev/null
sudo installer -pkg "$PACKAGE" -target /
test ! -e "$APP/Contents/Resources/installer-test-obsolete.txt"
test "$(shasum -a 256 "$DATA_DIR/config.json")" = "$CONFIG_HASH"
pkgutil --pkg-info com.anycubic.uploader
echo 'macOS install and reinstall passed; obsolete bundle files removed and settings preserved'
