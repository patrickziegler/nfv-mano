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
from contextlib import contextmanager
from functools import partial

from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import CPULimitedHost, OVSBridge, RemoteController
from mininet.term import makeTerm
from mininet.topo import Topo
from mininet.util import makeIntfPair
from nfv.mano.vim import set_memlock
from nfv.util.shell import shell_exec

BPF_DIR = os.path.abspath(os.sep.join(
    (os.path.dirname(os.path.abspath(__file__)), "..", "..", "bpf")))


def deploy_bpf_xdp(key, prog, **kwargs):
    kwargs.setdefault("verbose", True)
    out, _, _ = shell_exec("ip link show", **kwargs)
    for line in out.split("\n"):
        words = line.split(" ")
        try:
            if words[1][0] == key and "@" in words[1]:
                cmd = prog + "_user " + words[1].split("@")[0]
                shell_exec(os.sep.join((BPF_DIR, prog, "build", cmd)), **kwargs)
        except IndexError:
            pass


def deploy_bpf_tc(key, prog, sec="classifier", **kwargs):
    kwargs.setdefault("verbose", True)
    out, _, _ = shell_exec("ip link show", **kwargs)
    for line in out.split("\n"):
        words = line.split(" ")
        try:
            if words[1][0] == key and "@" in words[1]:
                iface = words[1].split("@")[0]
                shell_exec("tc qdisc add dev %s clsact" % iface, **kwargs)
                cmd = "tc filter add dev %s egress bpf direct-action obj %s sec %s verbose" % (
                    iface,
                    os.sep.join((BPF_DIR, prog, "build", prog + "_kern.o")),
                    sec
                )
                shell_exec(cmd, **kwargs)
        except IndexError:
            pass


def deploy_bpf_lldp_monitoring(memlock=8):
    set_memlock(size=memlock)
    deploy_bpf_xdp("b", "xdp_pass")
    deploy_bpf_xdp("s", "xdp_lldp_ingress")
    deploy_bpf_tc("s", "bpf_lldp_egress")


def deploy_inband_control(net, cnode="c1", **kwargs):
    kwargs.setdefault("verbose", True)
    cmd = partial(shell_exec, **kwargs)
    c = net.getNodeByName(cnode)
    makeIntfPair("ctrl", "%s-ctrl" % cnode, node1=c)
    c.cmd("ip addr add 10.1.0.1/28 dev ctrl")
    c.cmd("ip link set dev ctrl up")
    cmd("ip addr add 10.1.0.2/28 dev %s-ctrl" % cnode)
    cmd("ip link set dev %s-ctrl up" % cnode)


@contextmanager
def hosts_subns(topo, **kwargs):
    kwargs.setdefault("verbose", True)
    for host in topo.hosts():
        if host.startswith("h"):
            shell_exec("ip netns add ovs-%s-eth0" % host, **kwargs)
    yield
    for host in topo.hosts():
        if host.startswith("h"):
            shell_exec("ip netns delete ovs-%s-eth0" % host, **kwargs)


def addTerm(net, node, **kwargs):
    net.terms.extend(
        makeTerm(net.getNodeByName(node), **kwargs)
    )


class OVSHub(OVSBridge):

    @classmethod
    def batchStartup(cls, switches, **kwargs):
        result = super().batchStartup(switches, **kwargs)
        for switch in switches:
            switch.cmd("ovs-ofctl del-flows %s" % switch)
            switch.cmd("ovs-ofctl add-flow %s priority=0,actions=flood" % switch)
        return result


class DelayTopo(Topo):

    def __init__(self, *args, **kwargs):
        self.n = 0
        super().__init__(*args, **kwargs)

    def addLink(self, node1, node2, delay=None, **kwargs):
        if delay is None:
            super().addLink(node1, node2, **kwargs)
        else:
            kwargs.setdefault("cls", TCLink)
            kwargs.setdefault("use_tbh", True)
            self.n += 1
            b1 = self.addSwitch("b%d" % self.n, cls=OVSHub)
            self.n += 1
            b2 = self.addSwitch("b%d" % self.n, cls=OVSHub)
            super().addLink(node1, b1)
            super().addLink(node2, b2)
            super().addLink(b1, b2, delay=delay, **kwargs)


class IgnorantRemoteController(RemoteController):

    def checkListening(self):
        pass


@contextmanager
def create_mininet(*args, terms=None, ctrl_ip=None, log_level="info", **kwargs):
    setLogLevel(log_level)
    if ctrl_ip is not None:
        c = partial(IgnorantRemoteController, ip=ctrl_ip, port=6653)
        kwargs.setdefault("controller", c)
    kwargs.setdefault("host", CPULimitedHost)
    net = Mininet(*args, **kwargs)
    net.start()
    if terms is not None:
        for node in terms:
            addTerm(net, node)
    try:
        yield net
    finally:
        net.stop()
