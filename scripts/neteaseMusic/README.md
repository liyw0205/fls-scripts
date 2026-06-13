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
