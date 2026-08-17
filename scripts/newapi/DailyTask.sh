#!/bin/ash

DEFAULT_URL="https://huashang.dpdns.org"

RAW_USER_ID="${user_id:-${USER_ID:-$1}}"
RAW_TOKEN="${token:-${TOKEN:-$2}}"
RAW_TOKENS="${tokens:-${TOKENS:-}}"
RAW_URL="${url:-${URL:-${3:-}}}"
RAW_COOKIE="${cookie:-${COOKIE:-${session_cookie:-${SESSION_COOKIE:-}}}}"

ACCOUNTS=""
ACCOUNT_COUNT=0
SUCCESS_COUNT=0
FAIL_COUNT=0

AUTH_MODE=""
USER_ID=""
TOKEN=""
SESSION_COOKIE=""
BASE_URL=""
json_data=""

ui_print() {
    echo "$@"
}

usage() {
    echo "用法："
    echo "  令牌模式：$0 <user_id> <token> [url]"
    echo ""
    echo "也可通过环境变量设置："
    echo "  user_id=123,456,789"
    echo "  token=aaa,bbbbbb,ccc"
    echo "  tokens='123#aaa#1.com,456#bbb#2.com'"
    echo "  url=1.com,2.com,3.com"
    echo "  cookie=aaa,bbbbbb,ccc"
    echo "  cookie='123#aaaaa#1.com,456#qqqqqq,2.com'"
    echo ""
    echo "说明："
    echo "  token 模式可配合 user_id 变量使用，也可写成 tokens=user_id#token[#url]。"
    echo "  cookie 模式可配合 user_id 变量使用，也可写成 user_id#cookie[#url]。"
    echo "  url 可省略，默认 ${DEFAULT_URL}；url 不带协议时自动补 https://。"
    echo ""
    echo "示例："
    echo "  user_id='123,456' token='aaa,bbb' url='1.com,2.com' $0"
    echo "  tokens='123#aaa#1.com,456#bbb,2.com' $0"
    echo "  cookie='123#aaaaa#1.com,456#qqqqqq,2.com' $0"
    echo ""
}

trim() {
    printf '%s' "$1" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

normalize_base_url() {
    local raw
    raw=$(trim "$1")
    [ -z "$raw" ] && raw="$DEFAULT_URL"
    raw="${raw%/}"
    case "$raw" in
        http://*|https://*) echo "$raw" ;;
        *) echo "https://$raw" ;;
    esac
}

normalize_session_cookie() {
    local raw
    local session_value

    raw=$(trim "$1")
    raw=$(printf '%s' "$raw" | sed 's/^[[:space:]]*[Cc][Oo][Oo][Kk][Ii][Ee]:[[:space:]]*//')

    session_value=$(printf '%s' "$raw" | awk -F';' '
        {
            for (i = 1; i <= NF; i++) {
                part = $i
                gsub(/^[ \t]+|[ \t]+$/, "", part)
                if (part ~ /^session=/) {
                    sub(/^session=/, "", part)
                    print part
                    exit
                }
            }
        }
    ')

    if [ -n "$session_value" ]; then
        echo "$session_value"
        return
    fi

    case "$raw" in
        session=*) echo "${raw#session=}" ;;
        *) echo "$raw" ;;
    esac
}

normalize_cookie_header() {
    local raw

    raw=$(trim "$1")
    raw=$(printf '%s' "$raw" | sed 's/^[[:space:]]*[Cc][Oo][Oo][Kk][Ii][Ee]:[[:space:]]*//')
    if [ -z "$raw" ]; then
        echo ""
        return
    fi

    case "$raw" in
        *=*) echo "$raw" ;;
        *) echo "session=$raw" ;;
    esac
}

is_positive_int() {
    case "$1" in
        ""|*[!0-9]*) return 1 ;;
    esac
    [ "$1" -gt 0 ] 2>/dev/null
}

csv_count() {
    local value="$1"
    if [ -z "$value" ]; then
        echo 0
        return
    fi
    awk -v text="$value" 'BEGIN {
        n = split(text, parts, ",")
        count = 0
        for (i = 1; i <= n; i++) {
            gsub(/^[ \t]+|[ \t]+$/, "", parts[i])
            if (parts[i] != "") {
                count++
            }
        }
        print count
    }'
}

