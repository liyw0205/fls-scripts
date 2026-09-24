# 智画创每日签到

脚本：`wisart_checkin.py`

## 配置

可以在 FLS 任务变量中配置用户名和密码：

```text
WISART_USERNAME=你的用户名
WISART_PASSWORD=你的密码
```

仍可使用 Cookie 登录。在 FLS 任务变量中设置 `WISART_COOKIE`，值为浏览器开发者工具中复制的完整 Cookie，例如：

```text
WISART_COOKIE=wisart_session=...
```

也可以直接调用：

```bash
python3 wisart_checkin.py --cookie 'wisart_session=...'
```

需要使用测试站点或自定义地址时，可设置 `WISART_URL`，也可传入 `--url`。支持 `--dry-run` 查询状态、`--json` 输出单行 JSON；命令行也可通过 `--username` / `--password` 或 `--cookie` 提供认证信息。Cookie 文件方式可选使用 `--cookie-file` 或 `SIGNIN_COOKIE_FILE`，脚本不会自动读取固定凭据文件。

依赖：`requests`。
