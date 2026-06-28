#!/bin/sh
# 从环境变量 NETEASE_COOKIE 导入主账号（需含 MUSIC_U=）
# 多账号：用 #MUSIC_U= 衔接各段，与 fls-scripts 网易云 Python 脚本一致
set -e
NCMM_HOME="${NCMM_HOME:-$(pwd)}"
NCMM_BIN="${NCMM_BIN:-./ncmm}"
NCMM_CONFIG="${NCMM_CONFIG:-config.yaml}"

cookie="${NETEASE_COOKIE:-}"
if [ -z "$cookie" ]; then
  echo "未设置 NETEASE_COOKIE，跳过 Cookie 导入（请先在面板填写或手动 ncmm login）"
  exit 0
fi

if [ ! -x "$NCMM_BIN" ]; then
  echo "找不到可执行文件: $NCMM_BIN，请先执行安装任务或 install 步骤" >&2
  exit 1
fi

case "$cookie" in
  *'#MUSIC_U='*)
    idx=0
    printf '%s' "$cookie" | sed 's/#MUSIC_U=/\n#MUSIC_U=/g' | while IFS= read -r seg; do
      [ -z "$seg" ] && continue
      idx=$((idx + 1))
      case "$seg" in
        MUSIC_U=*) ;;
        \#MUSIC_U=*) seg="${seg#\#}" ;;
      esac
      if [ "$idx" -eq 1 ]; then
        echo "导入主账号 Cookie (-m)..."
        "$NCMM_BIN" -c "$NCMM_CONFIG" --home "$NCMM_HOME" login cookie "$seg" -m || true
      else
        fan="fan${idx}.json"
        echo "导入辅助账号 -> $fan ..."
        "$NCMM_BIN" -c "$NCMM_CONFIG" --home "$NCMM_HOME" login cookie "$seg" -o "$fan" || true
      fi
    done
    ;;
  *)
    echo "导入主账号 Cookie (-m)..."
    "$NCMM_BIN" -c "$NCMM_CONFIG" --home "$NCMM_HOME" login cookie "$cookie" -m
    ;;
esac