#!/usr/bin/env python3
#
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

from nfv.util.shell import shell_exec


def link_clean(**kwargs):
    out, _, _ = shell_exec("ip link show", **kwargs)
    for line in out.split("\n"):
        words = line.split(" ")
        try:
            if words[1][0] in ("s", "h", "b", "v"):
                if "@" in words[1]:
                    cmd = "ip link delete %s" % words[1].split("@")[0]
                else:
                    cmd = "ovs-vsctl del-br %s" % words[1].replace(":", "")
                shell_exec(cmd, **kwargs)
        except IndexError:
            pass


if __name__ == "__main__":
    link_clean(verbose=True)
