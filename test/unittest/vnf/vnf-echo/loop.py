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
import random
import socket
import time
import uuid

import netifaces
import ryu.lib.packet as packet

from nfv.util.shell import dump_hex

ETH_P_ALL = 0x3


def get_addr(iface):
    addr = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]["addr"],
    port = random.randint(49152, 65535)
    return addr[0], port


def get_random_mac_pair():
    tmp_uuid = uuid.uuid4()
    mac_src = ":".join("%02x" % b for b in tmp_uuid.bytes[0:6])
    mac_dst = ":".join("%02x" % b for b in tmp_uuid.bytes[6:12])
    return mac_src, mac_dst


def udp(addr_src, addr_dst, msg, label=None):
    mac_src, mac_dst = get_random_mac_pair()
    prot_eth = packet.ethernet.ethernet(
        src=mac_src,
        dst=mac_dst,
        ethertype=packet.ether_types.ETH_TYPE_IP,
    )
    prot_ip = packet.ipv4.ipv4(
        src=addr_src[0],
        dst=addr_dst[0],
        proto=packet.in_proto.IPPROTO_UDP,
    )
    prot_udp = packet.udp.udp(
        src_port=addr_src[1],
        dst_port=addr_dst[1],
    )
    payload = bytes(msg, "utf-8")
    pkt = packet.packet.Packet()
    pkt.add_protocol(prot_eth)
    if label is not None:
        prot_eth.ethertype = packet.ether_types.ETH_TYPE_MPLS
        pkt.add_protocol(
            proto=packet.mpls.mpls(
                label=label,
            ),
        )
    pkt.add_protocol(prot_ip)
    pkt.add_protocol(prot_udp)
    pkt.add_protocol(payload)
    pkt.serialize()
    return pkt


def send(iface, pkt):
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    sock.bind((iface, 0))
    try:
        sock.send(pkt.data)
        return sock.recv(1024)
    except ConnectionRefusedError:
        print("Lost connection to server...")
    except KeyboardInterrupt:
        print("Shutting down client...")
    finally:
        sock.close()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(type=str, dest="iface", default="eth0", nargs="?")
    parser.add_argument(type=str, dest="ip", default="127.0.0.1", nargs="?")
    parser.add_argument(type=int, dest="port", default=5005, nargs="?")
    parser.add_argument("-m", "--message", type=str, dest="msg", default="msg")
    parser.add_argument("-l", "--label", type=int, default=None)
    parser.add_argument("-p", "--period", type=float, default=1)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    i = 0
    args = parse_args()
    addr_src = get_addr(args.iface)
    addr_dst = (args.ip, args.port)
    pkt = udp(addr_src, addr_dst, args.msg, args.label)
    try:
        while True:
            print("send %d\n%s" % (i, dump_hex(pkt.data)))
            answ = send(args.iface, pkt)
            print("recv %d\n%s" % (i, dump_hex(bytearray(answ))))
            time.sleep(args.period)
            i += 1
    except KeyboardInterrupt:
        print("Exit")
