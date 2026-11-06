# MCSManager 安装（国内网络环境）

## 目标形态

- 代码在 `/opt/mcsmanager`，自带 Node（`node-vXX-linux-x64`），不动系统 node。
- 两个 systemd 服务：`mcsm-web`（面板，默认 `23333`）、`mcsm-daemon`（节点，默认 `24444`）。
- 两个都 `enable + active`，开机自启。

## 标准步骤

```bash
# 1) 拿官方脚本，先看再执行
curl -fsSL https://script.mcsmanager.com/setup.sh -o /tmp/mcsm_setup.sh
less /tmp/mcsm_setup.sh        # 至少确认下载地址与写入路径

# 2) 执行（必须在后台跑，原因见坑 3）
setsid nohup bash /tmp/mcsm_setup.sh > /tmp/mcsm_install.log 2>&1 &
tail -f /tmp/mcsm_install.log
```

装完后：

```bash
systemctl status mcsm-web mcsm-daemon --no-pager | head -20
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:23333/    # 期望 200
ss -lntp | grep -E "23333|24444"
```

## 坑 1：`--install-source` 是摆设

脚本会解析 `--install-source <本地包>` 参数并赋值给 `install_source_path`，但**后面的下载逻辑根本不引用这个变量**，仍然去 `wget` GitHub Release。国内 220 KB/s 拉 37 MB 要 4 小时。

绕法一（推荐）：先把包用镜像下好，再 patch 脚本

```bash
# ghfast.top 前缀镜像 + 断点续传
curl -L -C - -o /tmp/mcsmanager_linux_release.tar.gz \
  "https://ghfast.top/https://github.com/MCSManager/MCSManager/releases/download/v10.22.1/mcsmanager_linux_release.tar.gz"
gzip -t /tmp/mcsmanager_linux_release.tar.gz     # 校验完整性

# 在脚本里把下载那段替换成本地文件（先 grep 找到 wget/curl 那行）
sed -i 's#^\(\s*\)wget .*mcsmanager.*#\1cp /tmp/mcsmanager_linux_release.tar.gz ./mcsmanager_linux_release.tar.gz#' /tmp/mcsm_setup.sh
```

绕法二：改用 `install_source` 相关分支（不同版本脚本行为不一致，需先 `grep -n install_source` 确认）。

## 坑 2：npm 依赖慢

```bash
export npm_config_registry=https://registry.npmmirror.com
```

或把 registry 写进 `/opt/mcsmanager/web/.npmrc` 与 `/opt/mcsmanager/daemon/.npmrc`。web 约 560 包（几秒），daemon 约 620 包（1–2 分钟）。

## 坑 3：安装脚本吞掉 SSH 会话输出

脚本内部会读 stdin（交互提示/`read`），通过 `ssh host "bash script.sh"` 方式执行时会把外层会话的输入流吃掉，表现为**命令执行了但一个字都不输出**，还会留下孤儿进程互相抢锁。

- 一律用 `setsid nohup ... > log 2>&1 &` + 轮询日志。
- 已经出现幽灵进程时：`ps aux | grep -i mcsm` 找出来 `kill`，再重跑。

## 装完必做的安全加固

`/opt/mcsmanager/daemon/data/Config/global.json`：

```json
{ "ip": "127.0.0.1", "port": 24444, "key": "<自动生成>" }
```

把 `ip` 从 `0.0.0.0` 改成 `127.0.0.1`，再 `systemctl restart mcsm-daemon`。daemon 的 RPC 只有 apikey 保护，暴露公网等于把机器交出去。

改完验证：

```bash
ss -lntp | grep 24444      # 应为 127.0.0.1:24444
```

面板侧不需要改任何东西（web 与 daemon 同机，走回环）。

## 首次登录

面板没有初始账号，首次访问会引导创建管理员。**不要用 admin/123456**，面板一旦映射到公网就是入口。

语言默认 `en_us`，登录后设置里可改 `zh_cn`。
