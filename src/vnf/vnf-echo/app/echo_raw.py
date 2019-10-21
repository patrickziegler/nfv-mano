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

import socket
import time

from ryu.lib.packet import packet

ETH_P_ALL = 0x3


def run_echo_server_raw(iface, msg, delay):
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    sock.bind((iface, 0))
    print("Starting raw server at %s" % iface)
    try:
        while True:
            pkt = packet.Packet(sock.recv(1024))
            if msg is not None:
                pkt.add_protocol(bytes(msg, "utf-8"))
            pkt.serialize()
            time.sleep(delay)
            sock.send(pkt.data)
    except KeyError:
        print("Shutting down server...")
