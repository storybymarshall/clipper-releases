# Stupidly Simple Clipper Homebrew tap

This is a Clipper-only Homebrew tap for [Stupidly Simple](https://stupidlysimple.app/). It installs the public Clipper release. It does not contain Marker, Tracker, or any other app, and it does not contain Clipper's source.

The cask token is `stupidly-simple-clipper`. The installed bundle is still `Clipper.app`.

## Publication status

**Staged.** This directory is not a live Homebrew tap.

`storybymarshall/homebrew-tap` does not exist. On 8 November 2026 the GitHub API returned 404 for that repository. `storybymarshall` is a user account, and the only repository this run's GitHub installation can access is `storybymarshall/clipper-releases`. `GET /user` returns 403, so this installation cannot create a repository on that account. The pull request tool can open a pull request only on `clipper-releases`.

Until the files in this directory are published as the root of a public `storybymarshall/homebrew-tap` repository, this command cannot succeed:

```sh
brew install --cask storybymarshall/tap/stupidly-simple-clipper
```

Homebrew maps that command to `github.com/storybymarshall/homebrew-tap`, with `Casks/stupidly-simple-clipper.rb` at the repository root.

No credentials were requested or extracted. Nothing was submitted to `Homebrew/homebrew-cask`.

### Publish the tap

1. Create a **public** repository named `homebrew-tap` on the `storybymarshall` account.
2. Copy the contents of this directory to that repository's root. `Casks/stupidly-simple-clipper.rb` must sit at `Casks/stupidly-simple-clipper.rb`, not under another `homebrew-tap/` folder. The workflow at `.github/workflows/ci.yml` is the tap's own check.
3. Push the default branch.
4. On a Mac, run the install command above.
5. After that repository is live, this staging copy and `clipper-releases/.github/workflows/staged-homebrew-tap.yml` can be removed.

## Requirements

Apple silicon and macOS Sonoma (14) or later. The shipping zip is a single arm64 slice, and both `LSMinimumSystemVersion` and the Sparkle feed say `14.0`.

## Installation

After the public tap exists:

```sh
brew install --cask storybymarshall/tap/stupidly-simple-clipper
```

Homebrew downloads `Clipper.zip` from the versioned GitHub release, checks the checksum, and moves `Clipper.app` into `/Applications`. Gatekeeper and the download quarantine stay enabled.

## Upgrades

Clipper checks for updates itself. The bundle sets `SUEnableAutomaticChecks` and points Sparkle at:

`https://storybymarshall.github.io/clipper-releases/appcast.xml`

The cask sets `auto_updates true`, so a plain `brew upgrade` skips it. When the tap's cask version changes and you want Homebrew to install that zip:

```sh
brew upgrade --cask --greedy-auto-updates storybymarshall/tap/stupidly-simple-clipper
```

`--greedy` includes the same casks. Sparkle remains the path for updates between cask bumps.

## Uninstallation

```sh
brew uninstall --cask storybymarshall/tap/stupidly-simple-clipper
```

That removes `Clipper.app` and Homebrew's staged copy. Clipboard history stays on the Mac. Clipper's `ClipStore` writes clips to its own folder; this environment did not launch the app, so that absolute path was not observed and is not listed here.

The cask has no `zap` stanza and no file-removal list. `brew uninstall --zap` warns that no zap stanza is present and still has no clipboard paths to remove.

To drop the tap formula list after the app is uninstalled:

```sh
brew untap storybymarshall/tap
```

## Signing and notarization

Clipper 1.0 (build 1) is ad-hoc signed. The main executable has a code signature whose flags include `CS_ADHOC`, and the certificate blob is empty. There is no Developer ID certificate and no stapled notarization ticket.

Gatekeeper and the download quarantine stay enabled. This cask does not change them. macOS may refuse the first launch until a notarized build is published. The same notice is printed by the cask `caveats` stanza during `brew install` and `brew info`.

## Release maintenance

Ship new Clipper builds from `storybymarshall/clipper-releases` only. Keep the asset name `Clipper.zip`.

1. Tag the release `v<version>`, matching `CFBundleShortVersionString`.
2. Update `docs/appcast.xml`: `sparkle:shortVersionString`, `sparkle:version` (`CFBundleVersion`), `sparkle:minimumSystemVersion`, and the enclosure `url`, `length`, and `edSignature`.
3. Set the cask `version` to that short version and replace `sha256` with `shasum -a 256 Clipper.zip`.
4. Keep `depends_on arch: :arm64` while the executable is a single arm64 slice.
5. Set `depends_on macos:` from the bundle's minimum major version: `14` is `:sonoma`, `15` is `:sequoia`, `26` is `:tahoe`, and `27` is `:golden_gate`.
6. When a build is Developer ID signed and notarized, replace the `caveats` text and update the ad-hoc expectation in `script/validate_cask.py` in the same change. The script currently requires an ad-hoc signature with an empty certificate blob, and it requires the caveat to say so.
7. From this directory, run `python3 script/validate_cask.py`. On a Mac, also run `brew style --cask Casks/stupidly-simple-clipper.rb` and `brew audit --cask --online Casks/stupidly-simple-clipper.rb`.

The livecheck block reads `sparkle:shortVersionString`, which is the version interpolated into the download URL. The URL is `https://github.com/storybymarshall/clipper-releases/releases/download/v#{version}/Clipper.zip`.

## Validation

`script/validate_cask.py` downloads the live zip and appcast and checks:

- cask version, checksum, versioned URL, Sparkle livecheck, `auto_updates`, architecture, minimum macOS, and `Clipper.app`
- zip integrity and that the archive root is `Clipper.app`
- bundle version, build, minimum OS, bundle id, and Sparkle feed against the appcast
- arm64 Mach-O, ad-hoc signature, empty certificate blob, and the signing caveat
- Sparkle's ed25519 enclosure signature against `SUPublicEDKey`
- Ruby syntax of the cask
- the tap text does not include a quarantine bypass or a cask stanza that removes files

The script does not install or launch Clipper. A passing run is not a Mac install test.

On 8 November 2026, from Homebrew's `main` branch:

- `brew style --cask storybymarshall/tap/stupidly-simple-clipper` reported no offenses.
- `brew livecheck --cask` reported `1.0 ==> 1.0`.
- `brew info --cask` showed arm64, macOS >= 14, `Clipper.app`, and the signing caveat.
- `brew audit --cask --online --strict` reported no cask problems after a local `plutil` stand-in. Linux has no `plutil`, so the first audit stopped while reading `Info.plist`. That stand-in only printed the XML plist. It did not change Gatekeeper, quarantine, or the zip.

Homebrew also refuses to load this tap until `brew trust storybymarshall/tap` is run locally. That trust entry lives in the Homebrew config on that machine. It is not part of this cask.

In this staging repository, `.github/workflows/staged-homebrew-tap.yml` runs that script when the tap directory changes. After publication, `.github/workflows/ci.yml` in the tap repository runs the same script.

## Verified release

Checked on 8 November 2026 against the live files:

| Item | Value |
| --- | --- |
| Release | https://github.com/storybymarshall/clipper-releases/releases/tag/v1.0 |
| Download | https://github.com/storybymarshall/clipper-releases/releases/download/v1.0/Clipper.zip |
| SHA-256 | `3323f1ac9e5ef07af866cb58c20c3db78460e04e5fa1bf06ed0b05d97fa11b7f` |
| Size | 1913000 bytes |
| Appcast | https://storybymarshall.github.io/clipper-releases/appcast.xml |
| Homepage | https://stupidlysimple.app/ |
| Bundle | Clipper 1.0 (build 1), `com.seese.clipper` |
| CPU / OS | arm64, macOS 14.0 |
| Updates | Sparkle automatic checks, feed matches the appcast |
