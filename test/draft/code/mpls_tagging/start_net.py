from mininet.cli import CLI
from mininet.topo import LinearTopo
from mininet.node import RemoteController
from mininet.net import Mininet
from contextlib import contextmanager

@contextmanager
def create_mininet(*args, **kwargs):
    net = Mininet(*args, **kwargs)
    net.start()
    try:
        yield net
    finally:
        net.stop()


if __name__ == "__main__":
    kwargs = {
        "topo": LinearTopo(2),
        "controller": RemoteController,
        "xterms": False
    }
    with create_mininet(**kwargs) as net:
        CLI(net)
