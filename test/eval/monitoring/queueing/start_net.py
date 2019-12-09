import os

from mininet.cli import CLI
from mininet.node import OVSBridge
from nfv.mano.vim import VIMAgent, set_memlock
from nfv.util.emu import DelayTopo, addTerm, create_mininet, deploy_bpf_xdp


class TestTopo(DelayTopo):

    def build(self):
        s0 = self.addSwitch("s0")
        c1 = self.addHost("c1", ip="10.1.0.1/24")
        s1 = self.addHost("s1", ip="10.1.0.2/24")
        s2 = self.addHost("s2", ip="10.1.0.3/24")
        self.addLink(c1, s0)
        self.addLink(s1, s0)
        self.addLink(s2, s0)
        self.addLink(s1, s2, delay="50ms")
        p1 = self.addHost("p1", ip="10.2.0.1/24")
        self.addLink(p1, s2)
        p2 = self.addHost("p2", ip="10.2.0.2/24")
        self.addLink(p2, s1)


def init_ovs(net, vim, node):

    vim.create_ovsdb()
    vim.exec("ovs-vsctl %s add-br %s" %
             (vim.ovs_sock, vim.ovs_bridge_name), netns=vim.netns)
    vim.exec("ovs-vsctl %s set-fail-mode %s secure" %
             (vim.ovs_sock, vim.ovs_bridge_name), netns=vim.netns)
    vim.exec("ovs-vsctl %s add-port %s %s" %
             (vim.ovs_sock, vim.ovs_bridge_name, node + "-eth1"), netns=vim.netns)
    vim.exec("ovs-vsctl %s set-controller %s %s tcp:10.1.0.1:6653" %
             (vim.ovs_sock, vim.ovs_bridge_name, node + "-eth0"), netns=vim.netns)


def deploy_bpf(vim, node):
    vim.netns = net.getNodeByName(node).pid
    vim.exec("%s/xdp_lldp_ingress/build/xdp_lldp_ingress_user %s" %
             (v1.BPF_DIR, node + "-eth1"), netns=vim.netns)
    vim.exec("tc qdisc add dev %s clsact" % (node + "-eth1"), netns=vim.netns)
    vim.exec("tc filter add dev %s egress bpf direct-action obj %s sec classifier verbose" %
             (node + "-eth1", os.sep.join((vim.BPF_DIR, "bpf_lldp_egress/build/bpf_lldp_egress_kern.o"))), netns=vim.netns)


if __name__ == "__main__":
    kwargs = {
        "topo": TestTopo(),
        "switch": OVSBridge,
        "controller": None,
    }
    v1 = VIMAgent("dummy")
    v2 = VIMAgent("dummy")
    set_memlock(size=8)
    with create_mininet(**kwargs) as net:
        deploy_bpf_xdp("b", "xdp_pass")
        deploy_bpf(v1, "s1")
        deploy_bpf(v2, "s2")
        init_ovs(net, v1, "s1")
        init_ovs(net, v2, "s2")
        v1.ovs_add_port("s1-eth2")
        v2.ovs_add_port("s2-eth2")
        addTerm(net, "c1", title="NFVO", cmd="nfvctl init master")
        addTerm(net, "s2")
        addTerm(net, "p1")
        addTerm(net, "p2")
        CLI(net)
    v1.stop()
    v2.stop()
