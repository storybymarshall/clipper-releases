cask "stupidly-simple-clipper" do
  version "1.0"
  sha256 "3323f1ac9e5ef07af866cb58c20c3db78460e04e5fa1bf06ed0b05d97fa11b7f"

  url "https://github.com/storybymarshall/clipper-releases/releases/download/v#{version}/Clipper.zip"
  name "Clipper"
  desc "Clipboard history manager for the menu bar"
  homepage "https://stupidlysimple.app/"

  livecheck do
    url "https://storybymarshall.github.io/clipper-releases/appcast.xml"
    strategy :sparkle, &:short_version
  end

  auto_updates true
  depends_on arch: :arm64
  depends_on macos: :sonoma

  app "Clipper.app"

  caveats <<~EOS
    Clipper #{version} is ad-hoc signed, with no Developer ID certificate and no stapled notarization ticket.
    Gatekeeper and the download quarantine stay enabled. This cask does not change them.
    macOS may refuse the first launch until a notarized build is published.
  EOS
end
