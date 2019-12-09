import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import networkx as nx
import random
import warnings
warnings.filterwarnings("ignore")
# matplotlib.use("Qt5Agg")


def set_random_latencies(g):
    tmp = np.random.normal(200, 300, len(g.edges))
    tmp[np.where(tmp < 0)] = 0
    for i, (a, b) in enumerate(g.edges()):
        g.edges[a, b]["latency"] = tmp[i]


def set_zero_cpu_usage(g):
    for i, k in enumerate(g.nodes()):
        g.nodes[k]["cpu"] = 0
        g.nodes[k]["node_type"] = 1


def add_compute_nodes(g: nx.DiGraph, n=10):
    set_zero_cpu_usage(g)
    h = np.max(g.nodes()) + 1
    tmp = np.random.normal(80, 30, n)
    tmp[np.where(tmp < 0)] = 0
    tmp[np.where(tmp > 100)] = 100
    for i, k in enumerate(random.sample(g.nodes(), n)):
        g.add_node(h, cpu=tmp[i], node_type=2)
        g.add_edge(k, h)
        g.add_edge(h, k)
        h += 1
    set_random_latencies(g)


def plot_graph(g):
    # node_color = [k[1]["cpu"] for k in g.nodes(data=True)]
    node_color = [k[1]["node_type"] for k in g.nodes(data=True)]
    nx.draw(
        g,
        with_labels=True,
        font_weight='bold',
        edge_color=[e[2]["latency"] for e in g.edges(data=True)],
        edge_cmap=plt.cm.viridis,
        node_color=node_color,
        cmap=plt.cm.Set3,
        vmin=1,
        vmax=2,
    )


if __name__ == "__main__":
    from nfv.placement.algo import HastyTraveller, RandomPlacement

    model = nx.to_directed(nx.random_tree(6))
    add_compute_nodes(model, 4)

    switches = [k[0] for k in model.nodes(data=True) if k[1]["node_type"] == 1]
    node_src, node_dst = random.sample(switches, 2)

    a1 = HastyTraveller(node_src, node_dst, chain_length=4, limit=4)
    a1.prepare(model)
    path, attrs = a1.calc()
    print("Best path (%.02f ms):" % attrs["latency"])
    print(path)

    a2 = RandomPlacement(node_src, node_dst, chain_length=4)
    a2.prepare(model)
    path, attrs = a2.calc()
    print("Random path (%.02f ms):" % attrs["latency"])
    print(path)

    my_dpi = 96
    plt.figure(figsize=(800/my_dpi, 360/my_dpi), dpi=my_dpi)
    plt.subplot("121")
    plot_graph(model)
    plt.subplot("122")
    plot_graph(a1.mesh)
    # plt.savefig("out.svg")
    plt.show()
