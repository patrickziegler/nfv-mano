from mininet.cli import CLI
from nfv.util.emu import (DelayTopo, addTerm, create_mininet,
                          deploy_bpf_lldp_monitoring)


class TestTopo(DelayTopo):

    def build(self):
        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")
        s3 = self.addSwitch("s3")
        self.addLink(s1, s2, delay="100ms")
        self.addLink(s2, s3, delay="200ms")
        self.addLink(s3, s1, delay="500ms")


if __name__ == "__main__":
    kwargs = {
        "topo": TestTopo(),
        "ctrl_ip": "127.0.0.1",
    }
    with create_mininet(**kwargs) as net:
        deploy_bpf_lldp_monitoring()
        addTerm(net, "s1", cmd="nfvctl init master")
        CLI(net)
