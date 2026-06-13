import argparse
import base64
import hashlib
import json
import os
import sys
from http.cookies import SimpleCookie

import requests
from Crypto.Cipher import AES


LOGIN_URL = "https://music.163.com/weapi/login/cellphone"
DAILY_TASK_URL = "https://music.163.com/weapi/point/dailyTask"
RECOMMEND_URL = "https://music.163.com/weapi/v1/discovery/recommend/resource"
WEBLOG_URL = "http://music.163.com/weapi/feedback/weblog"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/84.0.4147.89 Safari/537.36"
    ),
    "Referer": "http://music.163.com/",
    "Accept-Encoding": "gzip, deflate",
}

LOGIN_HEADERS = {
    **HEADERS,
    "Cookie": (
        "os=pc; osver=Microsoft-Windows-10-Professional-build-10586-64bit; "
        "appver=2.0.3.131777; channel=netease; __remember_me=true;"
    ),
}


class CheckinError(Exception):
    pass


def encrypt(key, text):
    cryptor = AES.new(key.encode("utf8"), AES.MODE_CBC, b"0102030405060708")
    length = 16
    count = len(text.encode("utf-8"))
    add = length - (count % length) if count % length != 0 else 16
    pad = chr(add)
    text1 = text + (pad * add)
    ciphertext = cryptor.encrypt(text1.encode("utf8"))
    return str(base64.b64encode(ciphertext), encoding="utf-8")


def md5(text):
    hl = hashlib.md5()
    hl.update(text.encode(encoding="utf-8"))
    return hl.hexdigest()


def protect(text):
    return {
        "params": encrypt(
            "TA3YiYCfY2dDJQgg",
            encrypt("0CoJUm6Qyw8W8jud", text),
        ),
        "encSecKey": (
            "84ca47bca10bad09a6b04c5c927ef077d9b9f1e37098aa3eac6ea70eb59df"
            "0aa28b691b7e75e4f1f9831754919ea784c8f74fbfadf2898b0be17849f"
            "d656060162857830e241aba44991601f137624094c114ea8d17bce815b0c"
            "d4e5b8e2fbaba978c6d1d14dc3d1faf852bdd28818031ccdaaa13a601"
            "8e1024e2aae98844210"
        ),
    }


def parse_cookie(cookie_text):
    cookie = SimpleCookie()
    cookie_dict = {}
    try:
        cookie.load(cookie_text)
        cookie_dict = {key: morsel.value for key, morsel in cookie.items()}
    except Exception:
        cookie_dict = {}

    if cookie_dict:
        return cookie_dict

    for item in cookie_text.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        if key:
            cookie_dict[key] = value.strip()
    return cookie_dict


def first_env(*names):
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def split_accounts(value):
    if not value:
        return []
    return [item.strip() for item in value.split("#") if item.strip()]


def get_args():
    parser = argparse.ArgumentParser(description="网易云音乐自动签到 + 刷歌")
    parser.add_argument(
        "--cookie",
        default=first_env("NETEASE_COOKIE", "NCM_COOKIE", "COOKIE"),
        help="网易云音乐 Cookie，多账号用 # 分隔",
    )
    parser.add_argument(
        "--phone",
        default=first_env("NETEASE_USER", "NETEASE_PHONE", "NCM_USER", "NCM_PHONE"),
        help="手机号，多账号用 # 分隔",
    )
    parser.add_argument(
        "--password",
        default=first_env("NETEASE_PWD", "NETEASE_PASSWORD", "NCM_PWD", "NCM_PASSWORD"),
        help="密码，多账号用 # 分隔",
    )
    return parser.parse_args()


def login_by_cookie(session, cookie_text):
    cookie_dict = parse_cookie(cookie_text)
    if not cookie_dict:
        raise CheckinError("Cookie 为空或格式不正确")

    requests.utils.add_dict_to_cookiejar(session.cookies, cookie_dict)
    print("已使用 Cookie 登录")
    return cookie_dict


def login_by_password(session, phone, password):
    if not phone or not password:
        raise CheckinError("请设置 NETEASE_COOKIE，或同时设置 NETEASE_USER 和 NETEASE_PWD")

    logindata = {
        "phone": phone,
        "countrycode": "86",
        "password": md5(password),
        "rememberLogin": "true",
    }
    res = session.post(
        url=LOGIN_URL,
        data=protect(json.dumps(logindata)),
        headers=LOGIN_HEADERS,
        timeout=30,
    )
    result = json.loads(res.text)
    if result.get("code") == 200:
        print("登录成功")
        return requests.utils.dict_from_cookiejar(session.cookies)

    raise CheckinError("登录失败，请检查密码是否正确：" + str(result.get("code")))


