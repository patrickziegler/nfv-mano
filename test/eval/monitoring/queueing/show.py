import matplotlib as mpl
mpl.use("Qt5Agg")
import matplotlib.pyplot as plt
import numpy as np


if __name__ == "__main__":
    link1 = np.loadtxt("link1.csv", delimiter=";")
    link2 = np.loadtxt("link2.csv", delimiter=";")
    link1strip = np.loadtxt("link1strip.csv", delimiter=";")
    link2strip = np.loadtxt("link2strip.csv", delimiter=";")

    print("Link1 latency")
    print("STD: %f ms" % np.std(link1strip[:,2]))
    print("MEAN: %f ms" % np.mean(link1strip[:,2]))

    print("Link1 half rtt")
    print("STD: %f ms" % np.std(link1strip[:,3]))
    print("MEAN: %f ms" % np.mean(link1strip[:,3]))

    print("Link2 latency")
    print("STD: %f ms" % np.std(link2strip[:,2]))
    print("MEAN: %f ms" % np.mean(link2strip[:,2]))

    print("Link2 half rtt")
    print("STD: %f ms" % np.std(link2strip[:,3]))
    print("MEAN: %f ms" % np.mean(link2strip[:,3]))

    plt.style.use("seaborn")

    nice_fonts = {
        #"text.usetex": True,
        "font.family": "Open Sans",
        "axes.labelsize": 12,
        "font.size": 12,
        "legend.fontsize": 12,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
    }
    mpl.rcParams.update(nice_fonts)

    my_dpi = 96
    plt.figure(figsize=(600/my_dpi, 400/my_dpi), dpi=my_dpi)

    plt.subplot("211")
    plt.plot(link1[:,3], label="There (direction)")
    plt.plot(link2[:,3], label="Back (direction)")
    plt.plot(50 * np.ones((link2.shape[0], 1)))
    plt.ylabel("Latency / ms")

    plt.legend()
    plt.grid(linestyle="dotted")

    plt.subplot("212")
    plt.plot(link1[:,2] - 50)
    plt.plot(link2[:,2] - 50)
    plt.ylabel("Error / ms")

    plt.grid(linestyle="dotted")

    plt.tight_layout()

    plt.savefig("EvalMonitoring.svg")

    plt.show()
