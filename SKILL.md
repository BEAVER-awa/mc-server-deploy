---
name: mc-server-deploy
description: 从零部署 Minecraft Java 版服务器并接入 MCSManager 面板管理的完整流程，覆盖 Java 版本判定、MCSManager（含国内网络绕行）、NAT 转发/安全组开端口、实例注册、启动验证与崩溃排查。当用户提出「开个 MC 服」「搭 Minecraft 服务器」「装 MCSManager」「服务端起不来 / 一直崩」「玩家连不上」等需求时使用。
---

# Minecraft 服务器部署（通用流程）

## 用途

把一台 Linux 云主机变成可用的 MC Java 版服务器：装对 Java、装面板、开对端口、把服务端注册成面板实例、并且**用真实协议握手验证**而不是只看日志说"应该没问题"。

## 开工前必须问清的 4 件事（一次问完，别分批问）

1. **版本与加载器**：MC 版本号（如 1.21.4 / 26.2）+ 加载器（Vanilla / Fabric / Forge / NeoForge）。这决定 Java 版本和启动命令。
2. **网络形态**：公网直连（有独立公网 IP / 弹性 IP）还是 **NAT 型**（内网 IP + 公网 IP 不同，端口靠控制台转发）。这决定开端口怎么做，是最常见的返工点。
3. **机器规格**：CPU 核数、内存、磁盘分区。决定了堆大小和「服务端放哪个盘」。
4. **是否已有服务端文件夹要迁移**（有的话先做容量核对，见 `references/migrate-existing.md`）。

## 步骤 1：确认 Java 版本（最容易错的一步）

**不要按 MC 版本号猜 Java 版本。** 直接读服务端 jar 里 class 的字节码 major 版本：

```bash
# 从 server.jar 里取一个核心类，读第 7-8 字节
unzip -p server.jar net/minecraft/server/MinecraftServer.class | od -An -tu1 -j6 -N2
# 输出形如 0 69  → major = 69*256 + 0 的算法见下表；实际 major = 69
```

major → Java 对照（完整表与探测脚本见 `references/java-version.md`）：`61=Java 17`、`65=Java 21`、`69=Java 25`。

装 JDK 的要点：

- Ubuntu 22.04 的 apt **没有** openjdk-25；Adoptium 官方 API 会 302 跳 GitHub（国内常不通）。
- 走清华镜像：`https://mirrors.tuna.tsinghua.edu.cn/Adoptium/<major>/jdk/x64/linux/`
- 装到 `/opt/java/jdk-<ver>/`，软链 `/usr/bin/java`、`/usr/bin/javac`，这样面板和 `bash -lc` 里都能直接 `java`。

## 步骤 2：装 MCSManager

细节、参数、以及三个必踩的坑见 `references/mcsm-install.md`。要点：

- 官方脚本 `https://script.mcsmanager.com/setup.sh`，装到 `/opt/mcsmanager`（自带 Node）。
- **`--install-source` 参数脚本解析了但代码里没用**，仍会去 GitHub 拉 37 MB；国内 ~220 KB/s 等于 4 小时。要么 patch 脚本读本地包，要么先把包用镜像下好。
- daemon 默认监听 `0.0.0.0:24444` 且是**无鉴权 RPC**，务必改成 `127.0.0.1`（改 `daemon/data/Config/global.json` 的 `ip`），只让本机面板访问。

## 步骤 3：开端口（先分清是安全组还是 NAT）

| 现象 | 类型 | 做法 |
|---|---|---|
| 机器 `ip a` 显示的就是控制台里那个公网 IP | 直连 / 弹性 IP | 云控制台**安全组**放行端口 |
| 机器只有内网 IP（如 `172.16.x.x`），公网 IP 在网关 | **NAT 型** | 控制台「NAT 转发」逐条加 `外部端口 → 内部端口` |

必须开的端口：

| 端口 | 用途 | 备注 |
|---|---|---|
| `23333/tcp` | MCSManager 网页面板 | 建议把外部端口换成好记的（如 20034） |
| `25565/tcp` | MC 游戏端口 | 内部端口跟着 `server.properties` 的 `server-port` 走 |
| `22/tcp`（或映射端口） | SSH | 通常在装系统时已给 |
| `24444/tcp` | daemon 内部通信 | **不要对外开** |

**判断是否生效的唯一正确方法**：从**另一台机器**上去连。NAT 型机器在自己机内 `curl 公网IP:端口` 一定失败（无 hairpin NAT），那不是没配好。

同一公网 IP 上如果有别的服务占着某端口（例如 `25565` 回了另一个代理端），玩家会连到别人的服务。用 `scripts/mc_ping.py` 一测就知道端口后面到底是谁。

## 步骤 4：把服务端注册成面板实例

MCSManager 的 daemon **没有对外 HTTP API**（`/api/*` 全部 404），别浪费时间试探。可靠做法是直接写实例配置文件再重启 daemon：

1. 写 `/opt/mcsmanager/daemon/data/InstanceConfig/<uuid>.json`（字段模板见 `references/instance-config.md`）
2. `systemctl restart mcsm-daemon`
3. daemon 启动时会把该目录下所有配置加载进来，`eventTask.autoStart=true` 的会被自动拉起

字段上的三个硬要求：

- `stopCommand` 必须是游戏内命令（MC 就是 `stop`），**不要用 kill**，否则世界不落盘。
- `cwd` 指向服务端根目录（`server.jar` / 启动脚本所在处）。
- `type` 用 `universal`，配合完整命令行最省事。

## 步骤 5：验证（必须做完整的三层）

1. **进程与端口**：`systemctl is-active mcsm-web mcsm-daemon`、`ss -lntp | grep 25565`
2. **日志**：实例日志在 `/opt/mcsmanager/daemon/data/InstanceLog/<uuid>.log`，看 `Done (x.xxxs)!` 和 `ERROR` 计数
3. **真实协议握手**：`python scripts/mc_ping.py <host> <port>` —— 能证明「端口是通的」且「后面确实是 MC 服务端」，还能拿到版本号和在线人数。telnet/`/dev/tcp` 只能证明 TCP 通，证明不了后面是谁。

## 步骤 6：起不来怎么办

先看 `crash-reports/` 最新一份 + 实例日志，再对 `references/troubleshoot.md` 里的模式表排。高频四类：

- `UnsupportedClassVersionError` → Java 版本低于 jar 要求
- `HikariPool$PoolInitializationException` / `Communications link failure` → 某个插件（Ledger 等）配了 MySQL 但机器上没有数据库
- `Incompatible mod set` / `requires ... which is missing` → mod 依赖缺失或版本不匹配
- 端口被占 / 世界被两个进程同时打开 → 检查是不是有人用 tmux/screen 又起了一份

## 工具

| 脚本 | 作用 |
|---|---|
| `scripts/mc_ping.py` | MC 协议 status ping，输出版本/协议号/在线数；用于验证端口后面到底是谁 |
| `scripts/ssh_run.py` | 用 paramiko 把一批命令推到远端执行（密码从环境变量 `SSHPW` 读，不落盘），适合反复排障 |

## 参考

| 文件 | 内容 |
|---|---|
| `references/java-version.md` | 字节码 major → Java 对照表、探测命令、镜像安装命令 |
| `references/mcsm-install.md` | MCSManager 安装全过程与三个坑的绕法 |
| `references/instance-config.md` | daemon 实例配置 JSON 完整模板与字段含义 |
| `references/troubleshoot.md` | 崩溃/连不上 的排查模式表 |
| `references/migrate-existing.md` | 迁移已有服务端（大文件夹传输、容量核对、0 字节文件陷阱） |
