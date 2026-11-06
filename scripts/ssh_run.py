#!/usr/bin/env python3
"""用 paramiko + 密码把一批 shell 命令推到远端执行（密码只从环境变量读，不落盘）。

适用场景:
    - 目标机 sshd 关闭了公钥认证（PubkeyAuthentication no），无法用 ssh/scp
    - 需要反复排障，每次手工敲一长串命令太低效

用法:
    export SSHPW='<密码>'                      # Windows PowerShell: $env:SSHPW="..."
    python ssh_run.py -H 1.2.3.4 -p 22 -u root -c "uname -a" "df -h"
    python ssh_run.py -H 1.2.3.4 -p 22 -u root -f cmds.txt

说明:
    - 命令集先上传为 /tmp/_rc.sh 再 bash 执行。这样能避免「脚本读 stdin 把会话输入吞掉」
      导致的「执行了但零输出」，也让管道/多行语句正常工作。
    - 多个 -c 参数按行拼成一个脚本，等价于顺序执行。
"""
import argparse
import os
import sys
import time

import paramiko


def connect(host, port, user, password, retries=6):
    last = None
    for i in range(retries):
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(host, port=port, username=user, password=password,
                      timeout=20, banner_timeout=30, auth_timeout=30,
                      allow_agent=False, look_for_keys=False)
            return c
        except paramiko.AuthenticationException:
            raise  # 密码错就别重试了
        except Exception as e:  # noqa: BLE001
            last = e
            print("connect attempt %d failed: %s" % (i + 1, type(e).__name__), flush=True)
            time.sleep(4 + i * 3)
    raise last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-H", "--host", required=True)
    ap.add_argument("-p", "--port", type=int, default=22)
    ap.add_argument("-u", "--user", default="root")
    ap.add_argument("-c", "--cmd", action="append", default=[], help="可多次指定，按行拼接")
    ap.add_argument("-f", "--file", help="包含命令的文本文件，一行一条，# 开头忽略")
    ap.add_argument("--timeout", type=int, default=1800, help="远端执行超时（秒）")
    args = ap.parse_args()

    password = os.environ.get("SSHPW", "")
    if not password:
        print("ERROR 未设置环境变量 SSHPW", file=sys.stderr)
        return 2

    cmds = list(args.cmd)
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            cmds += [ln.rstrip("\n") for ln in f if ln.strip() and not ln.startswith("#")]
    if not cmds:
        print("ERROR 没有要执行的命令", file=sys.stderr)
        return 2

    script = "\n".join(cmds) + "\n"

    c = connect(args.host, args.port, args.user, password)
    try:
        sftp = c.open_sftp()
        with sftp.open("/tmp/_rc.sh", "w") as f:
            f.write(script)
        sftp.close()
        _in, out, err = c.exec_command("bash /tmp/_rc.sh", timeout=args.timeout)
        print(out.read().decode("utf-8", "replace"))
        e = err.read().decode("utf-8", "replace").strip()
        if e:
            print("[stderr]", e[:3000])
    finally:
        c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
