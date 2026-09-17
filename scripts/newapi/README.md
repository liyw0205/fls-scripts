# NewAPI 签到

用于 FLS 面板的 NewAPI / 魔改站每日签到。支持多账号 Token 或 Cookie。

## 配置变量

Token 多账号（推荐）：

```text
tokens=123#access_token#https://example.com,456#access_token#https://other.example
```

Cookie 多账号：

```text
cookie=123#session=xxxx#https://example.com
```

也可拆开写 `user_id` / `token` / `url`，逗号分隔，数量为 1 或与账号数一致。

## Cloudflare / 地域限制

请求默认走 IPv4（`curl_ip=4`）。`api.futureppo.top` 走 IPv6 时常返回 Cloudflare「Just a moment...」挑战页，IPv4 才能打到签到接口。

香港/机房 IP 仍可能被 Cloudflare 拦。可给任务配国内代理：

```text
HTTP_PROXY=http://127.0.0.1:7890
```

或只给指定站点走代理（不要把账号密码写进仓库）：

```text
host_proxies=futureppo.top=http://127.0.0.1:7890
```

`curl_ip=auto` 不强制 IPv4。

可选 `skip_hosts`：逗号分隔主机名，匹配到的账号不请求、不算失败。

## 说明

- 签到接口：`POST /api/user/checkin`
- 用户信息：`GET /api/user/self`
- curl 跟随重定向（`-L`）
- 非 JSON 响应会打印前 200 字符，便于区分 Cloudflare 挑战页和地域拒绝页
