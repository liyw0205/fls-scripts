# FLS 在线脚本源说明

这是一个适用于 **FLS 面板** 的在线脚本源 `index.json` 示例。  
FLS 面板可以通过该 JSON 读取可安装脚本列表，并支持一键拉取、安装、导入任务、编辑配置和定时运行。

---

## 脚本源地址

在 FLS 面板中进入：

```text
配置 -> 在线脚本源
```

填写你的 `index.json` 地址，例如：

```text
https://cdn.jsdelivr.net/gh/liyw0205/fls-scripts@main/index.json
```

然后进入：

```text
在线脚本 -> 刷新远程脚本源
```

即可加载脚本列表。

---

## 当前包含脚本

| ID | 名称 | 类型 | 说明 |
|---|---|---|---|
| `caiyun` | 中国移动云盘 | `repo` | 拉取仓库运行移动云盘签到 |
| `chinaUnicom` | 中国联通 | `raw` | 单文件 Python 脚本 |
| `kg` | 酷狗音乐签到 | `repo` | 酷狗签到 / 扫码 |
| `cloud189checkin` | 天翼云盘自动签到 | `repo` | 天翼云盘签到 |
| `checkbox` | 签到盒 checkbox | `repo` | 集合型签到仓库，通过 `task_link` 加载任务列表 |

---

# 脚本源字段说明

每个脚本项支持如下字段。

## 基础字段

```json
{
  "id": "checkbox",
  "name": "签到盒 checkbox",
  "type": "repo",
  "link": "https://github.com/Wenmoux/checkbox.git",
  "link_name": "checkbox",
  "doc_link": "https://cdn.jsdelivr.net/gh/Wenmoux/checkbox@master/README.md",
  "install": "cd checkbox\nnpm install",
  "task_cron": {},
  "task_link": "",
  "created_at": "2026-05-07 00:00:00",
  "updated_at": "2026-05-07 00:00:00"
}
```

---

## `id`

脚本唯一标识。

示例：

```json
"id": "checkbox"
```

要求：

- 建议只使用英文、数字、下划线、中划线；
- 同一个脚本源中不能重复；
- 用于识别在线脚本、避免重复导入任务。

---

## `name`

脚本显示名称。

示例：

```json
"name": "签到盒 checkbox"
```

---

## `type`

脚本类型，目前支持：

```text
raw
repo
```

### `raw`

单文件脚本。

示例：

```json
"type": "raw",
"link": "https://github.com/xxx/xxx/raw/main/demo.py",
"link_name": "demo.py"
```

FLS 会把文件下载到：

```text
scripts/demo.py
```

适合：

- 单个 `.py`
- 单个 `.js`
- 单个 `.sh`

---

### `repo`

Git 仓库。

示例：

```json
"type": "repo",
"link": "https://github.com/Wenmoux/checkbox.git",
"link_name": "checkbox"
```

FLS 会把仓库克隆到：

```text
scripts/checkbox
```

适合：

- Node.js 项目；
- Python 项目；
- 有多个文件依赖的项目；
- 需要 `package.json` / `requirements.txt` / 配置文件的项目；
- 集合型脚本仓库。

---

## `link`

脚本地址。

### raw 示例

```json
"link": "https://github.com/liyw0205/fls-scripts/raw/refs/heads/main/scripts/chinaUnicom/chinaUnicom.py"
```

### repo 示例

```json
"link": "https://github.com/Wenmoux/checkbox.git"
```

---

## `link_name`

保存名称。

### raw

```json
"link_name": "chinaUnicom.py"
```

最终保存为：

```text
scripts/chinaUnicom.py
```

### repo

```json
"link_name": "checkbox"
```

最终保存为：

```text
scripts/checkbox
```

---

## `doc_link`

文档地址。

示例：

```json
"doc_link": "https://cdn.jsdelivr.net/gh/Wenmoux/checkbox@master/README.md"
```

FLS 在线脚本页支持查看文档。

支持：

- Markdown；
- 普通文本；
- 网页链接。

---

## `install`

安装命令。

