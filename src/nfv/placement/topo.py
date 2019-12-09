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

import networkx as nx


class NetworkModel:

    NODE_TYPE_SWITCH = 1
    NODE_TYPE_WORKER = 2
    NODE_TYPE_MASTER = 3

    def __init__(self):
        self.model = nx.DiGraph()

    def update(self, attr):
        # print(json.dumps(attr, indent=4))
        node_id_src = attr["src"].pop("node_id")
        node_id_dst = attr["dst"].pop("node_id")
        rtt = attr["link"]["rtt"]
        rtt_queue = attr["link"]["rtt_queue"]
        latency = rtt_queue - rtt / 2
        # print("%x -> %x : %f ms (%f ms)" % (node_id_src, node_id_dst, latency, rtt / 2))
        # with open("%x-%x.csv" % (node_id_src, node_id_dst), "a+") as fp:
        #     fp.write("%f;%f;%f;%f\n" % (rtt, rtt_queue, rtt / 2, latency))
        self.model.add_node(node_id_src, **attr["src"])
        self.model.add_node(node_id_dst, **attr["dst"])
        self.model.add_edge(node_id_src, node_id_dst, latency=latency, **attr["link"])

    def get_port(self, node_src, node_dst):
        return self.model[node_dst][node_src]["port"]

    def get_addr(self, node_id):
        return self.model.nodes[node_id]["addr"]

    def as_dict(self):
        return {
            "nodes": dict(self.model.nodes(data=True)),
            "edges": [{"src": a, "dst": b, "attr": dict(c)}
                      for a, b, c in self.model.edges(data=True)],
        }

    def as_json(self, **kwargs):
        return json.dumps(self.as_dict(), **kwargs)

    def plot(self):
        import matplotlib.pyplot as plt
        latencies = [e[2]["latency"] for e in self.model.edges(data=True)]
        plt.figure()
        nx.draw(
            self.model,
            with_labels=True,
            arrows=False,
            font_weight='bold',
            edge_color=latencies,
            edge_cmap=plt.cm.cool,
        )
        plt.show()
