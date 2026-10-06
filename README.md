# Anycubic Cloud Auto-Uploader

A Windows and macOS tray app that uploads `.pm4u` files to Anycubic Cloud.
Choose the folders where your slicer saves files. The app waits for each file to stop changing, then uploads it.

## Start from source

You need Python 3.10 or later with Tk support and an Anycubic Cloud account.

```sh
git clone https://github.com/nzrbits/anycubic-uploader
cd anycubic-uploader
```

On Windows, run this in PowerShell:

```powershell
.\start.ps1
```

On macOS:

```sh
chmod +x start.sh
./start.sh
```

The launcher creates a virtual environment and installs dependencies when needed.
If installation fails, run it again. It retries without treating the partial installation as complete.

Homebrew Python needs a separate Tk package. The launcher prints the package name if Tk is missing.
For Python 3.12, that is `brew install python-tk@3.12`.

## Use a standalone app

Download the Windows executable or macOS app from [Releases](https://github.com/nzrbits/anycubic-uploader/releases).
The packaged app includes Python.

## Enter your token

Right-click the tray icon and open **FAQ** for the [browser instructions](docs/faq.md).
Copy your Anycubic `XX-Token`, paste it into **Settings**, and save.

The app starts without a setup wizard. If no token is saved, it shows one red notification and stays in the tray.
Files wait until you save a token. The app does not read browser profiles or close browser windows.

## Choose folders

The default folder is `~/Downloads`.
Right-click the tray icon, open **Settings**, and add or remove folders.
The app watches files directly inside each folder; it does not scan subfolders.

Settings contains the folder list, file extensions and token.
Save applies the changes and checks the selected folders. Cancel leaves the settings unchanged.
Choose **Upload pending files** to check your folders immediately and retry failed uploads.
Files already recorded as uploaded are skipped.

New, modified and renamed files enter the same upload queue.
The app also scans every 30 seconds to find missed files and retry failures.
Only one upload runs at a time. Duplicate events for a pending file share one queue entry.

Successful uploads are recorded by file path, size and modification time.
An unchanged file is skipped on later scans. A failed file stays eligible even when newer files upload successfully.
The tray app and bulk command share this record to avoid uploading the same version concurrently.

Quitting stops new work, cancels the current transfer and releases its cloud reservation. An in-flight network request may take a few seconds to return.
Files left in the queue are found again on the next launch.
After a forced exit, an unfinished upload can be retried once its 20-minute reservation in the local record expires.

## Settings and logs

Settings and logs are stored in your user data folder:

| System | Default folder |
| --- | --- |
| Windows | `%LOCALAPPDATA%\AnycubicUploader` |
| macOS | `~/Library/Application Support/AnycubicUploader` |
| Linux | `$XDG_DATA_HOME/anycubic-uploader`, or `~/.local/share/anycubic-uploader` |

Set `ANYCUBIC_UPLOADER_DATA_DIR` to use another folder.
Source runs and packaged apps use the same paths.

| File | Contents |
| --- | --- |
| `config.json` | Token, watched folders and file extensions |
| `uploads.sqlite3` | Completed file versions and active uploads |
| `watcher.log` | Upload activity and errors; two rotated copies are kept |

Example settings:

```json
{
  "token": "<your XX-Token>",
  "watch_folders": ["~/Downloads", "~/Desktop/prints"],
  "watch_extensions": [".pm4u"]
}
```

Folder paths expand `~`. Extension matching ignores case.
Invalid settings produce an error instead of silently resetting your folders.
Keep `config.json` private: it contains your login token.

When upgrading a source checkout, an existing `config.json` next to the scripts is copied to the settings folder once.
The old `last_upload.json` timestamp cannot identify which files succeeded.
The first scan after upgrading may upload existing files again.

## Upload existing files

Windows:

```powershell
.venv\Scripts\python.exe upload_existing.py
```

macOS:

```sh
.venv/bin/python upload_existing.py
```

The command uses the same file checks and upload record as the tray app.
It prints uploaded, failed, deferred and skipped counts. Failed or deferred files give exit code 1.

Standalone Windows builds accept `AnycubicUploader.exe --upload-existing`.
For a macOS bundle, run `"Anycubic Uploader.app/Contents/MacOS/Anycubic Uploader" --upload-existing` in Terminal.
The Windows GUI executable does not open a console for command output.

## Replace an expired token

Follow the [FAQ](docs/faq.md), then replace the token in **Settings** and save.
The uploader reads the saved token before each attempt, so the running tray app picks up the replacement.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Authentication errors | Replace your token with the steps above |
| File keeps being deferred | Check whether your slicer is still writing it; empty files are also deferred |
| Folder is unavailable | Restore it or remove it in Settings |
| Upload failed | Open the log; the next scan retries the file |
| Tk import error on macOS | Install the matching `python-tk` Homebrew package |

If a transfer or registration fails, the app attempts to release its cloud reservation.
A rejected finalization counts as a failure.
The upload flow uses Anycubic's web API and can break if that API changes.

For login startup, see [autostart setup](docs/autostart.md).
For tests and builds, see [CONTRIBUTING.md](CONTRIBUTING.md).

MIT licensed.
