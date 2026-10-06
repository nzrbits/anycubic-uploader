#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cat "$PROJECT_ROOT/packaging/version.txt")"
mkdir -p "$PROJECT_ROOT/build" "$PROJECT_ROOT/dist"
WORK="$(mktemp -d "$PROJECT_ROOT/build/macos-installer.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/root/Applications"
ditto "$PROJECT_ROOT/dist/Anycubic Uploader.app" "$WORK/root/Applications/Anycubic Uploader.app"
python3 - "$WORK/components.plist" <<'PY'
import plistlib
import sys

with open(sys.argv[1], "wb") as output:
    plistlib.dump([{
        "RootRelativeBundlePath": "Applications/Anycubic Uploader.app",
        "BundleIsRelocatable": False,
        "BundleIsVersionChecked": True,
        "BundleHasStrictIdentifier": True,
        "BundleOverwriteAction": "upgrade",
    }], output)
PY
pkgbuild --root "$WORK/root" --component-plist "$WORK/components.plist" \
    --install-location / --identifier com.anycubic.uploader --version "$VERSION" \
    "$PROJECT_ROOT/dist/AnycubicUploader-macOS-$(uname -m).pkg"
