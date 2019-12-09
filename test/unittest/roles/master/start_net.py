from mininet.cli import CLI
from nfv.util.emu import (DelayTopo, addTerm, create_mininet,
                          deploy_bpf_lldp_monitoring, deploy_inband_control,
                          hosts_subns)


class TestTopo(DelayTopo):

    def build(self):
        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")
        s3 = self.addSwitch("s3")
        c1 = self.addHost("c1", ip="10.0.0.1/24")
        h1 = self.addHost("h1", ip="10.0.0.2/24", cpu=0.5)
        h2 = self.addHost("h2", ip="10.0.0.3/24", cpu=0.5)
        h3 = self.addHost("h3", ip="10.0.0.4/24", cpu=0.5)
        p1 = self.addHost("p1", ip="10.0.0.5/24")
        p2 = self.addHost("p2", ip="10.0.0.6/24")
        self.addLink(h1, s1, delay="50ms")
        self.addLink(h2, s2, delay="10ms")
        self.addLink(h3, s3, delay="10ms")
        self.addLink(s1, s2, delay="15ms")
        self.addLink(s2, s3, delay="15ms")
        self.addLink(c1, s1)
        self.addLink(p1, s2)
        self.addLink(p2, s3)


if __name__ == "__main__":
    kwargs = {
        "topo": TestTopo(),
        "terms": ["c1", "h1", "p1", "p2"],
        "ctrl_ip": "10.1.0.1",
    }
    with hosts_subns(kwargs["topo"], verbose=True):
        with create_mininet(**kwargs) as net:
            deploy_bpf_lldp_monitoring()
            deploy_inband_control(net)
            # addTerm(net, "c1", title="NFVO", cmd="nfvctl init master")
            # addTerm(net, "h1", title="NFVM1", cmd="nfvctl init worker h1-eth0")
            addTerm(net, "h2", title="NFVM2", cmd="nfvctl init worker h2-eth0")
            addTerm(net, "h3", title="NFVM3", cmd="nfvctl init worker h3-eth0")
            addTerm(net, "p2", title="peer2", cmd="python echo.py p2-eth0")
            CLI(net)
