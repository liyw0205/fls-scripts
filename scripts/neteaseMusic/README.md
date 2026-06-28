# 网易云音乐签到刷歌

用于 FLS 面板的网易云音乐自动签到和刷歌脚本。

## 配置变量

推荐使用 Cookie 登录：

```text
NETEASE_COOKIE=MUSIC_U=xxx; __csrf=xxx
```

多账号用 `#` 分隔：

```text
NETEASE_COOKIE=MUSIC_U=xxx; __csrf=xxx#MUSIC_U=yyy; __csrf=yyy
```

也支持手机号密码登录：

```text
NETEASE_USER=13800000000
NETEASE_PWD=password
```

多账号时账号和密码都用 `#` 分隔，数量必须一致。

## 指定刷歌曲目

默认从「每日推荐歌单」凑满约 310 条播放记录。可改为指定歌曲或歌单：

**指定一首或多首歌曲**（歌曲页 URL 里 `id=` 即为歌曲 ID，会循环上报直到达到刷歌条数）：

```text
NETEASE_SONG_IDS=186016,1234567
```

或命令行：

```text
task neteaseMusic/netease_music_checkin.py --song-ids 186016,1234567
```

**指定歌单**（歌单页 URL 里 `id=` 即为歌单 ID）：

```text
NETEASE_PLAYLIST_ID=3778678
```

或：

```text
task neteaseMusic/netease_music_checkin.py --playlist-id 3778678
```

可选调整上报条数（默认 310）：

```text
NETEASE_PLAY_COUNT=310
```

`NETEASE_SONG_IDS` 与 `NETEASE_PLAYLIST_ID` 可同时留空；都未填或 ID 无效、歌单拉取失败时自动用每日推荐。若同时填写有效歌曲 ID，则只用歌曲 ID（忽略歌单）。

## FLS 任务

```text
task neteaseMusic/netease_music_checkin.py
```

建议定时：

```text
30 7,22 * * *
```

## 依赖

```bash
python3 -m pip install requests pycryptodome
```
