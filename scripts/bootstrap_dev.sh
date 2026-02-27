#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/4] Creating/updating Python virtualenv..."
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt pytest

echo "[2/4] Verifying Python test tooling..."
.venv/bin/pytest --version

echo "[3/4] Generating iOS Xcode project with xcodegen..."
if ! command -v xcodegen >/dev/null 2>&1; then
  echo "xcodegen is not installed. Install via: brew install xcodegen"
  exit 1
fi
(
  cd ios/JayeshCoachApp
  xcodegen generate
)

echo "[4/4] Toolchain check..."
if xcodebuild -version >/dev/null 2>&1; then
  echo "Xcode is installed and xcodebuild is available."
else
  echo "Full Xcode is not installed yet. Install from App Store:"
  echo "  open 'macappstore://apps.apple.com/app/id497799835'"
  echo "Then run:"
  echo "  sudo xcode-select -s /Applications/Xcode.app/Contents/Developer"
  echo "  sudo xcodebuild -runFirstLaunch"
fi

echo "Bootstrap complete."
