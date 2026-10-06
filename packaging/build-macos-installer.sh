#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cat "$PROJECT_ROOT/packaging/version.txt")"
mkdir -p "$PROJECT_ROOT/build" "$PROJECT_ROOT/dist"
WORK="$(mktemp -d "$PROJECT_ROOT/build/macos-installer.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/root/Applications"
ditto "$PROJECT_ROOT/dist/Anycubic Uploader.app" "$WORK/root/Applications/Anycubic Uploader.app"
pkgbuild --analyze --root "$WORK/root" "$WORK/components.plist"
/usr/libexec/PlistBuddy -c 'Set :0:BundleIsRelocatable false' "$WORK/components.plist"
/usr/libexec/PlistBuddy -c 'Set :0:BundleOverwriteAction upgrade' "$WORK/components.plist"
pkgbuild --root "$WORK/root" --component-plist "$WORK/components.plist" \
    --install-location / --identifier com.anycubic.uploader --version "$VERSION" \
    "$PROJECT_ROOT/dist/AnycubicUploader-macOS-$(uname -m).pkg"