csv_item() {
    local value="$1"
    local wanted="$2"
    awk -v text="$value" -v wanted="$wanted" 'BEGIN {
        n = split(text, parts, ",")
        count = 0
        for (i = 1; i <= n; i++) {
            gsub(/^[ \t]+|[ \t]+$/, "", parts[i])
            if (parts[i] != "") {
                count++
                if (count == wanted) {
                    print parts[i]
                    exit
                }
            }
        }
    }'
}

csv_value_for_index() {
    local value="$1"
    local index="$2"
    local total="$3"
    local name="$4"
    local fallback="$5"
    local count

    count=$(csv_count "$value")
    if [ "$count" -eq 0 ]; then
        echo "$fallback"
        return 0
    fi
    if [ "$count" -eq 1 ]; then
        csv_item "$value" 1
        return 0
    fi
    if [ "$count" -eq "$total" ]; then
        csv_item "$value" "$index"
        return 0
    fi

    echo "错误：环境变量 ${name} 数量必须为 1 或 ${total}，当前为 ${count}" >&2
    return 1
}

max_number() {
    local max="$1"
    shift
    while [ $# -gt 0 ]; do
        [ "$1" -gt "$max" ] && max="$1"
        shift
    done
    echo "$max"
}

append_account() {
    local mode="$1"
    local account_user_id
    local secret
    local account_url

    account_user_id=$(trim "$2")
    secret=$(trim "$3")
    account_url=$(normalize_base_url "$4")

    if ! is_positive_int "$account_user_id"; then
        ui_print "错误：无效 user_id：$account_user_id"
        return 1
    fi
    if [ -z "$secret" ]; then
        ui_print "错误：用户 ${account_user_id} 的认证信息为空"
        return 1
    fi

    if [ -z "$ACCOUNTS" ]; then
        ACCOUNTS="${mode}|${account_user_id}|${secret}|${account_url}"
    else
        ACCOUNTS="${ACCOUNTS}
${mode}|${account_user_id}|${secret}|${account_url}"
    fi
    ACCOUNT_COUNT=$((ACCOUNT_COUNT + 1))
    return 0
}

build_token_accounts() {
    local user_count
    local token_count
    local url_count
    local total
    local index
    local account_user_id
    local account_token
    local account_url

    if [ -z "$RAW_USER_ID" ] && [ -z "$RAW_TOKEN" ]; then
        return 0
    fi
    if [ -z "$RAW_TOKEN" ] && { [ -n "$RAW_TOKENS" ] || [ -n "$RAW_COOKIE" ]; }; then
        return 0
    fi
    if [ -z "$RAW_USER_ID" ] || [ -z "$RAW_TOKEN" ]; then
        ui_print "错误：令牌模式需要同时设置 user_id 和 token"
        return 1
    fi

    user_count=$(csv_count "$RAW_USER_ID")
    token_count=$(csv_count "$RAW_TOKEN")
    url_count=$(csv_count "$RAW_URL")
    total=$(max_number "$user_count" "$token_count" "$url_count")

    if [ "$total" -le 0 ]; then
        ui_print "错误：未解析到令牌用户"
        return 1
    fi

    index=1
    while [ "$index" -le "$total" ]; do
        account_user_id=$(csv_value_for_index "$RAW_USER_ID" "$index" "$total" "user_id" "") || return 1
        account_token=$(csv_value_for_index "$RAW_TOKEN" "$index" "$total" "token" "") || return 1
        account_url=$(csv_value_for_index "$RAW_URL" "$index" "$total" "url" "$DEFAULT_URL") || return 1
        append_account "token" "$account_user_id" "$account_token" "$account_url" || return 1
        index=$((index + 1))
    done
    return 0
}

build_cookie_csv_accounts() {
    local user_count
    local cookie_count
    local url_count
    local total
    local index
    local account_user_id
    local account_cookie
    local account_url

    if [ -z "$RAW_USER_ID" ]; then
        ui_print "错误：cookie 变量不含 user_id#cookie 格式时，需要同时设置 user_id"
        return 1
    fi

    user_count=$(csv_count "$RAW_USER_ID")
    cookie_count=$(csv_count "$RAW_COOKIE")
    url_count=$(csv_count "$RAW_URL")
    total=$(max_number "$user_count" "$cookie_count" "$url_count")

    if [ "$total" -le 0 ]; then
        ui_print "错误：未解析到 cookie 用户"
        return 1
    fi

    index=1
    while [ "$index" -le "$total" ]; do
        account_user_id=$(csv_value_for_index "$RAW_USER_ID" "$index" "$total" "user_id" "") || return 1
        account_cookie=$(csv_value_for_index "$RAW_COOKIE" "$index" "$total" "cookie" "") || return 1
        account_url=$(csv_value_for_index "$RAW_URL" "$index" "$total" "url" "$DEFAULT_URL") || return 1
        account_cookie=$(normalize_cookie_header "$account_cookie")
        append_account "cookie" "$account_user_id" "$account_cookie" "$account_url" || return 1
        index=$((index + 1))
    done
    return 0
}

COOKIE_RECORDS=""
COOKIE_RECORD_COUNT=0

append_cookie_record() {
    local record
    record=$(trim "$1")
    [ -z "$record" ] && return 0

    if [ -z "$COOKIE_RECORDS" ]; then
        COOKIE_RECORDS="$record"
    else
        COOKIE_RECORDS="${COOKIE_RECORDS}
${record}"
    fi
    COOKIE_RECORD_COUNT=$((COOKIE_RECORD_COUNT + 1))
}

parse_cookie_records() {
    local rest="$1"
    local part
    local pending=""

    COOKIE_RECORDS=""
    COOKIE_RECORD_COUNT=0

    while [ -n "$rest" ]; do
        case "$rest" in
            *,*)
                part="${rest%%,*}"
                rest="${rest#*,}"
                ;;
            *)
                part="$rest"
                rest=""
                ;;
        esac

        part=$(trim "$part")
        [ -z "$part" ] && continue

        case "$part" in
            *"#"*"#"*)
                if [ -n "$pending" ]; then
                    append_cookie_record "$pending"
                    pending=""
                fi
                append_cookie_record "$part"
                ;;
            *"#"*)
                if [ -n "$pending" ]; then
                    append_cookie_record "$pending"
                fi
                pending="$part"
                ;;
            *)
                if [ -n "$pending" ]; then
                    append_cookie_record "${pending}#${part}"
                    pending=""
                else
                    append_cookie_record "$part"
                fi
                ;;
        esac
    done

    if [ -n "$pending" ]; then
        append_cookie_record "$pending"
    fi
}

