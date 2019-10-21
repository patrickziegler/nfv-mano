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
import socketserver
import time
from functools import partial

import netifaces


class EchoRequestHandler(socketserver.BaseRequestHandler):

    def __init__(self, delay, *args, **kwargs):
        self.delay = delay
        super().__init__(*args, **kwargs)

    def handle(self):
        data, sock = self.request
        print("%s:\n%s" % (self.client_address, data.decode("utf-8")))
        if self.delay:
            time.sleep(self.delay)
        sock.sendto(data, self.client_address)


def run_echo_server_udp(addr, delay):
    print("Starting udp server at %s" % str(addr))
    try:
        handler = partial(EchoRequestHandler, delay)
        with socketserver.UDPServer(addr, handler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server...")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(type=str, dest="iface", default="eth0", nargs="?")
    parser.add_argument(type=int, dest="port", default=5005, nargs="?")
    parser.add_argument("-d", "--delay", type=int, default=0)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    addr = netifaces.ifaddresses(args.iface)[netifaces.AF_INET][0]["addr"]
    run_echo_server_udp((addr, args.port), args.delay)
