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
ACCOUNTS_ENV_NAMES = ("ZAIDUYU_ACCOUNTS", "PAI_ACCOUNTS")
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


def parse_accounts(raw: str) -> list[tuple[str, str]]:
    entries = [entry.strip() for entry in raw.split("#") if entry.strip()]
    if not entries:
        raise RedemptionError(
            "ZAIDUYU_ACCOUNTS 不能为空，格式应为：账号1,密码1#账号2,密码2"
        )

    accounts = []
    for index, entry in enumerate(entries, 1):
        if "," not in entry:
            raise RedemptionError(
                f"ZAIDUYU_ACCOUNTS 第 {index} 项格式不正确，应为账号,密码"
            )
        identifier, password = entry.split(",", 1)
        identifier = identifier.strip()
        password = password.strip()
        if not identifier or not password:
            raise RedemptionError(f"ZAIDUYU_ACCOUNTS 第 {index} 项缺少账号或密码")
        accounts.append((identifier, password))

    return accounts


def resolve_accounts(args: argparse.Namespace) -> list[tuple[str, str]]:
    raw = str(args.accounts or "").strip() or first_env(*ACCOUNTS_ENV_NAMES)
    if raw:
        return parse_accounts(raw)

    identifier = str(args.identifier or "").strip() or first_env(*IDENTIFIER_ENV_NAMES)
    password = str(args.password or "").strip() or first_env(*PASSWORD_ENV_NAMES)
    if not identifier:
        raise RedemptionError(
            "未找到账号。请传入 --identifier，或设置 ZAIDUYU_IDENTIFIER，或设置 ZAIDUYU_ACCOUNTS"
        )
    if not password:
        raise RedemptionError(
            "未找到密码。请传入 --password，或设置 ZAIDUYU_PASSWORD，或设置 ZAIDUYU_ACCOUNTS"
        )
    return [(identifier, password)]


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


def run_account(
    base_url: str,
    identifier: str,
    password: str,
    code: str | None,
    args: argparse.Namespace,
) -> dict:
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


def run(args: argparse.Namespace) -> dict:
    base_url = normalize_base_url(
        args.base_url or first_env(*URL_ENV_NAMES) or DEFAULT_URL
    )
    accounts = resolve_accounts(args)
    code = None if args.dry_run else resolve_code(args)
    account_results = []

    for index, (identifier, password) in enumerate(accounts, 1):
        try:
            account_payload = run_account(base_url, identifier, password, code, args)
        except RedemptionError as exc:
            account_payload = result("error", str(exc))

        account_payload["account_index"] = index
        account_payload["account"] = identifier
        account_results.append(account_payload)

    if len(account_results) == 1:
        return account_results[0]

    success_count = sum(item.get("status") == ("pending" if args.dry_run else "success") for item in account_results)
    failed_count = len(account_results) - success_count
    if failed_count == 0:
        aggregate_status = "pending" if args.dry_run else "success"
    elif success_count == 0:
        aggregate_status = "error"
    else:
        aggregate_status = "partial"

    action = "查询" if args.dry_run else "兑换"
    return result(
        aggregate_status,
        f"多账号{action}完成：成功 {success_count} 个，失败 {failed_count} 个",
        accounts=account_results,
    )


def emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return

    print(f"{payload['site']}：{payload['message']}")
    if isinstance(payload.get("accounts"), list):
        for item in payload["accounts"]:
            account = item.get("account") or f"账号{item.get('account_index', '?')}"
            print(f"[{account}] {item.get('message', '无结果')}")
        return

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
        "--accounts",
        help="多账号，格式为 账号1,密码1#账号2,密码2",
    )
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
    return 1 if payload.get("status") in {"error", "partial"} else 0


if __name__ == "__main__":
    sys.exit(main())
