#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WisArt (智画创) daily check-in for FLS."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import requests


SITE_NAME = "智画创"
DEFAULT_URL = "https://wisart.kuaileshifu.com"
COOKIE_ENV = "WISART_COOKIE"
USERNAME_ENV = "WISART_USERNAME"
PASSWORD_ENV = "WISART_PASSWORD"
USERNAME_ENV_NAMES = (USERNAME_ENV,)
PASSWORD_ENV_NAMES = (PASSWORD_ENV,)
URL_ENV_NAMES = ("WISART_URL", "WISART_BASE_URL")
COOKIE_HOST = "wisart.kuaileshifu.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class CheckinError(RuntimeError):
    """An expected, user-actionable check-in failure."""


def first_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def normalize_base_url(value: str) -> str:
    raw = (value or DEFAULT_URL).strip().rstrip("/")
    parsed = urlsplit(raw)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise CheckinError("URL 必须是完整的 http(s) 地址")
    return f"{parsed.scheme}://{parsed.netloc}"


def normalize_cookie(value: str) -> str:
    cookie = (value or "").strip()
    if cookie.lower().startswith("cookie:"):
        cookie = cookie.split(":", 1)[1].strip()
    if "=" not in cookie or not cookie.split("=", 1)[0].strip():
        raise CheckinError("Cookie 格式不正确，应为 name=value")
    return cookie


def cookie_from_file(path: Path, host: str) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CheckinError(f"无法读取凭据文件 {path}: {exc}") from exc

    host = host.lower()
    for index, line in enumerate(lines):
        if host not in line.lower():
            continue
        for candidate in lines[index + 1 : index + 9]:
            candidate = candidate.strip()
            if not candidate or candidate.lower() in {"cookie", "cookies"}:
                continue
            if candidate.lower().startswith("cookie:"):
                candidate = candidate.split(":", 1)[1].strip()
            if "=" in candidate:
                return normalize_cookie(candidate)
        break
    raise CheckinError(f"凭据文件中没有找到 {host} 的 Cookie")


def resolve_credentials(args: argparse.Namespace) -> tuple[str, str]:
    username = str(args.username or "").strip() or first_env(*USERNAME_ENV_NAMES)
    password = str(args.password or "").strip() or first_env(*PASSWORD_ENV_NAMES)

    if not username:
        raise CheckinError(f"未找到用户名。请传入 --username 或设置 {USERNAME_ENV}")
    if not password:
        raise CheckinError(f"未找到密码。请传入 --password 或设置 {PASSWORD_ENV}")
    return username, password


def resolve_cookie_file(cookie_file: str | None) -> str:
    env_file = os.environ.get("SIGNIN_COOKIE_FILE", "").strip()
    explicit_file = cookie_file or env_file
    if explicit_file:
        path = Path(explicit_file).expanduser()
        if not path.is_file():
            raise CheckinError(f"凭据文件不存在：{path}")
        return cookie_from_file(path.resolve(), COOKIE_HOST)

    raise CheckinError("未找到 Cookie 文件")


def resolve_auth(args: argparse.Namespace) -> tuple[str, str, str]:
    explicit_cookie = str(args.cookie or "").strip()
    explicit_username = str(args.username or "").strip()
    explicit_password = str(args.password or "").strip()
    if explicit_cookie:
        return "cookie", normalize_cookie(explicit_cookie), ""
    if explicit_username or explicit_password:
        username, password = resolve_credentials(args)
        return "password", username, password

    env_cookie = os.environ.get(COOKIE_ENV, "").strip()
    if env_cookie:
        return "cookie", normalize_cookie(env_cookie), ""

    if first_env(*USERNAME_ENV_NAMES) or first_env(*PASSWORD_ENV_NAMES):
        username, password = resolve_credentials(args)
        return "password", username, password

    if args.cookie_file or os.environ.get("SIGNIN_COOKIE_FILE", "").strip():
        return "cookie", resolve_cookie_file(args.cookie_file), ""
    raise CheckinError(
        f"未找到认证信息。请设置 {USERNAME_ENV}/{PASSWORD_ENV}，或使用 --cookie / --cookie-file"
    )


