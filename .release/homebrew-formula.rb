class RiffCli < Formula
  desc "Conversation repair and semantic search CLI"
  homepage "https://github.com/NabiaTech/riff-cli"
  url "https://github.com/NabiaTech/riff-cli/releases/download/v2.0.0/riff-macos-latest-3.11.tar.gz"
  sha256 "CALCULATE_AND_INSERT_SHA256_HERE"
  license "MIT"

  depends_on "python@3.11"

  def install
    bin.install "riff"
  end

  test do
    system "#{bin}/riff", "--version"
  end
end
