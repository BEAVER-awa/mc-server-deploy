# 排障模式表

先定位证据，再动手：

```bash
# 面板实例日志（最全，含 stderr）
tail -100 /opt/mcsmanager/daemon/data/InstanceLog/<uuid>.log
# 服务端自己的日志
tail -100 <cwd>/logs/latest.log
# 崩溃报告（有则说明是 JVM 级崩溃，信息最完整）
ls -t <cwd>/crash-reports/ | head -3
```

## 崩溃 / 起不来

| 日志特征 | 原因 | 处理 |
|---|---|---|
| `UnsupportedClassVersionError` / `compiled by a more recent version` | Java 版本低于 jar 要求 | 读字节码 major 选 JDK（见 java-version.md） |
| `HikariPool$PoolInitializationException: Communications link failure` | 某插件（Ledger / LuckPerms / 经济插件）配了 MySQL，机器上没库 | `apt install mariadb-server`，按插件配置建库建账号；或把插件存储改成 SQLite/H2 |
| `Incompatible mod set` / `requires ... which is missing` | mod 依赖缺失/版本不匹配 | 按提示补前置 mod 或降版本 |
| `java.lang.OutOfMemoryError: Java heap space` | 堆太小 | 提 `-Xmx`，同时确认机器实际内存够（留 1–2 GB 给系统） |
| `Failed to bind to port` | 端口被占 | `ss -lntp \| grep <port>` 找到占用者；常见是残留的手工进程 |
| `You need to agree to the EULA` | 未接受 | `<cwd>/eula.txt` 改 `eula=true` |
| `session.lock` / `world is already locked` | 两个进程开同一个世界 | 杀掉多余进程（tmux/screen/nohup + 面板实例并存） |
| `Unsupported major.minor` 出现在某个 mod | mod 编译目标高于当前 Java | 换 mod 版本或升 Java |
| 启动几十秒后无故退出、无 ERROR | 被 OOM killer 干掉 | `dmesg -T \| grep -i killed`；减内存或加 swap |

## 连不上

| 现象 | 排查顺序 |
|---|---|
| 端口 TCP 都不通（超时） | ① NAT 转发/安全组是否放行 ② 是否从**外部**机器测的（机内测公网 IP 必失败） ③ `ss -lntp` 是否有监听 |
| TCP 通但 MC 客户端报「连接被重置 / 无法连接」 | 用 `mc_ping.py` 看响应：能拿到版本=服务端正常，问题在客户端（mod 不匹配、协议版本不同） |
| `mc_ping.py` 返回的版本/在线数和预期不符 | **端口后面是别的服务**（同 IP 上另一个代理/另一台机），换端口或改转发目标 |
| 能进服但一直卡在「登录」 | 验证插件（EasyAuth/AuthMe）问题：看日志是否在等 `/login`；检查 `online-mode` 与插件模式是否匹配 |
| 进服后被踢：`Invalid session` | `online-mode=true` + 盗版客户端；或 EasyAuth 的 `premium-auto-login` 与 `online-mode` 组合不当 |

## 卡顿

```bash
# 服务端内：/spark tps、/spark profiler（若装了 spark）
top -H -p <pid>            # 看线程
iostat -x 1 3              # 磁盘 IO（区块加载慢常见）
```

- `view-distance` / `simulation-distance` 调小是最有效的止血手段。
- `sync-chunk-writes=false` 能明显降低存档卡的 IO 压力。
- 大量实体（掉落物、村民）优先用清理插件处理。

## 一条经验

**别把「日志没报错」当成「服务正常」。** 判断服务可用只有两个硬指标：端口在监听 + 真实协议握手成功。日志干净但玩家连不上，八成是端口转发或 mod 客户端不匹配。
