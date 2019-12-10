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

import json
import time

import requests

from mininet.node import OVSSwitch, RemoteController
from nfv.util.emu import (DelayTopo, addTerm, create_mininet,
                          deploy_bpf_lldp_monitoring)


class LinearDelayTopo(DelayTopo):

    def __init__(self, *args, length, delay, **kwargs):
        self.length = length
        self.delay = delay
        super().__init__(*args, **kwargs)

    def build(self):
        """
        Simple linear topology with given latency used for all links
        """
        s1 = self.addSwitch("s0")
        for i in range(self.length):
            s2 = self.addSwitch("s%d" % (i + 1))
            self.addLink(s1, s2, delay=self.delay)
            s1 = s2


def measure_emulated_latencies(topo, duration=10, period=1):
    """
    Sampling all latencies found in the network model over a given time period

    :param float duration: total time during which latency is sampled
    :param float period: period of lldp probing and sampling
    """
    kwargs = {
        "topo": topo,
        "controller": RemoteController,
        "switch": OVSSwitch,
    }
    with create_mininet(**kwargs) as net:
        deploy_bpf_lldp_monitoring()
        addTerm(net, "s0", title="NFVO", cmd="nfvctl init master")
        time.sleep(5)  # wait for controller to start up
        requests.post("http://127.0.0.1:8080/lldp/period", json.dumps({"period": period}))
        t0 = time.time()
        latencies = []
        while (time.time() - t0) < duration:
            response = requests.get("http://127.0.0.1:8080/model")
            model = json.loads(response.text)
            latencies.extend([edge["attr"]["latency"] for edge in model["edges"]])
            time.sleep(period)
        return latencies


def plot_latencies(data):
    """
    :param ndarray data: 3xN matrix with N latency measurement tuples like
                         (chain length, mean, std. deviation)
    """
    import matplotlib.pyplot as plt
    plt.figure()
    plt.errorbar(data[:, 0], data[:, 1], data[:, 2], ecolor="black")
    plt.show()


if __name__ == "__main__":
    import numpy as np
    n = 4
    data = np.zeros(shape=(n, 3))
    data[:, 0] = 10 * (np.arange(n) + 1)  # chain length in first column
    for i in range(n):
        topo = LinearDelayTopo(length=int(data[i, 0]), delay="10ms")
        latencies = np.asarray(measure_emulated_latencies(topo))
        data[i, 1] = np.mean(latencies)
        data[i, 2] = np.std(latencies)
    print("Results:")
    print(data)
    plot_latencies(data)
