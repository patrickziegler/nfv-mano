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

import argparse

import netifaces

from echo_raw import run_echo_server_raw
from echo_udp import run_echo_server_udp
from util import await_iface


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(type=str, dest="iface", default="eth0", nargs="?")
    parser.add_argument(type=int, dest="port", default=5005, nargs="?")
    parser.add_argument("-m", "--message", type=str, default=None)
    parser.add_argument("-d", "--delay", type=int, default=0)
    parser.add_argument("-r", "--raw",  action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    if args.raw:
        await_iface(args.iface, has_ip=False, verbose=args.verbose)
        run_echo_server_raw(args.iface, args.message, args.delay)
    else:
        await_iface(args.iface, has_ip=True, verbose=args.verbose)
        addr = netifaces.ifaddresses(args.iface)[netifaces.AF_INET][0]["addr"]
        run_echo_server_udp((addr, args.port), args.message, args.delay)
