# mc-server-deploy

一套经过实战验证的 **Minecraft Java 版服务器部署技能包**：从零把一台 Linux 云主机变成可用的 MC 服务器，并接入 [MCSManager](https://mcsmanager.com/) 面板管理。

源自一次真实的部署实战（30 GB 存档跨机迁移、MC 26.2 / Java 25、NAT 型云主机），记录的不是"应该怎么做"，而是**实际会踩哪些坑、怎么绕**。

## 覆盖范围

- **Java 版本判定** —— 不按 MC 版本号猜，直接读 jar 内 class 的字节码 major 版本（`61=17`、`65=21`、`69=25`），含国内镜像安装路径
- **MCSManager 安装** —— 官方脚本三个必踩坑的绕法（`--install-source` 参数是假的、脚本吞 SSH 输出、GitHub release 下载极慢）
- **开端口** —— 分清"安全组放行" vs "NAT 转发"，以及 NAT 机器上 `curl 公网IP` 必然失败的误区
- **实例注册** —— daemon 没有对外 API，直接写实例配置文件 + 重启 daemon 的可靠做法
- **三层验证** —— 进程/端口 → 日志 → 真实 MC 协议握手（带版本号和在线人数）
- **崩溃排查** —— 高频故障模式表：`UnsupportedClassVersionError`、插件缺 MySQL、mod 依赖缺失、双进程抢世界
- **存量服务端迁移** —— 大文件夹传输、容量核对、以及"0 字节文件被误判已传"的陷阱

## 目录结构

```
SKILL.md                      主流程（六步）
references/
  java-version.md             字节码 major → Java 对照、镜像安装
  mcsm-install.md             MCSManager 安装与三个坑
  instance-config.md          daemon 实例配置 JSON 模板
  troubleshoot.md             崩溃/连不上 排查模式表
  migrate-existing.md         存量服务端迁移
scripts/
  mc_ping.py                  MC 协议 status ping（零依赖，标准库实现）
  ssh_run.py                  paramiko 批量远程执行（密码走环境变量，不落盘）
```

## 脚本用法

```bash
# 探测某端口后面到底是谁（能区分 MC 服务端 / Velocity 代理 / 其他）
python scripts/mc_ping.py <host> <port>

# 批量在远端执行命令（密码不落盘）
SSHPW=<密码> python scripts/ssh_run.py -H <host> -p <port> -u root \
  -c "systemctl is-active mcsm-web mcsm-daemon" \
  -c "ss -lntp | grep 25565"
```

## 作为技能包使用

本包遵循 [Agent Skills](https://github.com/anthropics/skills) 的 `SKILL.md` 约定。把本目录放进支持该约定的 AI 助手技能目录，当对话中出现「开个 MC 服」「搭 Minecraft 服务器」「装 MCSManager」「服务端起不来」「玩家连不上」等需求时会被自动命中。即使不接 AI 助手，`SKILL.md` 和 `references/` 本身也是一份可直接照做的部署手册。

## 安全要点

- daemon 默认监听 `0.0.0.0:24444` 且为**无鉴权 RPC**，务必改成仅 `127.0.0.1`（技能内有步骤）
- `stopCommand` 必须用游戏内命令（MC 为 `stop`），不要 kill，否则世界不落盘
- 判断端口是否放行，唯一正确方法是从**另一台机器**去连

## License

[MIT](LICENSE)
