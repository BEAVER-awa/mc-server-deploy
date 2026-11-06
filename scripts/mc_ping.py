#!/usr/bin/env python3
"""MC 协议 status ping —— 用来确认「端口后面到底是不是 MC 服务端」。

用法:
    python mc_ping.py <host> <port> [--timeout 8]

输出:
    成功: VERSION / PROTOCOL / ONLINE / MAX / MOTD
    失败: 明确区分「连不上」「不是 MC 服务端」「无响应」

为什么不用 telnet / /dev/tcp 判断:
    TCP 能握手只说明有人监听该端口，无法判断后面是 MC、是另一个代理，
    还是一个完全不相关的服务。这个脚本走真实的 Server List Ping 协议。
"""
import json
import socket
import struct
import sys


def varint(n: int) -> bytes:
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def read_varint(sock) -> int:
    num = 0
    shift = 0
    while True:
        b = sock.recv(1)
        if not b:
            raise IOError("连接被对端关闭")
        v = b[0]
        num |= (v & 0x7F) << shift
        if not v & 0x80:
            return num
        shift += 7
        if shift > 35:
            raise IOError("varint 过长，对端可能不是 MC 服务端")


def ping(host: str, port: int, timeout: float = 8.0, protocol: int = 767) -> dict:
    sock = socket.create_connection((host, port), timeout=timeout)
    try:
        host_b = host.encode()
        # Handshake
        body = (varint(0x00) + varint(protocol) + varint(len(host_b)) + host_b
                + struct.pack(">H", port) + varint(1))
        sock.sendall(varint(len(body)) + body)
        # Status Request
        sock.sendall(varint(1) + varint(0x00))
        # Response
        read_varint(sock)          # packet length
        read_varint(sock)          # packet id
        slen = read_varint(sock)
        data = b""
        while len(data) < slen:
            chunk = sock.recv(slen - len(data))
            if not chunk:
                break
            data += chunk
        return json.loads(data.decode("utf-8", "replace"))
    finally:
        sock.close()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    host = sys.argv[1]
    port = int(sys.argv[2])
    timeout = 8.0
    if "--timeout" in sys.argv:
        timeout = float(sys.argv[sys.argv.index("--timeout") + 1])

    try:
        info = ping(host, port, timeout)
    except ConnectionRefusedError:
        print("FAIL 端口拒绝连接（有主机，但该端口没有程序监听 / 转发目标没开）")
        return 1
    except socket.timeout:
        print("FAIL 连接超时（转发规则未生效，或被防火墙丢弃）")
        return 1
    except Exception as e:  # noqa: BLE001
        print("FAIL %s: %s（很可能该端口后面不是 MC 服务端）" % (type(e).__name__, e))
        return 1

    ver = info.get("version", {})
    players = info.get("players", {})
    print("OK   %s:%d 是 MC 服务端" % (host, port))
    print("  版本     : %s" % ver.get("name"))
    print("  协议号   : %s" % ver.get("protocol"))
    print("  在线/上限: %s / %s" % (players.get("online"), players.get("max")))
    motd = info.get("motd")
    if motd is not None:
        print("  MOTD     : %s" % json.dumps(motd, ensure_ascii=False)[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
