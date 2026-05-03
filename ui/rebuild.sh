#!/bin/bash
set -e

APPIMAGE="$(dirname "$0")/release/Accel-0.0.0.AppImage"

echo "==> Stopping running Accel..."
pkill -f '/tmp/.mount_Accel-.*/ui' 2>/dev/null
pkill -f 'Accel-0.0.0.AppImage' 2>/dev/null
sleep 1

echo "==> Building..."
cd "$(dirname "$0")"
npm run build:electron

echo "==> Launching Accel..."
ELECTRON_DISABLE_SANDBOX=1 "$APPIMAGE" --no-sandbox &
disown

echo "==> Done"
