# Start the uploader at login

Save your token in Settings before enabling autostart. The installers do not enable it automatically.

## Windows

1. Press `Win+R` and enter `shell:startup`.
2. Create a shortcut in the Startup folder.
3. For a source checkout, use this target with your checkout path:

   ```text
   powershell.exe -WindowStyle Hidden -File "D:\Dev\anycubic-uploader\start.ps1"
   ```

For an installed app, copy its Start menu shortcut into the Startup folder.
For a portable build, create a shortcut to `AnycubicUploader.exe` instead.
Delete the shortcut to disable autostart.

## macOS app bundle

Move `Anycubic Uploader.app` to `/Applications` or `~/Applications`.
Open **System Settings → General → Login Items** and add it.
Remove the entry there to disable autostart.

## macOS source checkout

Create a Launch Agent. Replace `INSTALL_DIR` with your checkout path:

```sh
INSTALL_DIR="$HOME/Applications/anycubic-uploader"
DATA_DIR="$HOME/Library/Application Support/AnycubicUploader"
PLIST="$HOME/Library/LaunchAgents/com.anycubic.uploader.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$DATA_DIR"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.anycubic.uploader</string>
    <key>ProgramArguments</key>
    <array><string>$INSTALL_DIR/start.sh</string></array>
    <key>RunAtLoad</key><true/>
    <key>EnvironmentVariables</key>
    <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
    <key>StandardOutPath</key><string>$DATA_DIR/launch.stdout.log</string>
    <key>StandardErrorPath</key><string>$DATA_DIR/launch.stderr.log</string>
</dict>
</plist>
EOF

chmod +x "$INSTALL_DIR/start.sh"
launchctl bootstrap "gui/$(id -u)" "$PLIST"
```

To disable it:

```sh
launchctl bootout "gui/$(id -u)" ~/Library/LaunchAgents/com.anycubic.uploader.plist
```

Upload logs remain in the settings folder. Launcher output goes to the two `launch.*.log` files.
