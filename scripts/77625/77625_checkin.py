#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""77625 routing service daily check-in for FLS."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from urllib.parse import urlsplit

import requests


SITE_NAME = "77625 路由站"
DEFAULT_URL = "https://ly.77625.xyz"
USERNAME_ENV = "LY77625_USERNAME"
PASSWORD_ENV = "LY77625_PASSWORD"
URL_ENV = "LY77625_URL"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class CheckinError(RuntimeError):
    """An expected, user-actionable check-in failure."""


def normalize_base_url(value: str) -> str:
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError
        if parsed.username is not None or parsed.password is not None:
            raise ValueError
        parsed.port
    except ValueError as exc:
        raise CheckinError("URL 必须是完整且不含账号密码的 http(s) 地址") from exc
    return f"{parsed.scheme}://{parsed.netloc}"


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

    if response.headers.get("cf-mitigated", "").lower() == "challenge":
        raise CheckinError("站点触发 Cloudflare 浏览器验证，当前请求无法完成")
    try:
        payload = response.json()
    except ValueError as exc:
        raise CheckinError(f"接口返回非 JSON（HTTP {response.status_code}）") from exc
    if not isinstance(payload, dict):
        raise CheckinError("接口返回格式不正确")
    if not response.ok or payload.get("ok") is False or payload.get("error"):
        detail = payload.get("detail") or payload.get("message") or payload.get("error")
        raise CheckinError(
            f"接口请求失败（HTTP {response.status_code}）：{detail or '请求未成功'}"
        )
    return payload


def result(status: str, message: str, **fields: object) -> dict:
    return {"site": SITE_NAME, "status": status, "message": message, **fields}


def run(args: argparse.Namespace) -> dict:
    username = (args.username or os.environ.get(USERNAME_ENV, "")).strip()
    password = args.password if args.password is not None else os.environ.get(PASSWORD_ENV, "")
    if not username or not password:
        raise CheckinError(f"请设置 {USERNAME_ENV} 和 {PASSWORD_ENV}，或传入 --username / --password")
    base_url = normalize_base_url(args.base_url or os.environ.get(URL_ENV, "").strip() or DEFAULT_URL)

    with requests.Session() as session:
        session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
                "Origin": base_url,
                "Referer": base_url + "/",
            }
        )
        login = request_json(
            session,
            "POST",
            base_url + "/api/auth/login",
            args.timeout,
            json={"username": username, "password": password, "remember": False},
        )
        if login.get("ok") is not True:
            raise CheckinError("登录响应未确认登录成功")

        state = request_json(session, "GET", base_url + "/api/auth/me", args.timeout)
        if not isinstance(state.get("checked_in_today"), bool):
            raise CheckinError("账号信息缺少有效的 checked_in_today 签到状态")
        if state["checked_in_today"]:
            return result("already_signed", "今日已签到", points=state.get("credits"))
        if state.get("checkin_enabled") is not True:
            raise CheckinError("站点当前未开启每日签到")
        if args.dry_run:
            return result("pending", "状态正常，未执行签到", points=state.get("credits"))

        try:
            payload = request_json(session, "POST", base_url + "/api/account/checkin", args.timeout)
        except CheckinError:
            # The check-in may have completed even if its response was lost.
            state = request_json(session, "GET", base_url + "/api/auth/me", args.timeout)
            if state.get("checked_in_today") is True:
                return result("already_signed", "今日已签到", points=state.get("credits"))
            raise
        if payload.get("points") is None or payload.get("credits") is None:
            raise CheckinError("签到响应未返回奖励积分和当前余额，无法确认签到成功")
        reward = payload["points"]
        return result("success", f"签到成功，获得 {reward} 积分", reward=reward, points=payload["credits"])


def emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return
    print(f"{payload['site']}：{payload['message']}")
    if payload.get("points") is not None:
        print(f"当前积分：{payload['points']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="77625 路由站每日签到（适用于 FLS）")
    parser.add_argument("--username", help=f"登录账号；默认读取 {USERNAME_ENV}")
    parser.add_argument("--password", help=f"登录密码；默认读取 {PASSWORD_ENV}")
    parser.add_argument("--url", "--base-url", dest="base_url", help=f"站点地址；默认读取 {URL_ENV} 或 {DEFAULT_URL}")
    parser.add_argument("--timeout", type=float, default=30.0, help="请求超时秒数，默认 30")
    parser.add_argument("--dry-run", action="store_true", help="只查询状态，不执行签到")
    parser.add_argument("--json", action="store_true", help="以单行 JSON 输出结果")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout 必须是大于 0 的有限数值")
    return args


def main() -> int:
    args = parse_args()
    try:
        payload = run(args)
    except CheckinError as exc:
        emit(result("error", str(exc)), args.json)
        return 1
    except KeyboardInterrupt:
        emit(result("error", "已取消"), args.json)
        return 130
    emit(payload, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
