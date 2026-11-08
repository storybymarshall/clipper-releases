#!/usr/bin/env python3
"""Check the Clipper cask against the live GitHub release and Sparkle feed.

The script downloads the versioned zip, hashes it, reads the app bundle, and
checks the signing disclosure. It does not install or launch the app.
"""

from __future__ import annotations

import hashlib
import plistlib
import re
import struct
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

TAP_ROOT = Path(__file__).resolve().parent.parent
CASK_PATH = TAP_ROOT / "Casks" / "stupidly-simple-clipper.rb"
README_PATH = TAP_ROOT / "README.md"
APPCAST_URL = "https://storybymarshall.github.io/clipper-releases/appcast.xml"
SPARKLE_NS = "http://www.andymatuschak.org/xml-namespaces/sparkle"
EXPECTED_URL = (
    "https://github.com/storybymarshall/clipper-releases/releases/download/"
    "v#{version}/Clipper.zip"
)
USER_AGENT = "stupidly-simple-clipper-cask-validator"
ARM64 = 0x0100000C
MACOS_SYMBOLS = {
    "14": "sonoma",
    "15": "sequoia",
    "26": "tahoe",
    "27": "golden_gate",
}
LC_CODE_SIGNATURE = 0x1D
CS_ADHOC = 0x2
CSMAGIC_EMBEDDED_SIGNATURE = 0xFADE0CC0
CSMAGIC_CODEDIRECTORY = 0xFADE0C02

# Commands and stanza keys that disable Gatekeeper or quarantine.
BYPASS_PATTERNS = (
    "xattr",
    "spctl",
    "csrutil",
    "master-disable",
    "quarantine: false",
    "com.apple.quarantine",
    "HOMEBREW_NO_QUARANTINE",
)
# Homebrew keys that remove files. Clipboard history must survive uninstall.
REMOVAL_PATTERNS = ("trash:", "delete:", "uninstall ", "uninstall\n", "zap ")

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if condition:
        print(f"PASS {message}")
    else:
        failures.append(message)
        print(f"FAIL {message}")


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def cask_field(text: str, stanza: str) -> str:
    match = re.search(rf'(?m)^  {stanza} "([^"]+)"\s*$', text)
    if match is None:
        raise ValueError(f"missing {stanza} stanza")
    return match.group(1)


def parse_macho(binary: bytes) -> dict[str, object]:
    magic = struct.unpack_from("<I", binary, 0)[0]
    if magic in (0xCAFEBABE, 0xBEBAFECA):
        raise ValueError("universal binary; expected a single arm64 slice")
    if magic != 0xFEEDFACF:
        raise ValueError(f"unexpected Mach-O magic {magic:#x}")

    cputype, _cpusubtype, _filetype, ncmds, _sizeofcmds, _flags, _reserved = (
        struct.unpack_from("<IIIIIII", binary, 4)
    )
    offset = 32
    signature = None
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", binary, offset)
        if cmd == LC_CODE_SIGNATURE:
            dataoff, datasize = struct.unpack_from("<II", binary, offset + 8)
            signature = binary[dataoff : dataoff + datasize]
        offset += cmdsize
    if signature is None:
        raise ValueError("missing LC_CODE_SIGNATURE")

    blob_magic, _length, count = struct.unpack_from(">III", signature, 0)
    if blob_magic != CSMAGIC_EMBEDDED_SIGNATURE:
        raise ValueError(f"unexpected signature magic {blob_magic:#x}")

    flags = None
    ident = None
    cms_length = None
    for index in range(count):
        slot_type, slot_offset = struct.unpack_from(">II", signature, 12 + 8 * index)
        slot_magic, slot_length = struct.unpack_from(">II", signature, slot_offset)
        if slot_magic == CSMAGIC_CODEDIRECTORY:
            flags = struct.unpack_from(">I", signature, slot_offset + 12)[0]
            ident_offset = struct.unpack_from(">I", signature, slot_offset + 20)[0]
            ident = signature[slot_offset + ident_offset :].split(b"\x00", 1)[0].decode()
        if slot_type == 0x10000:
            cms_length = slot_length - 8

    if flags is None or ident is None or cms_length is None:
        raise ValueError("incomplete code signature")
    return {
        "cputype": cputype,
        "adhoc": bool(flags & CS_ADHOC),
        "flags": flags,
        "ident": ident,
        "cms_length": cms_length,
    }


def verify_sparkle_signature(archive: bytes, appcast: bytes, public_key: str) -> None:
    import xml.etree.ElementTree as ET

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    root = ET.fromstring(appcast)
    enclosure = root.find("channel/item/enclosure")
    if enclosure is None:
        raise ValueError("appcast enclosure missing")
    signature = enclosure.attrib[f"{{{SPARKLE_NS}}}edSignature"]
    key = Ed25519PublicKey.from_public_bytes(base64_decode(public_key))
    key.verify(base64_decode(signature), archive)


def base64_decode(value: str) -> bytes:
    import base64

    return base64.b64decode(value)