def response_json(response: requests.Response) -> dict:
    try:
        payload = response.json()
    except ValueError as exc:
        snippet = response.text.strip().replace("\n", " ")[:200]
        raise CheckinError(
            f"接口返回非 JSON（HTTP {response.status_code}）：{snippet or '空响应'}"
        ) from exc

    if not isinstance(payload, dict):
        raise CheckinError("接口返回格式不正确")
    if not response.ok:
        detail = payload.get("message") or payload.get("error") or payload.get("detail")
        raise CheckinError(f"接口请求失败（HTTP {response.status_code}）：{detail or payload}")
    return payload


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    timeout: float,
    **kwargs: object,
) -> dict:
    try:
        response = session.request(method, url, timeout=timeout, **kwargs)
    except requests.RequestException as exc:
        raise CheckinError(f"网络请求失败：{exc}") from exc
    return response_json(response)


def result(status: str, message: str, **fields: object) -> dict:
    payload = {"site": SITE_NAME, "status": status, "message": message}
    payload.update(fields)
    return payload


def run(args: argparse.Namespace) -> dict:
    base_url = normalize_base_url(args.base_url or first_env(*URL_ENV_NAMES) or DEFAULT_URL)
    auth_type, auth_value, auth_secret = resolve_auth(args)

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Origin": base_url,
            "Referer": base_url + "/",
        }
    )

    if auth_type == "cookie":
        session.headers["Cookie"] = auth_value
    else:
        request_json(
            session,
            "POST",
            base_url + "/api/auth/login",
            args.timeout,
            json={"username": auth_value, "password": auth_secret},
        )

    state = request_json(
        session,
        "GET",
        base_url + "/api/points/checkin",
        args.timeout,
    )
    daily = state.get("daily_checkin")
    if not isinstance(daily, dict):
        raise CheckinError("接口没有返回每日签到状态")

    points = state.get("points")
    if daily.get("signed_today") is True:
        return result("already_signed", "今日已签到", points=points)
    if daily.get("enabled") is False:
        raise CheckinError("站点当前未开启每日签到")
    if daily.get("eligible") is False:
        raise CheckinError("当前账号暂不满足签到条件")
    if args.dry_run:
        return result("pending", "状态正常，未执行签到", points=points)

    payload = request_json(
        session,
        "POST",
        base_url + "/api/points/checkin",
        args.timeout,
    )
    if payload.get("ok") is False:
        detail = payload.get("message") or payload.get("error") or payload
        raise CheckinError(f"签到失败：{detail}")

    post_daily = payload.get("daily_checkin")
    if isinstance(post_daily, dict) and post_daily.get("signed_today") is False:
        raise CheckinError("接口未确认签到成功")
    added = payload.get("added", 0)
    balance = payload.get("balance", points)
    return result("success", f"签到成功，获得 {added} 积分", added=added, points=balance)


def emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return
    print(f"{payload['site']}：{payload['message']}")
    details = []
    if "added" in payload:
        details.append(f"本次 +{payload['added']}")
    if payload.get("points") is not None:
        details.append(f"当前积分 {payload['points']}")
    if details:
        print("，".join(details))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="智画创每日签到（适用于 FLS）")
    parser.add_argument("--cookie", help=f"Cookie；未提供时读取 {COOKIE_ENV}")
    parser.add_argument("--cookie-file", help="包含站点 Cookie 的凭据文件")
    parser.add_argument("--username", help=f"登录用户名；未提供时读取 {USERNAME_ENV}")
    parser.add_argument("--password", help=f"登录密码；未提供时读取 {PASSWORD_ENV}")
    parser.add_argument("--url", "--base-url", dest="base_url", help="站点地址")
    parser.add_argument("--timeout", type=float, default=30.0, help="请求超时秒数，默认 30")
    parser.add_argument("--dry-run", action="store_true", help="只查询状态，不执行签到")
    parser.add_argument("--json", action="store_true", help="以单行 JSON 输出结果")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")
    return args


def main() -> int:
    args = parse_args()
    try:
        payload = run(args)
    except CheckinError as exc:
        payload = result("error", str(exc))
        emit(payload, args.json)
        return 1
    except KeyboardInterrupt:
        payload = result("error", "已取消")
        emit(payload, args.json)
        return 130

    emit(payload, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
