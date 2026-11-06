# 把服务端注册成 MCSManager 实例

## 为什么不走 API

MCSManager 10.x 的 daemon 只对**面板**提供内部 RPC，**没有对外开放的 HTTP API**：`/api/overview`、`/api/instance`、`/api/instances` 等路径一律 `404 Not Found`（`GET /` 会返回 daemon 自带的前端页面，别被 200 误导）。

可靠路径：**直接写配置文件 → 重启 daemon**。daemon 启动时会遍历 `data/InstanceConfig/*.json` 并全部加载。

## 操作步骤

```bash
# 1) 先优雅停掉任何手工起的进程（tmux/screen/nohup），避免两个进程抢同一个世界
tmux send-keys -t mc "stop" Enter
while pgrep -f fabric-server-launch >/dev/null; do sleep 1; done

# 2) 生成配置（python 拼 JSON 最省心，避免手写引号出错）
python3 /tmp/mk_instance.py

# 3) 重启 daemon，它会加载新实例并按 autoStart 自动拉起
systemctl restart mcsm-daemon
sleep 10
tail -20 /opt/mcsmanager/daemon/logs/current.log
```

## 配置模板

```json
{
    "nickname": "My Server",
    "startCommand": "/usr/bin/java -Xms4G -Xmx8G -XX:+UseG1GC -jar server.jar nogui",
    "stopCommand": "stop",
    "stopTimeout": 60,
    "cwd": "/data/mc/server",
    "ie": "utf8",
    "oe": "utf8",
    "createDatetime": 0,
    "lastDatetime": 0,
    "type": "universal",
    "tag": [],
    "endTime": 0,
    "fileCode": "utf8",
    "processType": "general",
    "updateCommand": "",
    "runAs": "",
    "crlf": 1,
    "category": 0,
    "basePort": 25565,
    "enableRcon": false,
    "rconPassword": "",
    "rconPort": 0,
    "rconIp": "",
    "actionCommandList": [],
    "terminalOption": {"haveColor": true, "pty": true, "ptyWindowCol": 164, "ptyWindowRow": 40},
    "eventTask": {"autoStart": true, "autoRestart": true, "autoRestartMaxTimes": -1, "ignore": false},
    "java": {"id": ""},
    "docker": {
        "updateCommandImage": "HOST", "containerName": "", "image": "",
        "uploadSpeedLimit": 0, "downloadSpeedLimit": 0, "ports": [], "extraVolumes": [],
        "capAdd": [], "capDrop": [], "devices": [], "privileged": false, "memory": 0,
        "networkMode": "bridge", "networkAliases": [], "cpusetCpus": "", "cpuUsage": 0,
        "maxSpace": 0, "io": 0, "network": 0, "workingDir": "/data", "env": [],
        "changeWorkdir": true, "labels": [], "gpuEnabled": false, "gpuCount": -1,
        "gpuDeviceIds": [], "gpuDriver": "nvidia", "deviceReadBps": [], "deviceWriteBps": []
    },
    "pingConfig": {"ip": "127.0.0.1", "port": 25565, "type": 1},
    "extraServiceConfig": {"openFrpTunnelId": "", "openFrpToken": ""}
}
```

文件名用 uuid：`/opt/mcsmanager/daemon/data/InstanceConfig/a05f3359-....json`（`cat /proc/sys/kernel/random/uuid`）。

## 字段红线

| 字段 | 要求 | 踩错的后果 |
|---|---|---|
| `stopCommand` | 游戏内命令（MC 填 `stop`） | 用 kill 会丢世界，`session.lock` 残留 |
| `cwd` | 服务端根目录 | 相对路径解析失败，jar 找不到 |
| `startCommand` | 写**绝对路径**的 java | daemon 环境 PATH 与登录 shell 不同，`java: not found` |
| `eventTask.autoStart` | 想要开机自启就 `true` | 机器重启后服务端不在了 |
| `type` | `universal` | 其他值会走特定模板逻辑，通用命令反而受限 |
| `pingConfig` | 填 `127.0.0.1` + 真实端口 | 面板状态灯一直红 |

## 验证

```bash
ls /opt/mcsmanager/daemon/data/InstanceConfig/
grep -a "成功启动\|Done (" /opt/mcsmanager/daemon/data/InstanceLog/<uuid>.log | tail -3
ss -lntp | grep 25565
systemctl restart mcsm-daemon && sleep 15 && ss -lntp | grep 25565   # 验证 autoStart
```

第二条是**验证开机自启是否真的生效**的便宜办法：重启 daemon 等价于模拟开机时 daemon 起来的那一刻。

## 备注

- 实例配置里改完字段后，**必须重启 daemon** 才生效；只改文件不会热加载。
- 面板里手动改实例设置会反写这个 json，所以别在两边同时改。
- 面板登录后实例列表读的是 daemon 的实例集合，文件写对了面板就能看到，不需要"导入"。
