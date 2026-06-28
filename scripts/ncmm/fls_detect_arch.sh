#!/bin/sh
# 输出 ncmm release 资产后缀：Linux_arm64 | Linux_armv6 | Linux_x86_64
arch="$(uname -m)"
case "$arch" in
  aarch64|arm64) echo "Linux_arm64" ;;
  armv7l|armv6l|arm) echo "Linux_armv6" ;;
  x86_64|amd64) echo "Linux_x86_64" ;;
  *)
    echo "不支持的架构: $arch（ncmm 仅提供 Linux arm64/armv6/x86_64）" >&2
    exit 1
    ;;
esac