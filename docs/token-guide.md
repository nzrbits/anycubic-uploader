# Enter your Anycubic token

The uploader uses the `XX-Token` from your Anycubic Cloud login.
Copy it from your browser and paste it into the setup dialog.
The app does not inspect your browser profile.

## Chrome or Edge

1. Open [Anycubic Cloud](https://cloud-universe.anycubic.com/file) and log in.
2. Open developer tools with `F12`, or `Cmd+Option+I` on macOS.
3. Open **Application → Local Storage → https://cloud-universe.anycubic.com**.
4. Copy the full value of **XX-Token**.
5. Paste it into the uploader's setup dialog.

## Firefox

Open developer tools, then **Storage → Local Storage → https://cloud-universe.anycubic.com**.
Copy **XX-Token** and paste it into the setup dialog.

## Safari

Enable developer features in **Safari → Settings → Advanced**.
Open the Web Inspector, then select the Anycubic origin under **Storage → Local Storage**.
Copy **XX-Token**.

## Open setup again

Windows source checkout:

```powershell
.venv\Scripts\python.exe setup_token.py
```

macOS source checkout:

```sh
.venv/bin/python setup_token.py
```

Standalone Windows app:

```powershell
.\AnycubicUploader.exe --setup-token
```

Standalone macOS app:

```sh
"Anycubic Uploader.app/Contents/MacOS/Anycubic Uploader" --setup-token
```

The token is saved in `config.json` in the app's [settings folder](../README.md#settings-and-logs).
Setup hides the pasted value and does not print it.
Cancelling leaves the existing token unchanged.

If uploads fail with authentication errors, log in again and replace the saved token.
The running uploader uses the replacement on its next attempt.