def main() -> int:
    cask_text = CASK_PATH.read_text()
    readme_text = README_PATH.read_text()
    published_text = "\n".join(
        path.read_text()
        for path in [
            CASK_PATH,
            README_PATH,
            *sorted((TAP_ROOT / ".github").rglob("*.yml")),
        ]
    )

    version = cask_field(cask_text, "version")
    sha256 = cask_field(cask_text, "sha256")
    url_template = cask_field(cask_text, "url")
    check(url_template == EXPECTED_URL, "cask url is the versioned GitHub release asset")
    download_url = url_template.replace("#{version}", version)

    check(
        'strategy :sparkle, &:short_version' in cask_text
        and f'url "{APPCAST_URL}"' in cask_text,
        "livecheck uses the Sparkle appcast short version",
    )
    check("auto_updates true" in cask_text, "auto_updates is enabled")
    check("depends_on arch: :arm64" in cask_text, "cask requires arm64")
    check('app "Clipper.app"' in cask_text, "cask installs Clipper.app")
    check('name "Clipper"' in cask_text, "cask name is Clipper")
    check("zap" not in cask_text, "cask has no zap stanza")
    for pattern in REMOVAL_PATTERNS:
        check(pattern not in cask_text, f"cask omits removal stanza {pattern!r}")

    for pattern in BYPASS_PATTERNS:
        check(pattern not in published_text, f"published tap text omits {pattern!r}")

    disclosure = (
        "ad-hoc" in cask_text
        and "Developer ID" in cask_text
        and "notarization" in cask_text
        and "Gatekeeper" in cask_text
        and "quarantine" in cask_text
    )
    check(disclosure, "cask caveats disclose the ad-hoc signature, Gatekeeper, and quarantine")
    check("quarantine" in readme_text and "ad-hoc" in readme_text, "README discloses signing status")
    check("clipboard" in readme_text, "README states what happens to clipboard history")

    print(f"Downloading {download_url}")
    archive = fetch(download_url)
    digest = hashlib.sha256(archive).hexdigest()
    check(digest == sha256, f"downloaded sha256 matches cask ({digest})")

    appcast = fetch(APPCAST_URL)
    import xml.etree.ElementTree as ET

    root = ET.fromstring(appcast)
    item = root.find("channel/item")
    if item is None:
        check(False, "appcast has an item")
        return 1
    short_version = item.find(f"{{{SPARKLE_NS}}}shortVersionString")
    build_version = item.find(f"{{{SPARKLE_NS}}}version")
    minimum = item.find(f"{{{SPARKLE_NS}}}minimumSystemVersion")
    enclosure = item.find("enclosure")
    check(short_version is not None and short_version.text == version, "appcast short version matches cask")
    check(build_version is not None and bool(build_version.text), "appcast build number is present")
    check(minimum is not None and bool(minimum.text), "appcast minimum macOS is present")
    if enclosure is None:
        check(False, "appcast enclosure exists")
        return 1
    check(enclosure.attrib.get("url") == download_url, "appcast enclosure url matches the cask download")
    check(int(enclosure.attrib.get("length", "0")) == len(archive), "appcast enclosure length matches the zip")

    with tempfile.TemporaryDirectory() as temporary:
        archive_path = Path(temporary) / "Clipper.zip"
        archive_path.write_bytes(archive)
        with zipfile.ZipFile(archive_path) as bundle:
            bad_entry = bundle.testzip()
            check(bad_entry is None, "zip archive test")
            names = bundle.namelist()
            check("Clipper.app/Contents/Info.plist" in names, "zip contains Clipper.app")
            check(
                all(name == "Clipper.app" or name.startswith("Clipper.app/") for name in names),
                "zip root is Clipper.app",
            )
            info = plistlib.loads(bundle.read("Clipper.app/Contents/Info.plist"))
            binary = bundle.read("Clipper.app/Contents/MacOS/Clipper")

    check(info.get("CFBundleShortVersionString") == version, "bundle short version matches cask")
    check(
        build_version is not None and info.get("CFBundleVersion") == build_version.text,
        "bundle build number matches the appcast",
    )
    bundle_minimum = str(info.get("LSMinimumSystemVersion", ""))
    appcast_minimum = "" if minimum is None or minimum.text is None else minimum.text
    check(bundle_minimum == appcast_minimum, "bundle minimum macOS matches the appcast")
    major = bundle_minimum.split(".", 1)[0]
    symbol = MACOS_SYMBOLS.get(major)
    check(
        symbol is not None and f"depends_on macos: :{symbol}" in cask_text,
        f"cask minimum macOS is :{symbol} for {bundle_minimum or 'unknown'}",
    )
    check(info.get("CFBundleIdentifier") == "com.seese.clipper", "bundle id is com.seese.clipper")
    check(info.get("CFBundleName") == "Clipper", "bundle name is Clipper")
    check(info.get("SUEnableAutomaticChecks") is True, "Sparkle automatic checks are enabled")
    check(info.get("SUFeedURL") == APPCAST_URL, "Sparkle feed matches livecheck url")
    public_key = info.get("SUPublicEDKey")
    check(isinstance(public_key, str) and len(public_key) > 0, "Sparkle public key is present")

    signature = parse_macho(binary)
    check(signature["cputype"] == ARM64, "main executable is arm64")
    check(signature["ident"] == "com.seese.clipper", "code directory identifier is com.seese.clipper")
    check(signature["adhoc"] is True, "code signature is ad-hoc")
    check(signature["cms_length"] == 0, "code signature has no certificate blob")

    if isinstance(public_key, str):
        try:
            verify_sparkle_signature(archive, appcast, public_key)
            check(True, "Sparkle ed25519 signature matches the zip")
        except Exception as error:  # noqa: BLE001 - report the verifier result as a check
            check(False, f"Sparkle ed25519 signature matches the zip ({error})")

    ruby = subprocess.run(
        ["ruby", "-c", str(CASK_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    check(ruby.returncode == 0, f"ruby -c syntax ({ruby.stderr.strip() or ruby.stdout.strip()})")

    if failures:
        print(f"\n{len(failures)} check(s) failed:", file=sys.stderr)
        for message in failures:
            print(f"- {message}", file=sys.stderr)
        return 1
    print("\nAll Clipper cask checks passed.")
    print("macOS install and launch were not run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
