from mininet.cli import CLI
from nfv.util.emu import (DelayTopo, addTerm, create_mininet,
                          deploy_bpf_lldp_monitoring, deploy_inband_control,
                          hosts_subns)


class TestTopo(DelayTopo):

    def build(self):
        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")
        h1 = self.addHost("h1", cpu=0.1)
        h2 = self.addHost("h2", cpu=0.05)
        c1 = self.addHost("c1", addr="10.0.0.1/8")
        self.addLink(h1, s1, delay="50ms")
        self.addLink(h2, s2, delay="10ms")
        self.addLink(s1, s2, delay="15ms")
        self.addLink(c1, s1)


if __name__ == "__main__":
    kwargs = {
        "topo": TestTopo(),
        "ctrl_ip": "10.1.0.1",
    }
    with hosts_subns(kwargs["topo"], verbose=True):
        with create_mininet(**kwargs) as net:
            deploy_bpf_lldp_monitoring()
            deploy_inband_control(net)
            addTerm(net, "c1", cmd="nfvctl init master")
            addTerm(net, "h1", cmd="nfvctl init worker h1-eth0")
            addTerm(net, "h2", cmd="nfvctl init worker h2-eth0")
            CLI(net)
