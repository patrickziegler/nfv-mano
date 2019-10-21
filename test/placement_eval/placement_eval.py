import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
import random
import warnings
warnings.filterwarnings("ignore")
# matplotlib.use("Qt5Agg")


def set_random_latencies(g):
    tmp = np.random.normal(10, 100, len(g.edges))
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
    for i, k in enumerate(random.sample([node for node in g.nodes() if node != 0], n)):
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
    import itertools
    import time

    n = 7
    m = 7
    r = 1000

    model = nx.to_directed(nx.nx.star_graph(n))
    add_compute_nodes(model, n)

    switches = [k[0] for k in model.nodes(data=True) if k[1]["node_type"] == 1]
    src, dst = random.sample(switches, 2)

    lat_optim = np.full((n, m), np.nan)
    time_mesh = np.zeros(shape=(n, m))
    time_search = np.zeros(shape=(n, m))

    lat_rand = np.zeros(shape=(n, 2))
    time_random = np.zeros(shape=(n, 1))

    for i in range(n):
        for j in range(m):
            print("%d - %d" % (i, j))
            if j > i:
                continue
            t0 = time.time()
            algo = HastyTraveller(src, dst, chain_length=i+1, limit=j+1)
            algo.prepare(model)
            t1 = time.time()
            _, attrs = algo.calc()
            t2 = time.time()
            lat_optim[i, j] = attrs["latency"]
            time_mesh[i, j] = t1 - t0
            time_search[i, j] = t2 - t1
        t0 = time.time()
        for k in range(r):
            algo = RandomPlacement(src, dst, chain_length=i+1)
            algo.prepare(model)
            _, attrs = algo.calc()
            if attrs["latency"] < lat_rand[i, 0]:
                lat_rand[i, 0] = attrs["latency"]
            elif attrs["latency"] > lat_rand[i, 1]:
                lat_rand[i, 1] = attrs["latency"]
            elif lat_rand[i, 0] == 0:
                lat_rand[i, 0] = attrs["latency"]
        time_random[i, 0] = time.time() - t0

    my_dpi = 96

    max_lat = np.max(lat_rand)
    lat_rand /= max_lat
    lat_optim /= max_lat
    print(max_lat)

    print(lat_optim)
    print(lat_rand)
    print(time_search)
    print(time_random)

    x = np.arange(n) + 1

    plt.style.use("seaborn")
    nice_fonts = {
        #"text.usetex": True,
        #"font.family": "sans",
        "axes.labelsize": 12,
        "font.size": 10,
        #"legend.fontsize": 8,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
    }
    mpl.rcParams.update(nice_fonts)

    marker = itertools.cycle(("p", "s", "*", "h", "X", "d", "P", ">", "v", "<"))

    mpl.rcParams['font.family'] = 'Open Sans'

    plt.figure(figsize=(600/my_dpi, 500/my_dpi), dpi=my_dpi)
    plt.fill_between(
        x=x,
        y1=lat_rand[:, 0],
        y2=lat_rand[:, 1],
        alpha=0.3,
        color="grey",
        label="RP-%d" % r
    )
    # plt.plot(np.arange(m) + 1, lat_optim[np.where(np.eye(n, m))], marker=next(marker), label="Optim")
    for i in range(m):
        plt.plot(x, lat_optim[:, i], marker=next(marker), label="HT-%d" % (i + 1))
    plt.xlabel("Chain length")
    plt.ylabel("Latency (normalized)")
    plt.legend()
    plt.grid(linestyle="dotted")

    plt.tight_layout()
    # plt.savefig("HTLatency.svg")

    plt.figure(figsize=(800/my_dpi, 360/my_dpi), dpi=my_dpi)

    plt.subplot("121")

    marker = itertools.cycle(("p", "s", "*", "h", "X", "d", "P", ">", "v", "<"))

    # plt.plot(np.arange(m) + 1, time_search[np.where(np.eye(n, m))], marker=next(marker), label="Optim")
    for i in range(m):
        plt.plot(x, time_search[:, i], marker=next(marker), label="HT-%d" % (i + 1))
    plt.plot(np.arange(m) + 1, time_random, marker=next(marker), label="RP-%d" % r)
    plt.xlabel("Chain length")
    plt.ylabel("Execution Time / s")
    plt.legend()
    plt.grid(linestyle="dotted")

    plt.subplot("122")
    plt.plot(np.arange(m) + 1, time_mesh[np.where(np.eye(n, m))], marker=next(marker), label="Prepare Mesh")
    plt.plot(np.arange(m) + 1, time_search[np.where(np.eye(n, m))], marker=next(marker), label="Search Paths")
    plt.xlabel("Chain length")
    plt.ylabel("Execution Time / s")
    plt.legend()
    plt.grid(linestyle="dotted")

    plt.tight_layout()
    # plt.savefig("HTTiming.svg")

    plt.show()
