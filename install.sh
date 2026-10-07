#!/bin/zsh
# Install photoshop-mirror: puts the `psmirror` command on your PATH.
#
#   From a clone:   ./install.sh
#   One-liner:      curl -fsSL https://raw.githubusercontent.com/Vic-Chen-160/photoshop-mirror/main/install.sh | zsh
#   Uninstall:      ./install.sh --uninstall

set -e

REPO="https://github.com/Vic-Chen-160/photoshop-mirror.git"
DEST="$HOME/.local/share/photoshop-mirror"

# Pick a bin folder that is already on PATH and writable, else ~/.local/bin
BIN=""
for d in /opt/homebrew/bin /usr/local/bin; do
  [[ -d "$d" && -w "$d" && ":$PATH:" == *":$d:"* ]] && { BIN="$d"; break; }
done
[[ -n "$BIN" ]] || BIN="$HOME/.local/bin"

if [[ "$1" == "--uninstall" ]]; then
  for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin"; do
    [[ -L "$d/psmirror" ]] && rm "$d/psmirror" && print "  Removed $d/psmirror"
  done
  [[ -d "$DEST" ]] && rm -rf "$DEST" && print "  Removed $DEST"
  print "  Your settings and local assets in ~/.psmirror were kept. Delete that folder too if you want."
  exit 0
fi

# Run from a clone, or fetch the repo when piped from curl
if [[ -n "$ZSH_SCRIPT" && -f "${ZSH_SCRIPT:A:h}/bin/psmirror" ]]; then
  SRC="${ZSH_SCRIPT:A:h}"
else
  command -v git >/dev/null || { print -u2 "git not found. Run: xcode-select --install"; exit 1; }
  if [[ -d "$DEST/.git" ]]; then
    git -C "$DEST" pull -q --ff-only
  else
    mkdir -p "${DEST:h}"
    git clone -q --depth 1 "$REPO" "$DEST"
  fi
  SRC="$DEST"
fi

command -v python3 >/dev/null || print "  ⚠️  python3 not found. Run: xcode-select --install"

mkdir -p "$BIN"
chmod +x "$SRC/bin/psmirror"
ln -sf "$SRC/bin/psmirror" "$BIN/psmirror"
print "  ✅ Installed: $BIN/psmirror → $SRC/bin/psmirror"

if [[ ":$PATH:" != *":$BIN:"* ]]; then
  print "  Add this line to ~/.zshrc, then open a new Terminal window:"
  print "    export PATH=\"$BIN:\$PATH\""
fi
command -v qrencode >/dev/null || print "  Optional: brew install qrencode   (prints a QR code for your phone)"
print "  Next: psmirror -h"
