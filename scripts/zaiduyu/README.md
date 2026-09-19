# Clodesen 每日签到

脚本：`zaiduyu_checkin.py`

## 配置

在 FLS 任务变量中设置：

```text
ZAIDUYU_IDENTIFIER=用户名或邮箱
ZAIDUYU_PASSWORD=登录密码
```

也可以直接调用：

```bash
python3 zaiduyu_checkin.py --identifier '用户名或邮箱' --password '登录密码'
```

脚本通过账号密码登录 `pai.zaiduyu.top`，登录后查询当月签到状态，只有未签到时才执行签到。支持 `ZAIDUYU_URL` / `--url` 指定测试地址、`--dry-run` 只查询状态和 `--json` 输出单行 JSON。脚本不会自动读取固定路径或扫描用户目录。

依赖：`requests`。
