#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clodesen (pai.zaiduyu.top) daily check-in for FLS."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from urllib.parse import urlsplit

import requests


SITE_NAME = "Clodesen"
DEFAULT_URL = "https://pai.zaiduyu.top"
URL_ENV_NAMES = ("ZAIDUYU_URL", "ZAIDUYU_BASE_URL", "PAI_URL")
IDENTIFIER_ENV_NAMES = (
    "ZAIDUYU_IDENTIFIER",
    "ZAIDUYU_USERNAME",
    "PAI_IDENTIFIER",
    "PAI_USERNAME",
)
PASSWORD_ENV_NAMES = ("ZAIDUYU_PASSWORD", "PAI_PASSWORD")
USER_AGENT = "fls-checkin/1.0 (+https://github.com/liyw0205/fls)"


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
        detail = payload.get("error") or payload.get("message") or payload.get("detail")
        raise CheckinError(
            f"接口请求失败（HTTP {response.status_code}）：{detail or payload}"
        )

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


def resolve_credentials(args: argparse.Namespace) -> tuple[str, str]:
    identifier = str(args.identifier or "").strip() or first_env(*IDENTIFIER_ENV_NAMES)
    password = str(args.password or "").strip() or first_env(*PASSWORD_ENV_NAMES)

    if not identifier:
        raise CheckinError(
            "未找到账号。请传入 --identifier，或设置 ZAIDUYU_IDENTIFIER"
        )

    if not password:
        raise CheckinError(
            "未找到密码。请传入 --password，或设置 ZAIDUYU_PASSWORD"
        )

    return identifier, password


def run(args: argparse.Namespace) -> dict:
    base_url = normalize_base_url(
        args.base_url or first_env(*URL_ENV_NAMES) or DEFAULT_URL
    )
    identifier, password = resolve_credentials(args)

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Origin": base_url,
            "Referer": base_url + "/#/checkin",
        }
    )

    login_payload = request_json(
        session,
        "POST",
        base_url + "/api/user-auth",
        args.timeout,
        json={
            "action": "login",
            "identifier": identifier,
            "password": password,
        },
    )

    if not isinstance(login_payload.get("user"), dict):
        raise CheckinError("登录响应未确认账号有效")

    month = datetime.now().strftime("%Y-%m")
    state = request_json(
        session,
        "GET",
        f"{base_url}/api/checkin?month={month}",
        args.timeout,
    )

    if "checkedIn" not in state:
        raise CheckinError("签到状态响应缺少 checkedIn 字段")

    points = state.get("balance")
    if state.get("checkedIn") is True:
        return result(
            "already_signed",
            "今日已签到",
            points=points,
            reward=state.get("reward"),
        )

    if state.get("enabled") is False:
        raise CheckinError("站点当前未开启每日签到")

    if args.dry_run:
        return result("pending", "状态正常，未执行签到", points=points)

    payload = request_json(
        session,
        "POST",
        base_url + "/api/checkin",
        args.timeout,
    )

    if (
        payload.get("error")
        or payload.get("ok") is False
        or payload.get("success") is False
        or payload.get("checkedIn") is False
    ):
        detail = payload.get("error") or payload.get("message") or payload
        raise CheckinError(f"签到失败：{detail}")

    reward = payload.get("reward", 0)
    validity_days = payload.get("validityDays", state.get("validityDays", 7))
    balance = payload.get("balance", points)
    return result(
        "success",
        f"签到成功，获得 {reward} 积分（有效 {validity_days} 天）",
        reward=reward,
        points=balance,
        validity_days=validity_days,
    )


def emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return

    print(f"{payload['site']}：{payload['message']}")
    details = []
    if payload.get("points") is not None:
        details.append(f"当前积分 {payload['points']}")
    if details:
        print("，".join(details))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clodesen 每日签到（适用于 FLS）")
    parser.add_argument(
        "--identifier",
        "--username",
        "--account",
        dest="identifier",
        help="登录账号（用户名或邮箱）",
    )
    parser.add_argument("--password", help="登录密码")
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
