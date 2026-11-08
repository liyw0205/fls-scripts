# 77625 路由站每日签到

使用账号密码登录 `https://ly.77625.xyz`，查询当天签到状态后领取积分。已签到时直接返回成功，不重复提交。

## 配置

在 FLS 任务的环境变量中填写：

| 环境变量 | 必填 | 说明 |
| --- | --- | --- |
| `LY77625_USERNAME` | 是 | 登录账号 |
| `LY77625_PASSWORD` | 是 | 登录密码 |
| `LY77625_URL` | 否 | 站点地址，默认 `https://ly.77625.xyz` |

脚本不读取 `app.txt` 或其他凭据文件。登录会话仅在本次运行内使用。

## 运行

依赖：Python 3.10+、`requests`。

```bash
python3 -m pip install requests
export LY77625_USERNAME='你的账号'
export LY77625_PASSWORD='你的密码'
python3 scripts/77625/77625_checkin.py
```

FLS 任务命令和默认定时：

```text
task 77625/77625_checkin.py
40 8 * * *
```

可选参数：

- `--username USER`、`--password PASSWORD`：覆盖环境变量中的账号密码。
- `--url URL`：覆盖站点地址。
- `--timeout SECONDS`：每次请求超时，默认 30 秒。
- `--dry-run`：仅登录并查询签到状态。
- `--json`：输出单行 JSON，状态为 `success`、`already_signed`、`pending` 或 `error`。

签到成功或今天已签到时退出码为 `0`，配置、登录或接口错误时为 `1`。若站点触发 Cloudflare 浏览器验证，脚本会明确报错。
