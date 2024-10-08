import math
import os
import re
import sys
import tempfile
import time
from glob import glob
from os import environ, path

import paramiko
import scp

envs = environ
INPUT_HOST = envs.get("INPUT_HOST")
INPUT_PORT = int(envs.get("INPUT_PORT", "22"))
INPUT_USER = envs.get("INPUT_USER")
INPUT_PASS = envs.get("INPUT_PASS")
INPUT_KEY = envs.get("INPUT_KEY")
INPUT_CONNECT_TIMEOUT = envs.get("INPUT_CONNECT_TIMEOUT", "30s")
INPUT_SCP = envs.get("INPUT_SCP")
INPUT_BEFORE = envs.get("INPUT_BEFORE")
INPUT_AFTER = envs.get("INPUT_AFTER")

seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "M": 86400 * 30}
pattern_seconds_per_unit = re.compile(r'^(' + "|".join(['\\d+' + k for k in seconds_per_unit.keys()]) + ')$')


def convert_to_seconds(s):
    if s is None:
        return 30
    if isinstance(s, str):
        return int(s[:-1]) * seconds_per_unit[s[-1]] if pattern_seconds_per_unit.search(s) else 30
    if (isinstance(s, int) or isinstance(s, float)) and not math.isnan(s):
        return round(s)
    return 30


strips = [" ", "\"", " ", "'", " "]
map = {}


def strip_and_parse_envs(p):
    if not p:
        return None
    for c in strips:
        p = p.strip(c)
    return path.expandvars(p) if p != "." else f"{path.realpath(p)}/*"


def connect(callback=None):
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        ssh = paramiko.SSHClient()
        p_key = None
        if INPUT_KEY:
            tmp.write(INPUT_KEY.encode())
            tmp.close()
            p_key = paramiko.RSAKey.from_private_key_file(filename=tmp.name)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(INPUT_HOST, port=INPUT_PORT, username=INPUT_USER,
                    pkey=p_key, password=INPUT_PASS,
                    timeout=convert_to_seconds(INPUT_CONNECT_TIMEOUT))
    except Exception as err:
        print(f"Connect error\n{err}")
        sys.exit(1)

    else:
        if callback:
            callback(ssh)

    finally:
        os.unlink(tmp.name)
        tmp.close()


# Define progress callback that prints the current percentage completed for the file
def progress(filename, size, sent):
    now = int(time.time())
    if now - 5 > map.get(filename, 0):
        sys.stdout.write(f"{filename}... {float(sent) / float(size) * 100:.2f}%\n")
        map[filename] = now


def ssh_process(ssh, input_ssh):
    command_str = path.expandvars(input_ssh.replace('\r', ''))
    print(command_str)

    stdin, stdout, stderr = ssh.exec_command(command_str)

    ssh_exit_status = stdout.channel.recv_exit_status()

    out = "".join(stdout.readlines())
    out = out.strip() if out is not None else None
    if out:
        print(f"Success: \n{out}")

    err = "".join(stderr.readlines())
    err = err.strip() if err is not None else None
    if err:
        print(f"Error: \n{err}")

    if ssh_exit_status != 0:
        print(f"ssh exit status: {ssh_exit_status}")
        sys.exit(1)

    pass


def scp_process(ssh, input_scp):
    copy_list = []
    for c in input_scp.splitlines():
        if not c:
            continue
        l2r = c.split("=>")
        if len(l2r) == 2:
            local = strip_and_parse_envs(l2r[0])
            remote = strip_and_parse_envs(l2r[1])
            if local and remote:
                copy_list.append({"l": local, "r": remote})
                continue
        print(f"SCP ignored {c.strip()}")
    print(copy_list)

    if len(copy_list) <= 0:
        print("SCP no copy list found")
        return

    with scp.SCPClient(ssh.get_transport(), progress=progress, sanitize=lambda x: x) as conn:
        for l2r in copy_list:
            remote = l2r.get('r')
            try:
                ssh.exec_command(f"mkdir -p {remote}")
            except Exception as err:
                print(f"Remote mkdir error. Can't create {remote}\n{err}")
                sys.exit(1)

            for f in [f for f in glob(l2r.get('l'))]:
                try:
                    conn.put(f, remote_path=remote, recursive=True)
                    print(f"{f} -> {remote}")
                except Exception as err:
                    print(f"Scp error. Can't copy {f} on {remote}\n{err}")
                    sys.exit(1)
    pass


def processes():
    if INPUT_KEY is None and INPUT_PASS is None:
        print("SSH-SCP invalid (Key/Passwd)")
        return

    if not INPUT_BEFORE:
        print("SSH-SCP no first input found")
    else:
        print("-------------------BEFORE-------------------")
        connect(lambda c: ssh_process(c, INPUT_BEFORE))
        print()

    if not INPUT_SCP:
        print("SSH-SCP no scp input found")
    else:
        print("-------------------SCP-------------------")
        connect(lambda c: scp_process(c, INPUT_SCP))
        print()

    if not INPUT_AFTER:
        print("SSH-SCP no after input found")
    else:
        print("-------------------AFTER-------------------")
        connect(lambda c: ssh_process(c, INPUT_AFTER))
        print()

    pass


if __name__ == '__main__':
    processes()
