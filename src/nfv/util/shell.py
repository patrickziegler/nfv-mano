# Copyright (C) 2019 Patrick Ziegler
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import pty
import shlex
import subprocess as sp
import sys

IS_PY3 = sys.version_info.major > 2


def shell_exec(cmd, netns=None, verbose=False, **kwargs):
    if netns is not None:
        if isinstance(netns, int):
            cmd = "nsenter --net=/proc/%s/ns/net " % netns + cmd
        else:
            cmd = "nsenter --net=/var/run/netns/%s " % netns + cmd

    if verbose:
        print("+ " + cmd)

    args = {
        "stdout": sp.PIPE,
        "stderr": sp.PIPE,
    }

    args.update(kwargs)

    if IS_PY3:
        kwargs["encoding"] = "UTF-8"

    if "shell" in kwargs and kwargs["shell"]:
        p = sp.Popen(cmd, **args)
    else:
        p = sp.Popen(shlex.split(cmd), **args)

    out, err = p.communicate()

    if IS_PY3:
        out = out.decode()
        err = err.decode()

    if verbose:
        print(err if p.returncode else out)

    return out, err, p.returncode


def shell_exec_check(*args, error=SystemError, **kwargs):
    out, err, ret = shell_exec(*args, **kwargs)
    if ret:
        raise error(err)
    return out, err, ret


def dump_hex(data, sep=" "):
    words = [["%02x" % octet, sep] for octet in data]
    for i in range(15, len(words), 16):
        words[i][1] = "\n"
    return "".join("".join(word) for word in words).rstrip(sep)


class BufferedShell():

    PS1 = chr(127)

    def __init__(self, shell_cmd="/bin/sh"):
        self.pty_in, pty_in_slave = pty.openpty()
        self.pty_out, pty_out_slave = pty.openpty()
        self.shell = sp.Popen(
            shlex.split("env PS1=" + self.__class__.PS1 + " " + shell_cmd),
            stdin=pty_in_slave,
            stdout=pty_out_slave,
            stderr=pty_out_slave,
        )
        self.pending = 1
        self.recv(silent=True)

    def get_pid(self):
        return self.shell.pid

    def send(self, cmd: str):
        self.pending += 1
        os.write(self.pty_in, (cmd + "\n").encode())

    def recv(self, silent=False):
        while True:
            try:
                data = os.read(self.pty_out, 1024).decode()
            except KeyboardInterrupt:
                pass

            if not silent:
                print(data.rstrip(self.__class__.PS1), end="")

            if data[-1] == self.__class__.PS1:
                self.pending -= 1
                if self.pending:
                    continue
                else:
                    break

    def interactive_shell(self, prompt="shell> "):
        while True:
            try:
                cmd = input(prompt)
                if cmd.startswith("exit"):
                    raise StopIteration
                self.send(cmd)
                self.recv()
            except KeyboardInterrupt:
                self.close()
                print("")
                break
            except StopIteration:
                self.close()
                break

    def close(self):
        os.close(self.pty_in)
        os.close(self.pty_out)
        self.shell.kill()
        self.shell.wait()


if __name__ == "__main__":
    bs = BufferedShell()
    print("[PID: " + str(bs.get_pid()) + "]")
    bs.send("ping -c 100 127.0.0.1")
    bs.recv()
    bs.interactive_shell()