def get_csrf(cookie_dict):
    return cookie_dict.get("__csrf", "")


def daily_task(session):
    last_message = None
    for task_type in (0, 1):
        res = session.post(
            url=DAILY_TASK_URL,
            data=protect(json.dumps({"type": task_type})),
            headers=HEADERS,
            timeout=30,
        )
        result = json.loads(res.text)
        code = result.get("code")
        if code == -2:
            print("重复签到")
            return
        if code == 200 and "point" in result:
            print("签到成功，经验+" + str(result["point"]))
            return

        last_message = result.get("msg") or result.get("message") or str(code)
        if code != 200:
            raise CheckinError("签到时发生错误：" + last_message)

    raise CheckinError("签到时发生错误：" + str(last_message))


def build_play_logs(session, csrf_token):
    res = session.post(
        url=RECOMMEND_URL,
        data=protect(json.dumps({"csrf_token": csrf_token})),
        headers=HEADERS,
        timeout=30,
    )
    result = json.loads(res.text, strict=False)
    recommend = result.get("recommend")
    if not isinstance(recommend, list):
        message = result.get("msg") or result.get("message") or str(result.get("code"))
        raise CheckinError("获取推荐歌单失败：" + message)

    buffer = []
    count = 0
    for playlist in recommend:
        url = "https://music.163.com/weapi/v3/playlist/detail?csrf_token=" + csrf_token
        data = {
            "id": playlist["id"],
            "n": 1000,
            "csrf_token": csrf_token,
        }
        res = session.post(url, protect(json.dumps(data)), headers=HEADERS, timeout=30)
        result = json.loads(res.text, strict=False)
        tracks = result.get("playlist", {}).get("trackIds", [])
        for track in tracks:
            buffer.append(
                {
                    "action": "play",
                    "json": {
                        "download": 0,
                        "end": "playend",
                        "id": track["id"],
                        "sourceId": "",
                        "time": "240",
                        "type": "song",
                        "wifi": 0,
                    },
                }
            )
            count += 1
            if count >= 310:
                break
        if count >= 310:
            break
    return buffer, count


def send_play_logs(session, buffer, count):
    postdata = {"logs": json.dumps(buffer)}
    res = session.post(
        WEBLOG_URL,
        protect(json.dumps(postdata)),
        headers=HEADERS,
        timeout=30,
    )
    result = json.loads(res.text, strict=False)
    if result.get("code") == 200:
        print("刷歌成功，共" + str(count) + "首")
        return

    raise CheckinError(
        "刷歌失败：" + str(result.get("code")) + str(result.get("message", ""))
    )


def run_account(cookie_text=None, phone=None, password=None):
    session = requests.Session()

    if cookie_text:
        cookie_dict = login_by_cookie(session, cookie_text)
    else:
        cookie_dict = login_by_password(session, phone, password)

    csrf_token = get_csrf(cookie_dict)
    daily_task(session)
    buffer, count = build_play_logs(session, csrf_token)
    send_play_logs(session, buffer, count)


def run_cookie_accounts(cookies):
    failed = 0
    print("共有 " + str(len(cookies)) + " 个 Cookie，即将开始签到")
    for index, cookie_text in enumerate(cookies, 1):
        print("========== Cookie 账号 " + str(index) + " ==========")
        try:
            run_account(cookie_text=cookie_text)
        except Exception as exc:
            failed += 1
            print("账号 " + str(index) + " 执行失败：" + str(exc))
    return failed


def run_password_accounts(phones, passwords):
    if len(phones) != len(passwords):
        raise CheckinError(
            "账号和密码个数不对应：账号 "
            + str(len(phones))
            + " 个，密码 "
            + str(len(passwords))
            + " 个"
        )

    failed = 0
    print("共有 " + str(len(phones)) + " 个账号，即将开始签到")
    for index, (phone, password) in enumerate(zip(phones, passwords), 1):
        print("========== 手机号账号 " + str(index) + " ==========")
        try:
            run_account(phone=phone, password=password)
        except Exception as exc:
            failed += 1
            print("账号 " + str(index) + " 执行失败：" + str(exc))
    return failed


def main():
    args = get_args()

    cookies = split_accounts(args.cookie)
    if cookies:
        failed = run_cookie_accounts(cookies)
    else:
        phones = split_accounts(args.phone)
        passwords = split_accounts(args.password)
        if not phones or not passwords:
            raise CheckinError("请设置 NETEASE_COOKIE，或同时设置 NETEASE_USER 和 NETEASE_PWD")
        failed = run_password_accounts(phones, passwords)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except CheckinError as exc:
        print(str(exc))
        sys.exit(1)
