#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clodesen (pai.zaiduyu.top) limited redemption for FLS."""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.parse import urlsplit

import requests


SITE_NAME = "Clodesen 限时兑换"
DEFAULT_URL = "https://pai.zaiduyu.top"
URL_ENV_NAMES = ("ZAIDUYU_URL", "ZAIDUYU_BASE_URL", "PAI_URL")
IDENTIFIER_ENV_NAMES = (
    "ZAIDUYU_IDENTIFIER",
    "ZAIDUYU_USERNAME",
    "PAI_IDENTIFIER",
    "PAI_USERNAME",
)
PASSWORD_ENV_NAMES = ("ZAIDUYU_PASSWORD", "PAI_PASSWORD")
CODE_ENV_NAMES = (
    "ZAIDUYU_REDEMPTION_CODE",
    "ZAIDUYU_CODE",
    "PAI_REDEMPTION_CODE",
    "PAI_CODE",
)
USER_AGENT = os.environ.get(
    "ZAIDUYU_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36",
).strip()


class RedemptionError(RuntimeError):
    """An expected, user-actionable redemption failure."""


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
        raise RedemptionError("URL 必须是完整的 http(s) 地址")
    return f"{parsed.scheme}://{parsed.netloc}"


def response_json(response: requests.Response) -> dict:
    try:
        payload = response.json()
    except ValueError as exc:
        snippet = response.text.strip().replace("\n", " ")[:200]
        raise RedemptionError(
            f"接口返回非 JSON（HTTP {response.status_code}）：{snippet or '空响应'}"
        ) from exc

    if not isinstance(payload, dict):
        raise RedemptionError("接口返回格式不正确")
    if not response.ok:
        detail = payload.get("error") or payload.get("message") or payload.get("detail")
        raise RedemptionError(
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
        raise RedemptionError(f"网络请求失败：{exc}") from exc
    return response_json(response)


def result(status: str, message: str, **fields: object) -> dict:
    payload = {"site": SITE_NAME, "status": status, "message": message}
    payload.update(fields)
    return payload


def resolve_credentials(args: argparse.Namespace) -> tuple[str, str]:
    identifier = str(args.identifier or "").strip() or first_env(*IDENTIFIER_ENV_NAMES)
    password = str(args.password or "").strip() or first_env(*PASSWORD_ENV_NAMES)

    if not identifier:
        raise RedemptionError(
            "未找到账号。请传入 --identifier，或设置 ZAIDUYU_IDENTIFIER"
        )
    if not password:
        raise RedemptionError(
            "未找到密码。请传入 --password，或设置 ZAIDUYU_PASSWORD"
        )
    return identifier, password


def resolve_code(args: argparse.Namespace) -> str:
    code = str(args.code or "").strip() or first_env(*CODE_ENV_NAMES)
    if not code:
        raise RedemptionError(
            "未找到兑换码。请传入 --code，或设置 ZAIDUYU_REDEMPTION_CODE"
        )
    if len(code) > 64:
        raise RedemptionError("兑换码长度不能超过 64 个字符")
    return code


def remaining_value(status: dict) -> object:
    remaining = status.get("remaining")
    if remaining is None:
        return None
    try:
        return int(remaining)
    except (TypeError, ValueError):
        return remaining


def run(args: argparse.Namespace) -> dict:
    base_url = normalize_base_url(
        args.base_url or first_env(*URL_ENV_NAMES) or DEFAULT_URL
    )
    identifier, password = resolve_credentials(args)
    code = None if args.dry_run else resolve_code(args)

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Origin": base_url,
            "Referer": base_url + "/#/limited-redemption",
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
        raise RedemptionError("登录响应未确认账号有效")

    quota = request_json(
        session,
        "GET",
        base_url + "/api/limited-redemption",
        args.timeout,
    )
    remaining = remaining_value(quota)
    if quota.get("enabled") is False:
        raise RedemptionError("站点当前未开放限时兑换码")
    if isinstance(remaining, int) and remaining <= 0:
        raise RedemptionError("当前账号的 24 小时兑换额度已用完")
    if args.dry_run:
        return result(
            "pending",
            "兑换状态正常，未执行兑换",
            limit=quota.get("limit"),
            remaining=remaining,
            reset_at=quota.get("resetAt"),
            credit_type=quota.get("creditType"),
            validity_days=quota.get("validityDays"),
        )

    payload = request_json(
        session,
        "POST",
        base_url + "/api/limited-redemption",
        args.timeout,
        json={"code": code},
    )
    redemption = payload.get("redemption")
    if not isinstance(redemption, dict) or redemption.get("credits") is None:
        raise RedemptionError("兑换响应未确认兑换成功")

    post_status = payload.get("status")
    if post_status is not None and not isinstance(post_status, dict):
        raise RedemptionError("兑换响应中的额度状态格式不正确")
    current_status = post_status if isinstance(post_status, dict) else quota
    credits = redemption.get("credits", 0)
    validity_days = redemption.get("validityDays", current_status.get("validityDays"))
    return result(
        "success",
        f"兑换成功，已到账 {credits} 积分",
        credits=credits,
        remaining=remaining_value(current_status),
        reset_at=current_status.get("resetAt"),
        credit_type=current_status.get("creditType"),
        validity_days=validity_days,
    )


def emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return

    print(f"{payload['site']}：{payload['message']}")
    details = []
    if payload.get("remaining") is not None:
        details.append(f"剩余额度 {payload['remaining']}")
    if payload.get("validity_days") is not None:
        details.append(f"有效 {payload['validity_days']} 天")
    if details:
        print("，".join(details))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clodesen 限时兑换码（适用于 FLS）")
    parser.add_argument(
        "--identifier",
        "--username",
        "--account",
        dest="identifier",
        help="登录账号（用户名或邮箱）",
    )
    parser.add_argument("--password", help="登录密码")
    parser.add_argument(
        "--code",
        "--redemption-code",
        dest="code",
        help="限时兑换码",
    )
    parser.add_argument("--url", "--base-url", dest="base_url", help="站点地址")
    parser.add_argument("--timeout", type=float, default=30.0, help="请求超时秒数，默认 30")
    parser.add_argument("--dry-run", action="store_true", help="只查询额度，不执行兑换")
    parser.add_argument("--json", action="store_true", help="以单行 JSON 输出结果")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")
    return args


def main() -> int:
    args = parse_args()
    try:
        payload = run(args)
    except RedemptionError as exc:
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
