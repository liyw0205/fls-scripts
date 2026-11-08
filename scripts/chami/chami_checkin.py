#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""茶蘼绘图公益站每日签到（适用于 FLS）。"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import requests


SITE_NAME = "茶蘼绘图公益站"
DEFAULT_URL = "http://chami.yyqzx.com"
DEFAULT_CREDENTIALS_FILE = "/data/user/0/com.termux/files/home/app.txt"
URL_ENV_NAMES = ("CHAMI_URL", "CHAMI_BASE_URL")
USERNAME_ENV = "CHAMI_USERNAME"
PASSWORD_ENV = "CHAMI_PASSWORD"
CREDENTIALS_FILE_ENV = "CHAMI_CREDENTIALS_FILE"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class CheckinError(RuntimeError):
    """可直接反馈给用户的签到错误。"""


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


def labeled_value(line: str, labels: tuple[str, ...]) -> str:
    pattern = rf"^\s*(?:{'|'.join(map(re.escape, labels))})\s*[:：]?\s*(.*?)\s*$"
    match = re.match(pattern, line, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def find_labeled(lines: list[str], labels: tuple[str, ...]) -> str:
    for line in lines:
        value = labeled_value(line, labels)
        if value:
            return value
    return ""


def read_credentials(path: Path) -> tuple[str, str, str]:
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    except OSError as exc:
        raise CheckinError(f"无法读取凭据文件 {path}：{exc}") from exc

    nonempty = [line for line in lines if line and not line.startswith("#")]
    if not nonempty:
        raise CheckinError(f"凭据文件为空：{path}")

    file_url = next(
        (line for line in nonempty if re.match(r"^https?://", line, flags=re.IGNORECASE)),
        "",
    )
    username = find_labeled(nonempty, ("账号", "用户名", "username", "user", "email"))
    password = find_labeled(nonempty, ("密码", "password", "pass"))

    # 兼容没有中文标签的简单四行格式：URL、Dashboard、账号、密码。
    if not username and len(nonempty) >= 3:
        username = nonempty[2]
    if not password and len(nonempty) >= 4:
        password = nonempty[3]

    if not username:
        raise CheckinError(f"凭据文件中没有找到账号：{path}")
    if not password:
        raise CheckinError(f"凭据文件中没有找到密码：{path}")
    return file_url, username, password


def resolve_auth(args: argparse.Namespace) -> tuple[str, str, str]:
    credentials_file = Path(
        args.credentials_file
        or os.environ.get(CREDENTIALS_FILE_ENV, "")
        or DEFAULT_CREDENTIALS_FILE
    ).expanduser()
    username = str(args.username or "").strip() or first_env(USERNAME_ENV)
    password = str(args.password or "").strip() or first_env(PASSWORD_ENV)
    configured_url = str(args.base_url or "").strip() or first_env(*URL_ENV_NAMES)
    file_url = ""
    if not username or not password or not configured_url:
        file_url, file_username, file_password = read_credentials(credentials_file)
        username = username or file_username
        password = password or file_password
    if not username:
        raise CheckinError(f"未找到登录账号；请检查 {credentials_file} 或设置 {USERNAME_ENV}")
    if not password:
        raise CheckinError(f"未找到登录密码；请检查 {credentials_file} 或设置 {PASSWORD_ENV}")
    return file_url, username, password


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


def request(
    session: requests.Session,
    method: str,
    url: str,
    timeout: float,
    **kwargs: object,
) -> requests.Response:
    try:
        return session.request(method, url, timeout=timeout, **kwargs)
    except requests.RequestException as exc:
        raise CheckinError(f"网络请求失败：{exc}") from exc


def result(status: str, message: str, **fields: object) -> dict:
    payload = {"site": SITE_NAME, "status": status, "message": message}
    payload.update(fields)
    return payload


def login(session: requests.Session, base_url: str, username: str, password: str, timeout: float) -> None:
    response = request(
        session,
        "POST",
        base_url + "/login",
        timeout,
        data={"username_or_email": username, "password": password, "real_ip": ""},
        allow_redirects=True,
    )
    final_path = urlsplit(response.url).path.rstrip("/")
    if final_path == "/login":
        message_match = re.search(r'class="(?:alert|error)[^"]*"[^>]*>(.*?)</', response.text, re.I | re.S)
        detail = re.sub(r"<[^>]+>", " ", message_match.group(1)).strip() if message_match else "账号或密码错误"
        raise CheckinError(f"登录失败：{detail}")
    if final_path != "/dashboard":
        raise CheckinError(f"登录未跳转到 Dashboard（当前地址：{response.url}）")


def dashboard_signed(response: requests.Response) -> bool:
    html = response.text
    badge = re.search(r'id=["\']sign-in-badge["\'][^>]*>(.*?)</span>', html, re.I | re.S)
    button = re.search(r'id=["\']sign-in-btn["\'][^>]*>', html, re.I | re.S)
    badge_text = re.sub(r"<[^>]+>", " ", badge.group(1)).strip() if badge else ""
    return "已签到" in badge_text or bool(button and re.search(r"\sdisabled(?:\s|=|>)", button.group(0), re.I))


def run(args: argparse.Namespace) -> dict:
    file_url, username, password = resolve_auth(args)
    base_url = normalize_base_url(args.base_url or first_env(*URL_ENV_NAMES) or file_url or DEFAULT_URL)

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/json",
            "User-Agent": USER_AGENT,
            "Origin": base_url,
            "Referer": base_url + "/login",
        }
    )
    login(session, base_url, username, password, args.timeout)
    session.headers["Referer"] = base_url + "/dashboard"

    dashboard = request(session, "GET", base_url + "/dashboard", args.timeout)
    if urlsplit(dashboard.url).path.rstrip("/") == "/login":
        raise CheckinError("登录状态未建立，无法访问 Dashboard")
    if not dashboard.ok:
        raise CheckinError(f"Dashboard 请求失败（HTTP {dashboard.status_code}）")
    if args.dry_run:
        return result("already_signed" if dashboard_signed(dashboard) else "pending", "今日已签到" if dashboard_signed(dashboard) else "状态正常，未执行签到")

    payload = response_json(request(session, "POST", base_url + "/sign_in", args.timeout))
    message = str(payload.get("message") or payload.get("detail") or "").strip()
    if "已签到" in message:
        return result("already_signed", message or "今日已签到")
    if str(payload.get("status", "")).lower() in {"success", "ok"}:
        return result("success", message or "签到成功")
    raise CheckinError(message or f"签到失败：{payload}")


def emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(f"{payload['site']}：{payload['message']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="茶蘼绘图公益站每日签到（适用于 FLS）")
    parser.add_argument("--credentials-file", help=f"凭据文件，默认 {DEFAULT_CREDENTIALS_FILE}")
    parser.add_argument("--username", help=f"登录账号；未提供时读取 {USERNAME_ENV} 或凭据文件")
    parser.add_argument("--password", help=f"登录密码；未提供时读取 {PASSWORD_ENV} 或凭据文件")
    parser.add_argument("--url", "--base-url", dest="base_url", help="站点地址，默认从凭据文件第一行读取")
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
