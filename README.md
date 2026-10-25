# Clipper

Clipper is a clipboard history for the Mac. Everything you copy is kept in a list you can copy from again, with the app it came from and when. Click the clipboard in the menu bar, or press ⇧⌘V anywhere. Clips are archived after a day and deleted after ten, unless you pin them. Passwords are never recorded, and nothing leaves your Mac. It comes in the same themes as Tracker: Classic, Library, Midnight, Blueprint, Sunday, Neon, Field, Matrix, Sorbet, and Dune.

This repo hosts Clipper's downloads and its update feed. The source code lives elsewhere.

## Download

**[Download Clipper (latest)](https://github.com/storybymarshall/clipper-releases/releases/latest/download/Clipper.zip)**

Clipper needs macOS 14 Sonoma or later on an Apple silicon Mac.

1. Open the downloaded `Clipper.zip`. Your Mac unzips it into `Clipper.app`.
2. Drag `Clipper.app` into your **Applications** folder.
3. Open it. The first launch needs one extra step, explained below. Clipper lives in the menu bar, so it has no Dock icon.

Older versions are on the [Releases](https://github.com/storybymarshall/clipper-releases/releases) page.

## First launch: "Apple could not verify Clipper…"

Clipper isn't signed with an Apple Developer ID yet, so macOS blocks it the first time you open it. You only need to allow it once. After that, it opens normally, and updates install without asking again.

Pick one:

- **System Settings (macOS 15 Sequoia and later):** Open Clipper once and click **Done** on the warning. Then go to **System Settings › Privacy & Security**, scroll down to the message about Clipper, click **Open Anyway**, and confirm with your password.
- **Right-click (macOS 14 Sonoma):** In Applications, right-click (or Control-click) Clipper, choose **Open**, then click **Open** in the dialog.
- **Terminal (any version):** Run this command, then open Clipper as usual:

  ```bash
  xattr -dr com.apple.quarantine /Applications/Clipper.app
  ```

## Updates

Clipper checks for updates by itself. When it finds one, the bottom of its panel says so, and it installs when you click. You can also choose **Check for Updates…** from the palette menu in the panel at any time.

Every update is signed, and Clipper verifies that signature before it installs anything. The feed is at <https://storybymarshall.github.io/clipper-releases/appcast.xml>.
