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
import random
import resource
import tempfile
import time

import docker
import netifaces

from nfv.util.shell import shell_exec


def set_memlock(size=8):
    limit = size * 1024 * 1024  # 8 MiB (necessary for extensive xpd deployment)
    resource.setrlimit(resource.RLIMIT_MEMLOCK, (limit, limit))  # eqv. to 'ulimit -l 8192'


def get_iface():
    s = "abcdefghijklmnopqrstuvwxyz0123456789"
    ifaces = netifaces.interfaces()
    iface = "lo"
    while iface in ifaces:
        iface = "vnf-" + "".join(random.choices(s, k=10))
    return iface


class VIMAgent:

    BPF_DIR = os.path.abspath(os.sep.join(
        (os.path.dirname(os.path.abspath(__file__)), "..", "..", "bpf")))

    IFACE_DATA = "ovs-data"
    IFACE_DATA_NETNS = "data"
    IFACE_CTRL = "ovs-ctrl"
    IFACE_CTRL_NETNS = "ctrl"
    BRIDGE_NAME = "br0"

    DCLI = docker.from_env()

    def __init__(self, iface):
        self.iface = iface
        self.netns = "ovs-%s" % iface
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ovs-")
        self.ovs_sock = "--db=unix:%s/db.sock" % self.tmpdir.name
        self.ovs_bridge_name = "br0"

    def exec(self, cmd, **kwargs):
        kwargs.setdefault("verbose", True)
        return shell_exec(cmd, **kwargs)

    def create_link(self, iface_in, iface_out, addr_in=None, addr_out=None, netns_out=None):
        self.exec("ip link add name %s type veth peer name %s netns %s" %
                  (iface_out, iface_in, self.netns), netns=netns_out)
        self.exec("ip link set dev %s up" %
                  (iface_in,), netns=self.netns)
        self.exec("ip link set dev %s up" %
                  (iface_out,), netns=netns_out)
        if addr_in is not None:
            self.exec("ip a add %s dev %s" %
                      (addr_in, iface_in), netns=self.netns)
        if addr_out is not None:
            self.exec("ip a add %s dev %s" %
                      (addr_out, iface_out), netns=netns_out)

    def create_ovsdb(self):
        self.exec("ovsdb-tool create %s/conf.db"
                  " /usr/share/openvswitch/vswitch.ovsschema" % self.tmpdir.name,
                  netns=self.netns)
        self.exec("ovsdb-server %s/conf.db "
                  " -vconsole:emer"
                  " -vsyslog:err"
                  " -vfile:info"
                  " --remote=punix:%s/db.sock"
                  " --private-key=db:Open_vSwitch,SSL,private_key"
                  " --certificate=db:Open_vSwitch,SSL,certificate"
                  " --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert"
                  " --log-file=%s/ovsdb-server.log"
                  " --pidfile=%s/ovsdb-server.pid"
                  " --no-chdir"
                  " --detach" % ((self.tmpdir.name, ) * 4),
                  netns=self.netns)
        self.exec("ovs-vsctl"
                  " --db=unix:%s/db.sock"
                  " --no-wait"
                  " init" % self.tmpdir.name,
                  netns=self.netns)
        self.exec("ovs-vswitchd unix:%s/db.sock"
                  " -vconsole:emer"
                  " -vsyslog:err"
                  " -vfile:info"
                  " --log-file=%s/ovs-vswitchd.log"
                  " --pidfile=%s/ovs-vswitchd.pid"
                  " --mlockall"
                  " --no-chdir"
                  " --detach" % ((self.tmpdir.name, ) * 3),
                  netns=self.netns)

    def start(self):
        if not os.path.exists("/var/run/netns/%s" % self.netns):
            self.exec("ip netns add %s" % self.netns)

        self.create_link(self.IFACE_DATA_NETNS, self.IFACE_DATA)
        self.create_link(self.IFACE_CTRL_NETNS, self.IFACE_CTRL,
                         "10.2.0.2/24", "10.2.0.1/24")

        self.exec("/bin/sh -c 'echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6'",
                  netns=self.netns)

        bpf_egress = os.sep.join((self.BPF_DIR, "bpf_lldp_egress",
                                  "build", "bpf_lldp_egress_kern.o"))

        set_memlock(size=8)

        self.exec("%s/xdp_lldp_ingress_redirect/build/xdp_lldp_ingress_redirect_user %s %s" %
                  (self.BPF_DIR, self.iface, self.IFACE_DATA))
        self.exec("%s/xdp_redirect/build/xdp_redirect_user %s %s" %
                  (self.BPF_DIR, self.IFACE_DATA, self.iface))
        self.exec("%s/xdp_pass/build/xdp_pass_user %s" %
                  (self.BPF_DIR, self.IFACE_DATA_NETNS), netns=self.netns)
        self.exec("tc qdisc add dev %s clsact" %
                  (self.IFACE_DATA_NETNS,), netns=self.netns)
        self.exec("tc filter add dev %s egress bpf direct-action obj %s" %
                  (self.IFACE_DATA_NETNS, bpf_egress), netns=self.netns)

        self.create_ovsdb()

        self.exec("ovs-vsctl %s add-br %s" %
                  (self.ovs_sock, self.ovs_bridge_name), netns=self.netns)
        self.exec("ovs-vsctl %s set-fail-mode %s secure" %
                  (self.ovs_sock, self.ovs_bridge_name), netns=self.netns)
        self.exec("ovs-vsctl %s add-port %s %s" %
                  (self.ovs_sock, self.ovs_bridge_name, self.IFACE_DATA_NETNS), netns=self.netns)
        self.exec("ovs-vsctl %s set-controller %s %s tcp:10.2.0.1:6653" %
                  (self.ovs_sock, self.ovs_bridge_name, self.IFACE_CTRL_NETNS), netns=self.netns)

    def stop(self):
        self.exec("ovs-vsctl %s del-br %s" %
                  (self.ovs_sock, self.ovs_bridge_name), netns=self.netns)
        with open("%s/ovs-vswitchd.pid" % self.tmpdir.name) as fp:
            shell_exec("kill %d" % int(fp.read()))
        with open("%s/ovsdb-server.pid" % self.tmpdir.name) as fp:
            shell_exec("kill %d" % int(fp.read()))
        self.exec("ip link delete %s" % self.IFACE_DATA_NETNS, netns=self.netns)
        self.exec("ip link delete %s" % self.IFACE_CTRL_NETNS, netns=self.netns)
        self.exec("ip netns delete %s" % self.netns)
        self.exec("ip link set %s xdp off" % self.iface)
        self.exec("tc qdisc del dev %s clsact" % self.IFACE_DATA_NETNS, netns=self.netns)
        # self.exec("ip netns delete %s" % self.netns)

    def ovs_add_port(self, iface):
        self.exec("ovs-vsctl %s add-port %s %s" % (self.ovs_sock, self.BRIDGE_NAME, iface))

    def ovs_get_port(self, iface):
        res, _, _ = self.exec("ovs-vsctl %s get Interface %s ofport" % (self.ovs_sock, iface))
        return int(res)

    def ovs_del_port(self, iface):
        self.exec("ovs-vsctl %s del-port %s %s" % (self.ovs_sock, self.BRIDGE_NAME, iface))

    def start_vnf(self, vnf, **kwargs):
        kwargs.update({
            "tty": True,
            "stdin_open": True,
            "detach": True,
            "network_mode": "none",
            "remove": True,
        })
        vnf.container = self.DCLI.containers.run(vnf.image, command=vnf.param, **kwargs)
        while not vnf.container.attrs["State"]["Running"]:
            vnf.container.reload()
            time.sleep(0.1)
        vnf.iface = get_iface()
        self.create_link(
            iface_in=vnf.iface,
            iface_out="eth0",
            netns_out=vnf.container.attrs["State"]["Pid"],
        )
        self.ovs_add_port(vnf.iface)
        vnf.port = self.ovs_get_port(vnf.iface)
        vnf.stopped = None

    def stop_vnf(self, vnf):
        self.ovs_del_port(vnf.iface)
        vnf.container.kill()