脚本下载安装到 `scripts` 目录后执行。

示例：

```json
"install": "cd checkbox || exit 1\nnpm install"
```

适合做：

- 安装依赖；
- 初始化配置；
- 首次复制配置模板；
- 创建默认文件。

---

# `task_cron` 任务说明

`task_cron` 用于安装脚本后导入 FLS 任务。

支持单个对象：

```json
"task_cron": {
  "name": "中国联通任务",
  "cron": "30 9,16 * * *",
  "command": "task chinaUnicom.py"
}
```

也支持数组：

```json
"task_cron": [
  {
    "name": "酷狗音乐签到",
    "cron": "30 8 * * *",
    "command": "cd kgcheckin || exit 1\nnpm run main"
  },
  {
    "name": "酷狗音乐扫码",
    "cron": "30 20 * * *",
    "command": "cd kgcheckin || exit 1\nnpm run qrcodeLogin"
  }
]
```

---

## `task_cron.name`

导入后的任务名称。

```json
"name": "中国移动云盘签到"
```

---

## `task_cron.cron`

定时表达式。

示例：

```json
"cron": "30 9,16,23 * * *"
```

表示每天：

```text
09:30
16:30
23:30
```

FLS 支持：

### 5 位 Cron

```text
分 时 日 月 周
```

示例：

```text
30 8 * * *
```

### 6 位 Cron

```text
秒 分 时 日 月 周
```

示例：

```text
0 30 8 * * *
```

---

## `task_cron.command`

任务命令。

示例：

```json
"command": "task chinaUnicom.py"
```

或者：

```json
"command": "cd checkbox || exit 1\nnode checkbox.js aliyun"
```

---

# FLS 的 `task` 命令说明

如果命令是：

```sh
task chinaUnicom.py
```

FLS 会自动从 `scripts` 目录查找：

```text
scripts/chinaUnicom.py
```

并根据后缀选择运行器。

例如：

| 命令 | 实际运行 |
|---|---|
| `task test.py` | Python |
| `task run.mjs` | Node.js |
| `task demo.sh` | Bash |

---

# `config_path` 配置文件说明

任务支持：

```json
"config_path": "checkbox/config.yml"
```

表示该任务有一个可编辑配置文件。

FLS 会在任务列表显示：

```text
配置
```

点击后可编辑：

```text
scripts/checkbox/config.yml
```

---

## 示例：移动云盘

```json
"config_path": "caiyun_box/asign.json"
```

对应文件：

```text
scripts/caiyun_box/asign.json
```

安装时会自动执行：

```sh
cd caiyun_box
if [ ! -f asign.json ]; then
  cp default_asign.json asign.json
fi
```

所以用户安装后只需要点击任务列表的：

```text
配置
```

编辑 `asign.json` 即可。

---

## 示例：签到盒

```json
"config_path": "checkbox/config.yml"
```

对应文件：

```text
scripts/checkbox/config.yml
```

安装时会自动执行：

```sh
cd checkbox || exit 1
npm install
npm install cheerio
if [ ! -f config.yml ]; then
  cp config.yml.temple config.yml
  echo "已生成 config.yml"
else
  echo "config.yml 已存在，不覆盖"
fi
```

这样第一次安装会自动生成：

```text
checkbox/config.yml
```

以后不会覆盖用户配置。

---

# `var` 任务变量说明

`task_cron` 可选字段：

```json
"var": {
  "chinaUnicomCookie": "a3e4c1ff2xxxxxxxxx"
}
```

导入任务后，会成为该任务的环境变量。

适合：

- Cookie；
- Token；
- 账号密码；
- 单脚本环境变量。

示例：

```json
{
  "name": "中国联通任务",
  "cron": "30 9,16 * * *",
  "command": "task chinaUnicom.py",
  "config_path": "unicom_token_cache.json",
  "var": {
    "chinaUnicomCookie": "a3e4c1ff2xxxxxxxxx"
  }
}
```

---

# `task_link` 外部任务列表说明

对于 `checkbox` 这种集合型仓库，不适合把大量任务都塞进主 `index.json`。