build_token_record_accounts() {
    local index
    local record
    local account_user_id
    local rest
    local account_token
    local account_url

    [ -z "$RAW_TOKENS" ] && return 0

    parse_cookie_records "$RAW_TOKENS"
    if [ "$COOKIE_RECORD_COUNT" -le 0 ]; then
        ui_print "错误：未解析到 tokens 用户"
        return 1
    fi

    index=1
    while IFS= read -r record; do
        [ -z "$record" ] && continue
        case "$record" in
            *"#"*) ;;
            *)
                ui_print "错误：tokens 格式应为 user_id#token[#url]：$record"
                return 1
                ;;
        esac

        account_user_id="${record%%#*}"
        rest="${record#*#}"
        account_token="${rest%%#*}"
        if [ "$rest" != "$account_token" ]; then
            account_url="${rest#*#}"
        else
            account_url=$(csv_value_for_index "$RAW_URL" "$index" "$COOKIE_RECORD_COUNT" "url" "$DEFAULT_URL") || return 1
        fi

        append_account "token" "$account_user_id" "$account_token" "$account_url" || return 1
        index=$((index + 1))
    done <<EOF
$COOKIE_RECORDS
EOF

    return 0
}

build_cookie_accounts() {
    local index
    local record
    local account_user_id
    local rest
    local account_cookie
    local account_url

    [ -z "$RAW_COOKIE" ] && return 0

    case "$RAW_COOKIE" in
        *"#"*) ;;
        *) build_cookie_csv_accounts; return $? ;;
    esac

    parse_cookie_records "$RAW_COOKIE"
    if [ "$COOKIE_RECORD_COUNT" -le 0 ]; then
        ui_print "错误：未解析到 cookie 用户"
        return 1
    fi

    index=1
    while IFS= read -r record; do
        [ -z "$record" ] && continue
        case "$record" in
            *"#"*) ;;
            *)
                ui_print "错误：cookie 格式应为 user_id#cookie[#url]：$record"
                return 1
                ;;
        esac

        account_user_id="${record%%#*}"
        rest="${record#*#}"
        account_cookie="${rest%%#*}"
        if [ "$rest" != "$account_cookie" ]; then
            account_url="${rest#*#}"
        else
            account_url=$(csv_value_for_index "$RAW_URL" "$index" "$COOKIE_RECORD_COUNT" "url" "$DEFAULT_URL") || return 1
        fi

        account_cookie=$(normalize_cookie_header "$account_cookie")
        append_account "cookie" "$account_user_id" "$account_cookie" "$account_url" || return 1
        index=$((index + 1))
    done <<EOF
