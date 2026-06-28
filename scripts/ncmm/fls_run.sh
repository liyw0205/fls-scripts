#!/bin/sh
# 通用入口：cd 到 ncmm 目录，可选导入 Cookie，再执行 ncmm 子命令
# 环境变量：NCMM_CMD（默认 task）、NCMM_ARGS（可选额外参数）
set -e
ROOT="${NCMM_ROOT:-ncmm}"
cd "$ROOT" || exit 1

export NCMM_HOME="${NCMM_HOME:-$(pwd)}"
export NCMM_BIN="${NCMM_BIN:-./ncmm}"
export NCMM_CONFIG="${NCMM_CONFIG:-config.yaml}"

FLS_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$FLS_DIR/fls_login_cookie.sh" ]; then
  NCMM_HOME="$NCMM_HOME" NCMM_BIN="$NCMM_BIN" NCMM_CONFIG="$NCMM_CONFIG" sh "$FLS_DIR/fls_login_cookie.sh"
fi

cmd="${NCMM_CMD:-task}"
if [ -n "${NCMM_ARGS:-}" ]; then
  # shellcheck disable=SC2086
  exec "$NCMM_BIN" -c "$NCMM_CONFIG" --home "$NCMM_HOME" $cmd $NCMM_ARGS
fi
exec "$NCMM_BIN" -c "$NCMM_CONFIG" --home "$NCMM_HOME" "$cmd"