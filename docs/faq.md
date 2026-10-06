# FAQ

## Where do I enter my token?

Right-click the tray icon and open **Settings**. Paste the token into **Anycubic token**, then click **Save**.
The field hides the value. Cancel keeps your previous settings.

If no token is saved, the app shows one red notification at startup and stays in the tray.
Uploads wait until you save a token. Saving settings checks the watched folders immediately.

## How do I get a token?

Open [Anycubic Cloud](https://cloud-universe.anycubic.com/file) in your desktop browser and log in.
Keep that tab open while following your browser's steps below.
Copy the full **XX-Token** value, without the key name or surrounding quotes.

### Chrome

1. Open developer tools with **Ctrl+Shift+I** on Windows/Linux or **Cmd+Option+I** on macOS.
2. Select **Application**. If the tab is hidden, use the **>>** tab menu.
3. Expand **Local Storage** and select **https://cloud-universe.anycubic.com**.
4. Select **XX-Token** and copy its value.

See [Chrome's local storage guide](https://developer.chrome.com/docs/devtools/storage/localstorage).

### Microsoft Edge

1. Open developer tools with **F12**, or right-click the page and choose **Inspect**.
2. Select **Application**, then **Local Storage** and the Anycubic Cloud origin.
3. Select **XX-Token** and copy its value.

See [Edge's local storage guide](https://learn.microsoft.com/en-us/microsoft-edge/devtools/storage/localstorage).

### Firefox

1. Open developer tools with **F12**, or **Cmd+Option+I** on macOS.
2. Select **Storage**, then **Local Storage** and the Anycubic Cloud origin.
3. Select **XX-Token** and copy its value.

See [Firefox's Storage Inspector guide](https://firefox-source-docs.mozilla.org/devtools-user/storage_inspector/index.html).

### Safari on macOS

1. Open **Safari → Settings → Advanced** and enable **Show features for web developers**.
2. Return to the Anycubic tab and open **Develop → Show Web Inspector**, or press **Cmd+Option+I**.
3. Select **Storage**, then the Anycubic origin under **Local Storage**.
4. Select **XX-Token** and copy its value.

See [WebKit's inspector setup](https://webkit.org/web-inspector/enabling-web-inspector/) and [Apple's Web Inspector guide](https://developer.apple.com/documentation/safari-developer-tools/web-inspector).

### Brave

Open developer tools by right-clicking the page and choosing **Inspect**.
Then follow the Chrome steps under **Application → Local Storage**.

### Opera and Opera GX

Open **Menu → Developer → Developer tools** on Windows/Linux, or **View → Show Developer Menu** on macOS.
On macOS, open **Developer → Developer tools** after enabling that menu.
Then follow the Chrome steps under **Application → Local Storage**.

See [Opera's developer tools instructions](https://help.opera.com/en/faq/).

### Vivaldi

Open **Vivaldi menu → Tools → Developer Tools**, or right-click the page and choose **Inspect**.
Then follow the Chrome steps under **Application → Local Storage**.

See [Vivaldi's developer tools guide](https://help.vivaldi.com/desktop/tools/developer-tools/).

### Other browsers

Look for **Inspect** or **Developer Tools**, then a panel named **Application** or **Storage**.
Select the Anycubic origin under **Local Storage** and look for **XX-Token**.
If your browser has no storage inspector, open your account in one of the desktop browsers above.

## What if XX-Token is not listed?

Check that you are logged in and inspecting the Anycubic tab, with the correct origin selected.
Reload that tab and reopen the storage view.

You can also check the token sent by the website:

1. Open **Network** in developer tools, then reload the Anycubic file page.
2. Select an authenticated Anycubic API request. In Chrome-based browsers, **Fetch/XHR** narrows the list.
3. Open **Headers** and find **XX-Token** under **Request Headers**.
4. Copy the full header value into the uploader's Settings.

See [Chrome's request-header instructions](https://developer.chrome.com/docs/devtools/network/reference/#headers).

Treat the token like your password. Keep it out of screenshots, issues and chat messages.

## Why do uploads fail after I saved a token?

Choose **Open log** in the tray menu. For authentication errors, log in to Anycubic again and replace the token in Settings.
The next attempt uses the replacement. **Upload pending files** retries waiting files immediately.

## Where do I change watched folders?

Open **Settings**, add or remove folders, and click **Save**.
The app watches files directly inside those folders. It does not scan subfolders.
File extensions are comma separated, such as `.pm4u, .gcode`, and matching ignores case.

## Why does my system ask about the publisher?

The releases do not have a Windows publisher signature or an Apple Developer ID signature and notarization.
Windows may show a SmartScreen prompt. Check that the download came from this repository's [Releases](https://github.com/nzrbits/anycubic-uploader/releases).
On macOS, if the package or app is blocked, open **System Settings → Privacy & Security** and use **Open Anyway** for that download. See [Apple's instructions](https://support.apple.com/en-us/102445).
The installers do not change your system's security settings.
