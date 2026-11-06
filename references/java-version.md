# Java 版本判定与安装

## 为什么不能凭 MC 版本号猜

同一个 MC 大版本的不同加载器/构建可能压不同的字节码目标；而网上流传的对照表也常常滞后（新版本出来半年内表格还是旧的）。**直接读 jar 的字节码 major 版本最可靠**。

## 字节码 major ↔ Java

| class major | Java |
|---|---|
| 52 | 8 |
| 53 | 9 |
| 54 | 10 |
| 55 | 11 |
| 56 | 12 |
| 57 | 13 |
| 58 | 14 |
| 59 | 15 |
| 60 | 16 |
| 61 | 17 |
| 62 | 18 |
| 63 | 19 |
| 64 | 20 |
| 65 | 21 |
| 66 | 22 |
| 67 | 23 |
| 68 | 24 |
| 69 | 25 |

经验对应（仅作参考，仍以实测为准）：

- MC 1.17 及以下 → Java 8/16
- MC 1.18 – 1.20.4 → Java 17
- MC 1.20.5 – 1.21.x → Java 21
- MC 26.x（新版本号体系）→ Java 25

## 探测命令

Fabric / Forge 的 `server.jar` 可能只是个 launcher，真正的服务端在 `versions/<ver>/server-<ver>.jar` 或 `libraries/` 里。按以下顺序试：

```bash
# 1) 直接读
unzip -p server.jar net/minecraft/server/MinecraftServer.class | od -An -tu1 -j6 -N2

# 2) Fabric 安装版：读 versions 下的真实 jar
V=$(ls versions | head -1)
unzip -p versions/$V/server-$V.jar net/minecraft/server/MinecraftServer.class | od -An -tu1 -j6 -N2
```

输出两个数字 `b1 b2`，major = `b1*256 + b2`（正常情况 b1=0，那么 major 就是第二个数字）。

用 Python 更省事（不依赖 unzip 输出解析）：

```python
import zipfile, sys
p = sys.argv[1]
with zipfile.ZipFile(p) as z:
    name = next(n for n in z.namelist() if n.endswith("MinecraftServer.class"))
    print(name, int.from_bytes(z.read(name)[6:8], "big"))
```

## 安装（Ubuntu 22.04 走清华镜像）

```bash
cd /opt
curl -LO https://mirrors.tuna.tsinghua.edu.cn/Adoptium/25/jdk/x64/linux/OpenJDK25U-jdk_x64_linux_hotspot_25.0.5_8.tar.gz
mkdir -p /opt/java && tar -zxf OpenJDK25U-jdk_x64_linux_hotspot_25.0.5_8.tar.gz -C /opt/java
ln -sf /opt/java/jdk-25.0.5+8/bin/java  /usr/bin/java
ln -sf /opt/java/jdk-25.0.5+8/bin/javac /usr/bin/javac
java -version
```

镜像目录命名规律：`https://mirrors.tuna.tsinghua.edu.cn/Adoptium/<major>/jdk/x64/linux/`，里面文件名形如 `OpenJDK<major>U-jdk_x64_linux_hotspot_<ver>_<build>.tar.gz`。先 `curl -s` 列一下目录再下，别硬编码版本。

## 排错

- `Error: could not open ... /libjvm.so` → 架构不对（x64 机器装了 aarch64 包，或反之）
- `java: command not found` 但 `/opt/java/...` 里有 → 软链没建，或面板以非 root 用户运行时 PATH 不同；实例的 `startCommand` 直接写**绝对路径**最稳
- `UnsupportedClassVersionError: ... compiled by a more recent version` → 装低了，按上表补