因此支持：

```json
"task_link": "https://cdn.jsdelivr.net/gh/liyw0205/fls-scripts@main/scripts/checkbox/tasks.json"
```

`task_link` 指向一个独立任务文件。

---

## `task_link` 适合什么场景

适合：

- 一个仓库里有很多子任务；
- 任务列表很长；
- 想单独维护任务；
- 不想让主 `index.json` 太大。

例如：

```text
checkbox
├── checkbox.js
├── Template.js
├── sendmsg.js
├── package.json
└── scripts/
    ├── aliyun.js
    ├── quark.js
    ├── hifini.js
    └── ...
```

主脚本源只写：

```json
{
  "id": "checkbox",
  "name": "签到盒 checkbox",
  "type": "repo",
  "link": "https://github.com/Wenmoux/checkbox.git",
  "link_name": "checkbox",
  "install": "...",
  "task_link": "https://xxx/tasks.json"
}
```

任务单独写在：

```text
scripts/checkbox/tasks.json
```

---

# `tasks.json` 格式

`task_link` 指向的 JSON 推荐格式：

```json
{
  "name": "签到盒 checkbox 任务列表",
  "version": "1.0.0",
  "tasks": [
    {
      "name": "签到盒 - 阿里云盘",
      "cron": "10 8 * * *",
      "command": "cd checkbox || exit 1\nnode checkbox.js aliyun",
      "config_path": "checkbox/config.yml"
    }
  ]
}
```

也支持直接数组：

```json
[
  {
    "name": "签到盒 - 阿里云盘",
    "cron": "10 8 * * *",
    "command": "cd checkbox || exit 1\nnode checkbox.js aliyun",
    "config_path": "checkbox/config.yml"
  }
]
```

---

# 当前 `index.json` 示例

```json
[
  {
    "id": "caiyun",
    "name": "中国移动云盘",
    "type": "repo",
    "link": "https://github.com/liyw0205/caiyun",
    "link_name": "caiyun_box",
    "doc_link": "https://cdn.jsdelivr.net/gh/liyw0205/caiyun@main/README.md",
    "install": "cd caiyun_box\nif [ ! -f asign.json ]; then\n  cp default_asign.json asign.json\n  echo \"已生成 asign.json\"\nelse\n  echo \"asign.json 已存在，不覆盖\"\nfi",
    "task_cron": {
      "name": "中国移动云盘签到",
      "cron": "30 9,16,23 * * *",
      "command": "task caiyun_box/run.mjs",
      "config_path": "caiyun_box/asign.json"
    },
    "created_at": "2026-05-07 00:00:00",
    "updated_at": "2026-05-07 00:00:00"
  },
  {
    "id": "chinaUnicom",
    "name": "中国联通",
    "type": "raw",
    "link": "https://github.com/liyw0205/fls-scripts/raw/refs/heads/main/scripts/chinaUnicom/chinaUnicom.py",
    "link_name": "chinaUnicom.py",
    "doc_link": "https://cdn.jsdelivr.net/gh/liyw0205/fls-scripts@main/scripts/chinaUnicom/README.md",
    "install": "${FLS_PYTHON:-python3} -m pip install pycryptodome",
    "task_cron": {
      "name": "中国联通任务",
      "cron": "30 9,16 * * *",
      "command": "task chinaUnicom.py",
      "config_path": "unicom_token_cache.json",
      "var": {
        "chinaUnicomCookie": "a3e4c1ff2xxxxxxxxx"
      }
    },
    "created_at": "2026-05-07 00:00:00",
    "updated_at": "2026-05-07 00:00:00"
  },
  {
    "id": "checkbox",
    "name": "签到盒 checkbox",
    "type": "repo",
    "link": "https://github.com/Wenmoux/checkbox.git",
    "link_name": "checkbox",
    "doc_link": "https://cdn.jsdelivr.net/gh/Wenmoux/checkbox@master/README.md",
    "install": "cd checkbox || exit 1\nnpm install\nnpm install cheerio\nif [ ! -f config.yml ]; then\n  cp config.yml.temple config.yml\n  echo \"已生成 config.yml\"\nelse\n  echo \"config.yml 已存在，不覆盖\"\nfi",
    "task_link": "https://cdn.jsdelivr.net/gh/liyw0205/fls-scripts@main/scripts/checkbox/tasks.json",
    "created_at": "2026-05-07 00:00:00",
    "updated_at": "2026-05-07 00:00:00"
  }
]
```

