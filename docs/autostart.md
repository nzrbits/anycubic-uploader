# Autostart Setup

Set up the Anycubic Uploader to launch automatically when you log in.

---

## Windows

1. Press `Win+R`, type `shell:startup`, press Enter
2. The Startup folder opens in Explorer
3. Right-click inside → **New → Shortcut**
4. Target:
   ```
   powershell.exe -WindowStyle Hidden -File "C:\path\to\anycubic-uploader\start.ps1"
   ```
   Replace `C:\path\to\anycubic-uploader` with the actual folder path.
5. Name the shortcut `Anycubic Uploader`
6. Click **Finish**

The tray icon will appear on every login without a visible window.

---

## macOS

Create a Launch Agent that macOS runs at login.

1. Open Terminal and run:

```bash
INSTALL_DIR="$HOME/Applications/anycubic-uploader"   # change to your path
PLIST="$HOME/Library/LaunchAgents/com.anycubic.uploader.plist"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.anycubic.uploader</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/start.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/watcher.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/watcher.log</string>
</dict>
</plist>
EOF

chmod +x "$INSTALL_DIR/start.sh"
launchctl load "$PLIST"
echo "Autostart configured."
```

2. To disable autostart later:
```bash
launchctl unload ~/Library/LaunchAgents/com.anycubic.uploader.plist
```

3. To check if it's running:
```bash
launchctl list | grep anycubic
```

---

## macOS — using a pre-built .app

If you downloaded the `Anycubic Uploader.app`:

1. Move it to `/Applications` or `~/Applications`
2. Open **System Settings → General → Login Items**
3. Click `+` and select `Anycubic Uploader.app`

The app will launch at login and live only in the menu bar (no Dock icon).

---

## Disable autostart

**Windows:** Delete the shortcut from the Startup folder (`shell:startup`).

**macOS (Launch Agent):**
```bash
launchctl unload ~/Library/LaunchAgents/com.anycubic.uploader.plist
```

**macOS (Login Items):** System Settings → General → Login Items → select and press `−`.
