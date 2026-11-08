# 茶蘼绘图公益站每日签到

脚本使用账号密码登录 `http://chami.yyqzx.com`，然后调用站点签到接口。

默认从 `/data/user/0/com.termux/files/home/app.txt` 读取凭据。当前格式示例：

```text
http://chami.yyqzx.com/login
http://chami.yyqzx.com/dashboard
账号 你的账号
密码 你的密码
```

运行：

```bash
python3 scripts/chami/chami_checkin.py
```

可选参数：

- `--credentials-file PATH`：指定凭据文件；也可设置 `CHAMI_CREDENTIALS_FILE`。
- `--url URL`：覆盖凭据文件第一行的站点地址；也可设置 `CHAMI_URL`。
- `--username USER`、`--password PASSWORD`：覆盖凭据文件中的账号密码。
- `--dry-run`：只查询 Dashboard 状态，不执行签到。
- `--json`：输出单行 JSON，便于 FLS 任务处理。

依赖：`requests`。
