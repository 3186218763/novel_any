#!/bin/bash
# Install libnspr4 and libnss3 without sudo for Playwright Chromium on WSL/Ubuntu
# Saves .so files to ~/miniconda3/lib/ (adjust if using different python env)

set -e

echo "Downloading libnspr4 and libnss3..."
cd /tmp

apt download libnspr4 2>/dev/null
apt download libnss3 2>/dev/null

echo "Extracting..."
dpkg-deb -x libnspr4_*.deb /tmp/nspr_extract
dpkg-deb -x libnss3_*.deb /tmp/nss_extract

echo "Copying to conda lib..."
mkdir -p ~/miniconda3/lib
find /tmp/nspr_extract -name "*.so*" -exec cp {} ~/miniconda3/lib/ \; 2>/dev/null
find /tmp/nss_extract -name "*.so*" -exec cp {} ~/miniconda3/lib/ \; 2>/dev/null

echo "Done. Libraries installed:"
ls ~/miniconda3/lib/libns* ~/miniconda3/lib/libnss* 2>/dev/null

echo ""
echo "Add to your shell or prefix commands with:"
echo "  export LD_LIBRARY_PATH=~/miniconda3/lib:\$LD_LIBRARY_PATH"