$COOKIE_RECORDS
EOF

    return 0
}

build_accounts() {
    build_token_record_accounts || return 1
    build_token_accounts || return 1
    build_cookie_accounts || return 1

    if [ "$ACCOUNT_COUNT" -le 0 ]; then
        usage
        return 1
    fi
    return 0
}

curl_wrapper() {
    local endpoint="$1"
    local method="$2"
    local data="$3"
    local curl_path
    local auth_header

    curl_path=$(which curl)

    if [ -z "$curl_path" ]; then
        ui_print "错误：找不到 curl 命令"
        return 1
    fi

    if [ "$AUTH_MODE" = "cookie" ]; then
        auth_header="Cookie: $SESSION_COOKIE"
    else
        auth_header="Authorization: Bearer ${TOKEN}"
    fi

    json_data=$($curl_path -s --connect-timeout 8 --max-time 45 \
        -X "$method" "${BASE_URL}${endpoint}" \
        -H "new-api-user: $USER_ID" \
        -H "$auth_header" \
        -H 'User-Agent: Mozilla/5.0 (Linux; Android; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36' \
        -H 'Accept: application/json, text/plain, */*' \
        -H 'sec-ch-ua-platform: "Android"' \
        -H 'sec-ch-ua: "Chromium";v="146", "Not-A.Brand";v="24", "Android WebView";v="146"' \
        -H 'sec-ch-ua-mobile: ?1' \
        -H "origin: $BASE_URL" \
        -H "referer: ${BASE_URL}/console/personal" \
        -H 'x-requested-with: mark.via' \
        -H 'sec-fetch-site: same-origin' \
        -H 'sec-fetch-mode: cors' \
        -H 'sec-fetch-dest: empty' \
        -H 'accept-language: zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7' \
        -H 'priority: u=1,i' \
        ${data:+-H 'Content-Type: application/json' -d "$data"} \
        2>/dev/null)

    if [ -z "$json_data" ]; then
        ui_print "请求失败：无响应 (${BASE_URL}${endpoint})"
        return 1
    fi

    return 0
}

get_value() {
    local key="$1"
    echo "$json_data" | sed -n "s/.*\"$key\": *\([^,}]*\).*/\1/p" | tr -d ' "'
}

bytes_to_human() {
    local bytes=$1

    if [ -z "$bytes" ] || [ "$bytes" = "null" ]; then
        echo "💰"
        return
    fi

    local mb
    mb=$(awk "BEGIN {printf \"%.2f\", $bytes / 500000}")
    echo "${mb} 💰"
}

set_account_context() {
    local mode="$1"
    local account_user_id="$2"
    local secret="$3"
    local account_url="$4"

    AUTH_MODE="$mode"
    USER_ID="$account_user_id"
    BASE_URL=$(normalize_base_url "$account_url")
    TOKEN=""
    SESSION_COOKIE=""
    if [ "$AUTH_MODE" = "cookie" ]; then
        SESSION_COOKIE="$secret"
    else
        TOKEN="$secret"
    fi
}

