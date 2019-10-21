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

import itertools
import random
from abc import abstractmethod

import networkx as nx

from nfv.placement.topo import NetworkModel as nm


class AbstractPlacement:

    def __init__(self, node_src, node_dst, chain_length):
        self.node_src = node_src
        self.node_dst = node_dst
        self.chain_length = chain_length
        self.expected_latency = None
        self.paths = None

    @abstractmethod
    def prepare(self, model):
        pass

    @abstractmethod
    def calc(self):
        pass


class RandomPlacement(AbstractPlacement):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workers = None

    def prepare(self, model):
        self.model = model
        self.workers = [e[0] for e in model.nodes(data=True)
                        if e[1]["node_type"] == nm.NODE_TYPE_WORKER]

    def calc(self):
        self.paths = []
        self.expected_latency = 0
        nodes = [self.node_src, *random.sample(self.workers, self.chain_length), self.node_dst]
        a, b = itertools.tee(nodes)
        next(b)
        for u, v in zip(a, b):
            path = nx.shortest_path(self.model, u, v)
            self.paths.append(path)
            c, d = itertools.tee(path)
            next(d)
            self.expected_latency += sum([self.model[u][v]["latency"] for u, v in zip(c, d)])
        return self.paths, {"latency": self.expected_latency}


class HastyTraveller(AbstractPlacement):

    def __init__(self, *args, limit=3, **kwargs):
        super().__init__(*args, **kwargs)
        self.tabu = [self.node_dst]
        self.limit = limit
        self.mesh = None
        self.mesh_costs = None
        self.mesh_paths = None

    def prepare(self, model):
        self.mesh = nx.DiGraph()
        self.mesh.add_nodes_from(
            [e for e in model.nodes(data=True) if e[1]["node_type"] == nm.NODE_TYPE_WORKER]
        )
        self.mesh.add_nodes_from(
            nx.subgraph(model, [self.node_src, self.node_dst]).nodes(data=True)
        )
        self.mesh_costs = {}
        self.mesh_paths = {}
        for node in self.mesh:
            self.mesh_costs[node], self.mesh_paths[node] = nx.single_source_dijkstra(
                G=model,
                source=node,
                weight="latency"
            )
        for node_a in self.mesh:
            for node_b in self.mesh:
                self.mesh.add_edge(node_a, node_b, latency=self.mesh_costs[node_a][node_b])

    def calc(self):

        def _core(node, level):
            if level == 0:
                return [(0, [node])]
            paths = []
            submesh = nx.subgraph(self.mesh, [e for e in self.mesh if e not in self.tabu])
            keys = sorted(submesh.adj[node], key=lambda item: submesh.adj[node][item]["latency"])
            neighs = [(k, submesh.adj[node][k]["latency"]) for k in keys if k != node]
            self.tabu.append(node)
            for i in range(min(len(neighs), self.limit)):
                neigh = neighs[i][0]
                cost = neighs[i][1]
                paths.extend([(e[0] + cost, [node, *e[1]]) for e in _core(neigh, level - 1)])
            self.tabu.pop(-1)
            return paths

        paths = _core(self.node_src, self.chain_length)
        for i in range(len(paths)):
            cost, path = paths[i]
            paths[i] = (
                cost + self.mesh_costs[paths[i][1][-1]][self.node_dst],
                [*path, self.node_dst]
            )
        cost, path = sorted(paths)[0]
        a, b = itertools.tee(path)
        next(b)
        self.paths = [self.mesh_paths[u][v] for u, v in zip(a, b)]
        self.expected_latency = cost
        return self.paths, {"latency": self.expected_latency}
