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

import socketserver
import time
from functools import partial


class EchoRequestHandler(socketserver.BaseRequestHandler):

    def __init__(self, msg, delay, *args, **kwargs):
        self.msg = msg
        self.delay = delay
        super().__init__(*args, **kwargs)

    def handle(self):
        data, sock = self.request
        # print("%s:\n%s" % (self.client_address, data.decode("utf-8")))
        if self.msg is not None:
            data = (data.decode("utf-8").rstrip() + self.msg).encode("utf-8")
        time.sleep(self.delay)
        sock.sendto(data, self.client_address)


def run_echo_server_udp(addr, msg, delay):
    print("Starting udp server at %s" % str(addr))
    try:
        handler = partial(EchoRequestHandler, msg, delay)
        with socketserver.UDPServer(addr, handler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server...")
