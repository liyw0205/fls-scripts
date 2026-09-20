# Clodesen 每日签到

脚本：`zaiduyu_checkin.py`

## 配置

在 FLS 任务变量中设置：

```text
ZAIDUYU_IDENTIFIER=用户名或邮箱
ZAIDUYU_PASSWORD=登录密码
# 可选：覆盖默认浏览器 User-Agent
ZAIDUYU_USER_AGENT=浏览器 User-Agent
```

也可以直接调用：

```bash
python3 zaiduyu_checkin.py --identifier '用户名或邮箱' --password '登录密码'
```

脚本通过账号密码登录 `pai.zaiduyu.top`，默认使用浏览器 User-Agent，登录后查询当月签到状态，只有未签到时才执行签到。支持 `ZAIDUYU_URL` / `--url` 指定测试地址、`ZAIDUYU_USER_AGENT` 覆盖请求头、`--dry-run` 只查询状态和 `--json` 输出单行 JSON。脚本不会自动读取固定路径或扫描用户目录。

依赖：`requests`。

## 限时兑换码

脚本：`zaiduyu_redemption.py`

在 FLS 任务变量中设置：

```text
ZAIDUYU_IDENTIFIER=用户名或邮箱
ZAIDUYU_PASSWORD=登录密码
ZAIDUYU_REDEMPTION_CODE=限时兑换码
# 可选：ZAIDUYU_URL、ZAIDUYU_USER_AGENT
```

多账号时使用 `ZAIDUYU_ACCOUNTS`，格式为 `账号1,密码1#账号2,密码2#账号3,密码3`。每个账号会独立登录和兑换，某个账号失败不会阻断其他账号；密码中的 `#` 不能作为分隔符。

也可以直接调用：

```bash
python3 zaiduyu_redemption.py \
  --identifier '用户名或邮箱' \
  --password '登录密码' \
  --code '兑换码'
```

多账号调用：

```bash
python3 zaiduyu_redemption.py \
  --accounts '账号1,密码1#账号2,密码2#账号3,密码3' \
  --code '兑换码'
```

脚本先通过 `POST /api/user-auth` 登录，再通过 `GET /api/limited-redemption` 查询兑换额度，最后向同一地址 `POST {"code":"兑换码"}`。支持 `--dry-run` 只查询额度和 `--json` 输出单行 JSON；脚本不会保存或读取固定路径中的凭据。
