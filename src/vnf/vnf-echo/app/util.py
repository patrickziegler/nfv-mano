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

import time
from contextlib import contextmanager

import netifaces


def dump_hex(data, sep=" "):
    words = [["%02x" % octet, sep] for octet in data]
    for i in range(15, len(words), 16):
        words[i][1] = "\n"
    return "".join("".join(word) for word in words).rstrip(sep)


@contextmanager
def info(on_enter=None, on_exit=None, verbose=True):
    if on_enter is not None and verbose:
        print(on_enter)
    yield
    if on_exit is not None and verbose:
        print(on_exit)


def iface_is_up(iface):
    MASK_STATE = 0x1
    with open("/sys/class/net/%s/flags" % iface) as fd:
        return int(fd.read(), 16) & MASK_STATE > 0


def await_iface(iface, has_ip=True, is_up=True, verbose=False):
    period = 0.1
    with info(
            on_enter="Awaiting iface %s..." % iface,
            on_exit="-> Found iface %s" % iface,
            verbose=verbose):
        while iface not in netifaces.interfaces():
            time.sleep(period)
    if has_ip:
        with info(
                on_enter="Awaiting ip addr for %s..." % iface,
                on_exit="-> Found ip addr for iface %s" % iface,
                verbose=verbose):
            while netifaces.AF_INET not in netifaces.ifaddresses(iface):
                time.sleep(period)
    if is_up:
        with info(
                on_enter="Awaiting activation of iface %s" % iface,
                on_exit="-> Found iface %s to be active" % iface,
                verbose=verbose):
            while not iface_is_up(iface):
                time.sleep(period)
