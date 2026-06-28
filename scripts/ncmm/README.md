# ncmm（FLS 集成）

[ncmm](https://github.com/3899/ncmm) 是基于 Go 的**网易云音乐人助手**：日常签到（云贝、黑胶 VIP）、模拟刷歌、音乐人进阶任务、乐迷团等，配置见 `config.yaml`。

本目录为 **FLS 面板** 包装脚本，不 fork 上游仓库；安装时克隆 `3899/ncmm` 到 `scripts/ncmm/`，再由任务拉取 Release 二进制与 `fls/*.sh`。

## 与现有 Python 脚本的关系

| 项目 | 说明 |
|------|------|
| `netease_music_checkin`（raw） | 轻量签到 + 刷歌，适合普通听歌等级 |
| **ncmm**（repo） | 音乐人 / 云贝 / VIP / 乐迷团 / 多账号接力，功能更重 |

可按需只装其一，或同时安装（注意刷歌频率与风控）。

## 首次使用

1. 在 FLS **在线脚本** 安装「ncmm 网易云音乐人助手」。
2. 运行任务 **ncmm - 安装/更新二进制与配置**（手动一次）。
3. 在任务变量填写 `NETEASE_COOKIE`（推荐，须含 `MUSIC_U=`），或安装后 SSH/终端进 `scripts/ncmm` 执行 `./ncmm login qrcode -m`。
4. 面板编辑 **配置** → `ncmm/config.yaml`（任务开关、播放上限、辅账号路径等）。
5. 定时运行 **ncmm - 一键批量任务** 或拆分 `sign` / `musician` / `fansgroup`。

## Cookie 多账号

与 `scripts/neteaseMusic` 一致：多账号用 `#MUSIC_U=` 衔接下一段，**不要**用裸 `#` 切整段 Cookie。

```text
MUSIC_U=aaa; __csrf=...#MUSIC_U=bbb; __csrf=...
```

第一段导入主账号（`-m`），其余写入 `fan2.json`、`fan3.json` 等（需在 `config.yaml` 的 `accounts.secondary` 中配置路径）。

## 上游文档

- [命令行说明](https://github.com/3899/ncmm/blob/main/docs/cli.md)
- [配置文件](https://github.com/3899/ncmm/blob/main/docs/configuration.md)

## FLS 面板项目

面板本体：[liyw0205/fls](https://github.com/liyw0205/fls)（Flask Lightweight Script Manager）。

脚本源维护仓库：[liyw0205/fls-scripts](https://github.com/liyw0205/fls-scripts)。

## 架构与二进制

Release [v1.1.7](https://github.com/3899/ncmm/releases/tag/v1.1.7) 提供 `Linux_arm64` / `Linux_armv6` / `Linux_x86_64`。Termux 多为 `aarch64` → `Linux_arm64`。

## 免责声明

仅供学习研究；使用须遵守网易云服务条款，风险自负。上游 [免责声明](https://github.com/3899/ncmm#%EF%B8%8F-%E5%85%8D%E8%B4%A3%E5%A3%B0%E6%98%8E) 同样适用。