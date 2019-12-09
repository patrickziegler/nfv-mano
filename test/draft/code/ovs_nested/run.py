from contextlib import contextmanager
from functools import partial
from mininet.net import Mininet
from mininet.node import Ryu
from mininet.cli import CLI


@contextmanager
def ovsns():
    controller_cls = partial(
        Ryu,
        ryu_args=("simple_switch.py",)
    )

    net = Mininet(topo=None, build=False, xterms=True, controller=controller_cls)

    h1 = net.addHost('h1', ip='10.1.0.1')
    s1 = net.addHost('s1')
    h2 = net.addHost('h2', ip='10.1.0.2')
    net.addController("c1", ip="10.1.0.200")

    net.addLink(h1, s1)
    net.addLink(h2, s1)

    net.start()
    try:
        yield net
    finally:
        net.stop()


if __name__ == "__main__":
    with ovsns() as net:
        CLI(net)
