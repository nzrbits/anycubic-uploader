# How to Find Your Anycubic Token

The Anycubic Uploader needs a login token from Anycubic Cloud to upload your files.
The easiest way is to run `setup_token.py`, which tries to extract it automatically.

If automatic extraction fails, here is how to find it manually.

---

## Automatic extraction (recommended)

**Windows:**
```powershell
.venv\Scripts\python.exe setup_token.py
```

**macOS / Linux:**
```bash
.venv/bin/python setup_token.py
```

The script will:
1. Try Microsoft Edge (Windows) or Google Chrome (macOS) to extract the token automatically
2. Fall back to a manual dialog if automatic extraction fails

---

## Manual extraction — Google Chrome or Edge

1. Open **[cloud-universe.anycubic.com/file](https://cloud-universe.anycubic.com/file)** in your browser
2. Log in with your Anycubic account
3. Open **DevTools**:
   - Windows/Linux: press `F12` or `Ctrl+Shift+I`
   - macOS: press `Cmd+Option+I`
4. Click the **Application** tab (you may need to expand the `»` menu)
5. In the left panel, expand **Storage → Local Storage**
6. Click on `https://cloud-universe.anycubic.com`
7. Find the key **`XX-Token`** in the list
8. **Double-click** the value cell and press `Ctrl+A` then `Ctrl+C` to copy the full token

   ![DevTools screenshot showing XX-Token key in Local Storage](./token-devtools.png)

9. Run `setup_token.py` and paste the token when prompted, or paste it directly into `config.json`:

```json
{
  "token": "eyJ...<paste your full token here>..."
}
```

---

## Manual extraction — Firefox

1. Open **[cloud-universe.anycubic.com/file](https://cloud-universe.anycubic.com/file)**
2. Log in
3. Press `F12` to open DevTools
4. Go to **Storage** tab
5. Expand **Local Storage → https://cloud-universe.anycubic.com**
6. Find `XX-Token` and copy its value

---

## Manual extraction — Safari (macOS)

1. Enable DevTools: **Safari → Settings → Advanced → Show features for web developers**
2. Open **[cloud-universe.anycubic.com/file](https://cloud-universe.anycubic.com/file)**
3. Log in
4. Press `Cmd+Option+I` to open Web Inspector
5. Go to **Storage** tab
6. Click **Local Storage → cloud-universe.anycubic.com**
7. Find `XX-Token` and copy its value

---

## Token expiry

Tokens expire after some time (typically weeks to months).
If uploads suddenly start failing with authentication errors, re-run `setup_token.py`
to get a fresh token — it will overwrite the old one in `config.json`.

---

## Security note

Your token is stored **locally only** in `config.json` next to the app.
It is never transmitted anywhere except to `cloud-universe.anycubic.com` during uploads.
The `config.json` file is excluded from git (listed in `.gitignore`).