do_user_info() {
    ui_print "→ 获取用户信息..."

    curl_wrapper "/api/user/self" "GET"

    if [ $? -ne 0 ]; then
        ui_print "获取用户信息失败"
        return 1
    fi

    local original_json="$json_data"
    json_data=$(echo "$json_data" | tr -d '\n\r')

    local username
    local id
    local group
    local display_name
    local quota
    local used_quota
    local request_count

    username=$(get_value "username")
    id=$(get_value "id")
    group=$(get_value "group")
    display_name=$(get_value "display_name")
    quota=$(get_value "quota")
    used_quota=$(get_value "used_quota")
    request_count=$(get_value "request_count")

    json_data="$original_json"

    ui_print "=== 用户数据 ==="
    ui_print "昵称：${username}"
    ui_print "显示名：${display_name}"
    ui_print "ID: ${id}"
    ui_print "群组：${group}"
    ui_print "余额：$(bytes_to_human "$quota")"
    ui_print "消耗：$(bytes_to_human "$used_quota")"
    ui_print "次数：${request_count}"
    ui_print "================"
    return 0
}

print_all_user_info() {
    local account_mode
    local account_user_id
    local account_secret
    local account_url

    ui_print "===== 拉取用户信息 ====="
    while IFS='|' read -r account_mode account_user_id account_secret account_url; do
        [ -z "$account_mode" ] && continue
        set_account_context "$account_mode" "$account_user_id" "$account_secret" "$account_url"
        do_user_info
        ui_print ""
    done <<EOF
$ACCOUNTS
EOF
}

do_checkin() {
    ui_print "→ 正在签到..."

    curl_wrapper "/api/user/checkin" "POST"

    if [ $? -ne 0 ]; then
        ui_print "签到失败：网络或响应异常"
        return 1
    fi

    local message
    local success
    local quota
    local date

    message=$(get_value "message")
    success=$(get_value "success")
    quota=$(get_value "quota_awarded")
    date=$(get_value "checkin_date")

    ui_print "签到结果：$message"

    case "$quota" in
        ""|*[!0-9]*) ;;
        *)
            if [ "$success" = "true" ] && [ "$quota" -gt 0 ]; then
                ui_print "获得额度：$(bytes_to_human "$quota")"
                ui_print "签到日期：$date"
            fi
            ;;
    esac

    if [ "$success" = "true" ]; then
        return 0
    fi

    case "$message" in
        *已签到*|*已经签到*|*Already*|*already*)
            return 0
            ;;
    esac

    return 1
}

run_account() {
    local index="$1"
    local mode="$2"
    local account_user_id="$3"
    local secret="$4"
    local account_url="$5"
    local checkin_status

    set_account_context "$mode" "$account_user_id" "$secret" "$account_url"

    if [ "$ACCOUNT_COUNT" -gt 1 ]; then
        ui_print "----- 用户 ${index}/${ACCOUNT_COUNT} 开始 -----"
    fi
    ui_print "ID：$USER_ID"
    ui_print "接口：$BASE_URL"
    ui_print "认证：$([ "$AUTH_MODE" = "cookie" ] && echo "Cookie" || echo "Token")"
    ui_print ""

    do_checkin
    checkin_status=$?
    ui_print ""

    if [ "$checkin_status" -eq 0 ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        ui_print "用户 ${USER_ID} 任务成功"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        ui_print "用户 ${USER_ID} 任务失败"
    fi

    if [ "$ACCOUNT_COUNT" -gt 1 ]; then
        ui_print "----- 用户 ${index}/${ACCOUNT_COUNT} 结束 -----"
        ui_print ""
    fi
}

build_accounts || exit 1

ui_print "===== 每日任务开始 ====="
ui_print "获取到${ACCOUNT_COUNT}个用户"
ui_print "时间：$(date '+%Y-%m-%d %H:%M:%S')"
ui_print ""

CURRENT_INDEX=1
while IFS='|' read -r account_mode account_user_id account_secret account_url; do
    [ -z "$account_mode" ] && continue
    run_account "$CURRENT_INDEX" "$account_mode" "$account_user_id" "$account_secret" "$account_url"
    CURRENT_INDEX=$((CURRENT_INDEX + 1))
done <<EOF
$ACCOUNTS
EOF

SUCCESS_RATE=$(awk "BEGIN { if ($ACCOUNT_COUNT <= 0) printf \"0.00\"; else printf \"%.2f\", $SUCCESS_COUNT * 100 / $ACCOUNT_COUNT }")

print_all_user_info
ui_print ""
ui_print "共${ACCOUNT_COUNT}个用户成功${SUCCESS_COUNT}个失败${FAIL_COUNT}个 ${SUCCESS_RATE}%"
ui_print "===== 任务结束 ====="