---

# 使用流程

## 1. 配置脚本源

进入 FLS 面板：

```text
配置 -> 在线脚本源
```

填写 `index.json` 地址。

---

## 2. 刷新脚本源

进入：

```text
在线脚本 -> 刷新远程脚本源
```

---

## 3. 安装脚本

在在线脚本页面选择脚本，点击：

```text
下载安装
```

如果该脚本有任务，可以勾选：

```text
导入任务
```

---

## 4. 编辑配置

安装并导入任务后，进入：

```text
任务管理
```

如果任务有 `config_path`，会显示：

```text
配置
```

点击后编辑配置文件。

例如：

```text
checkbox/config.yml
```

---

## 5. 运行任务

可以手动运行，也可以等待 Cron 自动执行。

---

# 配置文件示例

## `checkbox/config.yml`

```yaml
needPush: false
cbList: aliyun&quark&hifini

aliyun:
  refresh_token: "你的阿里云盘 refresh_token"

quark:
  cookie:
    - "你的夸克 cookie"

hifini:
  cookie: "你的 HiFiNi cookie"

Push:
  sckey: ""
  qmsgkey: ""
  pushplustoken: ""
  qywx:
    corpsecret: ""
    corpid: ""
    agentid: ""
    mediaid: ""
  tgpushkey:
    tgbotoken: ""
    chatid: ""
  vocechat:
    api: ""
    uid: ""
    key: ""
```

---

# 注意事项

## 1. repo 项目命令需要先进入目录

例如：

```sh
cd checkbox || exit 1
node checkbox.js aliyun
```

不要直接写：

```sh
node checkbox.js aliyun
```

因为任务默认工作目录是：

```text
scripts
```

而 `checkbox.js` 在：

```text
scripts/checkbox/checkbox.js
```

---

## 2. `config_path` 是相对 `scripts` 的路径

正确：

```json
"config_path": "checkbox/config.yml"
```

错误：

```json
"config_path": "/root/fls/scripts/checkbox/config.yml"
```

FLS 只允许编辑 `scripts` 目录下的文件，避免路径越权。

---

## 3. 安装命令不要覆盖用户配置

推荐写法：

```sh
if [ ! -f config.yml ]; then
  cp config.yml.temple config.yml
else
  echo "config.yml 已存在，不覆盖"
fi
```

不要写：

```sh
cp config.yml.temple config.yml
```

否则每次安装都会覆盖用户配置。

---

## 4. `task_link` 加载失败不应影响主脚本源

如果 `task_link` 无法访问，FLS 应只提示该任务源加载失败，不应导致整个 `index.json` 失效。

---

## 5. `raw` 单文件适合简单脚本

如果脚本依赖多个文件，推荐使用：

```json
"type": "repo"
```

不要强行拆成 `raw`。

---

# 推荐目录结构

```text
fls-scripts/
├── index.json
└── scripts/
    ├── chinaUnicom/
    │   ├── chinaUnicom.py
    │   └── README.md
    └── checkbox/
        └── tasks.json
```

---

# 维护建议

1. 主 `index.json` 只放项目级信息；
2. 集合型仓库用 `task_link` 拆任务；
3. 有配置文件的任务统一写 `config_path`；
4. 安装命令负责初始化默认配置；
5. 用户配置不要放进脚本源；
6. Cookie / Token 示例必须脱敏；
7. 不要在脚本源里写真实账号、真实密码、真实 Cookie。

---

# 免责声明

本脚本源仅供学习和自动化管理个人脚本使用。  
请勿用于任何违反目标网站服务条款、法律法规或侵犯他人权益的用途。