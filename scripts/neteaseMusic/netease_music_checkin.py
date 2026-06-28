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


def parse_song_ids_optional(value):
    if not value or not str(value).strip():
        return []
    ids = []
    for part in str(value).replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if part.isdigit():
            ids.append(int(part))
        else:
            print("忽略无效歌曲 ID：" + part)
    return ids


def parse_playlist_id_optional(value):
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    for part in text.replace("，", ",").split(","):
        part = part.strip()
        if part.isdigit():
            return int(part)
    print("忽略无效歌单 ID：" + text)
    return None


DEFAULT_PLAY_COUNT = 310


def play_log_entry(song_id):
    return {
        "action": "play",
        "json": {
            "download": 0,
            "end": "playend",
            "id": song_id,
            "sourceId": "",
            "time": "240",
            "type": "song",
            "wifi": 0,
        },
    }


def fill_buffer_from_track_ids(track_ids, target_count):
    buffer = []
    count = 0
    if not track_ids:
        return buffer, count
    index = 0
    while count < target_count:
        tid = track_ids[index % len(track_ids)]
        song_id = tid["id"] if isinstance(tid, dict) else tid
        buffer.append(play_log_entry(song_id))
        count += 1
        index += 1
    return buffer, count


def fetch_playlist_track_ids(session, playlist_id, csrf_token):
    url = "https://music.163.com/weapi/v3/playlist/detail?csrf_token=" + csrf_token
    data = {
        "id": playlist_id,
        "n": 1000,
        "csrf_token": csrf_token,
    }
    res = session.post(url, protect(json.dumps(data)), headers=HEADERS, timeout=30)
    result = json.loads(res.text, strict=False)
    playlist = result.get("playlist")
    if not playlist:
        message = result.get("msg") or result.get("message") or str(result.get("code"))
        raise CheckinError("获取歌单失败（id=" + str(playlist_id) + "）：" + message)
    return playlist.get("trackIds", [])


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
    parser.add_argument(
        "--song-ids",
        default=first_env("NETEASE_SONG_IDS", "NCM_SONG_IDS"),
        help="指定刷歌的歌曲 ID，逗号分隔；会循环上报直到达到刷歌数量",
    )
    parser.add_argument(
        "--playlist-id",
        default=first_env("NETEASE_PLAYLIST_ID", "NCM_PLAYLIST_ID"),
        help="指定歌单 ID，从该歌单取曲目刷歌（优先于每日推荐）",
    )
    parser.add_argument(
        "--play-count",
        type=int,
        default=int(first_env("NETEASE_PLAY_COUNT", "NCM_PLAY_COUNT") or DEFAULT_PLAY_COUNT),
        help="刷歌上报条数，默认 " + str(DEFAULT_PLAY_COUNT),
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


def build_play_logs_from_recommend(session, csrf_token, target_count):
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
        tracks = fetch_playlist_track_ids(session, playlist["id"], csrf_token)
        for track in tracks:
            buffer.append(play_log_entry(track["id"]))
            count += 1
            if count >= target_count:
                break
        if count >= target_count:
            break
    return buffer, count


def build_play_logs(session, csrf_token, song_ids=None, playlist_id=None, target_count=DEFAULT_PLAY_COUNT):
    if song_ids:
        print("使用指定歌曲 ID 刷歌：" + ",".join(str(i) for i in song_ids))
        return fill_buffer_from_track_ids(song_ids, target_count)

    if playlist_id is not None:
        print("使用指定歌单 ID 刷歌：" + str(playlist_id))
        track_ids = []
        try:
            track_ids = fetch_playlist_track_ids(session, playlist_id, csrf_token)
        except CheckinError as exc:
            print(str(exc) + "，改用每日推荐")
        except Exception as exc:
            print("获取歌单失败：" + str(exc) + "，改用每日推荐")
        if track_ids:
            return fill_buffer_from_track_ids(track_ids, target_count)
        if playlist_id is not None:
            print("歌单内没有可刷曲目，改用每日推荐")

    print("使用每日推荐歌单刷歌")
    return build_play_logs_from_recommend(session, csrf_token, target_count)


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


def run_account(
    cookie_text=None,
    phone=None,
    password=None,
    song_ids=None,
    playlist_id=None,
    play_count=DEFAULT_PLAY_COUNT,
):
    session = requests.Session()

    if cookie_text:
        cookie_dict = login_by_cookie(session, cookie_text)
    else:
        cookie_dict = login_by_password(session, phone, password)

    csrf_token = get_csrf(cookie_dict)
    daily_task(session)
    buffer, count = build_play_logs(
        session,
        csrf_token,
        song_ids=song_ids,
        playlist_id=playlist_id,
        target_count=play_count,
    )
    if count < 1:
        raise CheckinError("没有生成任何刷歌记录")
    send_play_logs(session, buffer, count)


def run_cookie_accounts(cookies, play_options):
    failed = 0
    print("共有 " + str(len(cookies)) + " 个 Cookie，即将开始签到")
    for index, cookie_text in enumerate(cookies, 1):
        print("========== Cookie 账号 " + str(index) + " ==========")
        try:
            run_account(cookie_text=cookie_text, **play_options)
        except Exception as exc:
            failed += 1
            print("账号 " + str(index) + " 执行失败：" + str(exc))
    return failed


def run_password_accounts(phones, passwords, play_options):
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
            run_account(phone=phone, password=password, **play_options)
        except Exception as exc:
            failed += 1
            print("账号 " + str(index) + " 执行失败：" + str(exc))
    return failed


def resolve_play_options(args):
    song_ids = parse_song_ids_optional(args.song_ids)
    playlist_id = parse_playlist_id_optional(args.playlist_id)
    if song_ids:
        playlist_id = None
    elif playlist_id is None:
        print("未配置有效歌曲/歌单 ID，使用每日推荐刷歌")
    play_count = args.play_count
    if play_count < 1:
        raise CheckinError("play-count 至少为 1")
    return {
        "song_ids": song_ids if song_ids else None,
        "playlist_id": playlist_id,
        "play_count": play_count,
    }


def main():
    args = get_args()
    play_options = resolve_play_options(args)

    cookies = split_accounts(args.cookie)
    if cookies:
        failed = run_cookie_accounts(cookies, play_options)
    else:
        phones = split_accounts(args.phone)
        passwords = split_accounts(args.password)
        if not phones or not passwords:
            raise CheckinError("请设置 NETEASE_COOKIE，或同时设置 NETEASE_USER 和 NETEASE_PWD")
        failed = run_password_accounts(phones, passwords, play_options)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except CheckinError as exc:
        print(str(exc))
        sys.exit(1)
