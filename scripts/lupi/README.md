# 噜皮生图每日签到

脚本：`lupi_checkin.py`

## 配置

在 FLS 任务变量中设置 `LUPI_COOKIE`，值为浏览器开发者工具中复制的完整 Cookie，例如：

```text
LUPI_COOKIE=chatgpt2api_session=...
```

也可以直接调用：

```bash
python3 lupi_checkin.py --cookie 'chatgpt2api_session=...'
```

需要使用测试站点或自定义地址时，可设置 `LUPI_URL`，也可传入 `--url`。支持 `--dry-run` 查询状态、`--json` 输出单行 JSON；也可以用 `--cookie-file` 或 `SIGNIN_COOKIE_FILE` 指定凭据文件。脚本不会自动读取固定路径或扫描用户目录。

依赖：`requests`。
