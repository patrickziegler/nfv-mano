# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.app.wsgi import ControllerBase, WSGIApplication, route, Response

import os
import hashlib
import json
import random
import numpy as np
import time
from webob.static import DirectoryApp


class Edge:
    def __init__(self, port, cost):
        self.port = port
        self.cost = cost


class Node:
    def __init__(self, name, dp):
        self.name = name
        self.datapath = dp
        self.neighbors = {}
        self.host = None

    def set_host(self, port):
        self.host = port

    def add_neighbor(self, dst, port):
        if os.path.exists(HaecController.TOPOLOGY_JSON):

            with open(HaecController.TOPOLOGY_JSON, "r") as fo:
                data = json.load(fo)

            pair = [int(self.name[1::]), int(dst[1::])]

            edges = [e for e in data["edges"]
                     if (e["to"] == pair[0] and e["from"] == pair[1])
                     or (e["from"] == pair[0] and e["to"] == pair[1])]

            if len(edges) > 0:
                self.neighbors[dst] = Edge(port, edges[0]["cost"])
                return

        self.neighbors[dst] = Edge(port, 10)

    def set_cost(self, dst, cost):
        self.neighbors[dst].cost = cost


class Flow:
    def __init__(self, node, next, src, dst, timeout):
        self.node = node
        self.next = next
        self.src = src
        self.dst = dst
        self.timeout = time.time() + timeout


class HaecController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    TOPOLOGY_JSON = None

    def __init__(self, *args, **kwargs):
        super(HaecController, self).__init__(*args, **kwargs)
        self.nodes = {}
        self.flows = []
        self.mac_to_node = {}

        HaecController.TOPOLOGY_JSON = os.path.realpath(os.path.dirname(os.path.realpath(__file__)) + "/../visualisation/topo.json")

        wsgi = kwargs['wsgi']
        wsgi.register(HaecRest, {'haec_api_app': self})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, CONFIG_DISPATCHER)
    def desc_stats_reply_handler(self, ev):
        msg = ev.msg
        for port in msg.body:
            src = port.name[:4]
            dst = port.name[5:]

            if not dst:
                continue

            node = self.nodes.get(src)
            if not node:
                node = Node(src, msg.datapath)
                self.nodes[src] = node

            if dst[0] == ord('h'):
                node.set_host(port.port_no)
            else:
                node.add_neighbor(dst, port.port_no)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, **kwargs):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst, **kwargs)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst, **kwargs)
        datapath.send_msg(mod)

    def add_broadcast(self, src, dst, prev, timeout, **kwargs):
        next_hop = {v: [] for v in self.nodes}
        for d, s in prev.items():
            # store d in next_hop of s
            next_hop[s].append((d, self.nodes[s].neighbors[d].port))

        for name, next in next_hop.items():
            node = self.nodes[name]
            dp = node.datapath
            parser = dp.ofproto_parser
            ofproto = dp.ofproto

            ports = [node.host] + [p for _, p in next]
            flow = Flow(node, [self.nodes[v] for v, _ in next], src, dst, timeout)
            self.flows.append(flow)

            match = parser.OFPMatch(eth_dst=dst, eth_src=src)
            actions = [parser.OFPActionOutput(p) for p in ports]
            self.add_flow(dp, 10, match, actions, hard_timeout=timeout, **kwargs)

    def add_path(self, src, dst, node, next, timeout, **kwargs):
        edge = node.neighbors[next.name]
        dp = node.datapath
        parser = dp.ofproto_parser
        ofproto = dp.ofproto

        flow = Flow(node, [next], src, dst, timeout)
        self.flows.append(flow)

        match = parser.OFPMatch(eth_dst=dst, eth_src=src)
        actions = [parser.OFPActionOutput(edge.port)]
        self.add_flow(dp, 20, match, actions, hard_timeout=timeout, **kwargs)

    def add_local(self, src, dst, node, **kwargs):
        dp = node.datapath
        parser = dp.ofproto_parser

        match = parser.OFPMatch(eth_dst=dst, eth_src=src)
        actions = [parser.OFPActionOutput(node.host)]
        self.add_flow(dp, 30, match, actions, **kwargs)

    def dijkstra(self, source):
        queue = [v for v in self.nodes]
        dist = {}
        prev = {}

        dist[source.name] = 0

        while queue:
            u = min(queue, key=lambda v: dist.get(v, np.inf))
            queue.remove(u)

            for v, e in self.nodes[u].neighbors.items():
                alt = dist[u] + e.cost
                if alt < dist.get(v, np.inf):
                    dist[v] = alt
                    prev[v] = u

        return dist, prev

    def get_flows(self):
        # find all flows that are timed out
        t = time.time()
        self.flows = [f for f in self.flows if f.timeout >= t]

        return self.flows

    def get_nodes(self):
        return self.nodes

    def set_cost(self, src, dst, cost):
        node = self.nodes[src]
        node.neighbors[dst].cost = cost

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        dst = eth.dst
        src = eth.src
        port = datapath.ports[in_port]
        name = port.name[:4]
        src_node = self.nodes[name]

        # learn the mac
        if port.name[5:6] == b'h':
            self.mac_to_node[src] = src_node

        _, prev = self.dijkstra(src_node)

        dst_node = self.mac_to_node.get(dst)
        if not dst_node:
            # setup broadcast
            self.add_broadcast(src, dst, prev, timeout=1)
            out_port = ofproto.OFPP_FLOOD
        elif src_node == dst_node:
            # forward to host interface
            self.add_local(src, dst, dst_node, idle_timeout=30)
            out_port = dst_node.host
        else:
            # setup shortest path
            c = dst_node
            self.add_local(src, dst, dst_node, idle_timeout=30)
            while c != src_node:
                p = self.nodes[prev[c.name]]
                self.add_path(src, dst, p, c, timeout=3)
                out_port = p.neighbors[c.name].port
                c = p

        actions = [parser.OFPActionOutput(out_port)]

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)


class HaecRest(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(HaecRest, self).__init__(req, link, data, **config)
        self.haec_api_app = data['haec_api_app']
        path = os.path.join(os.path.dirname(__file__), "../visualisation/")
        self.static_app = DirectoryApp(path)

    @route('topology', '/flows')
    def flow_handler(self, req, **kwargs):
        flows = self.haec_api_app.get_flows()
        data = [
            {"from": f.node.name.decode(), "to": [v.name.decode() for v in f.next], "src": f.src, "dst": f.dst}
            for f in flows
        ]
        body = json.dumps(data)
        res = Response(content_type='application/json', body=body)
        # res._headerlist.append(('Access-Control-Allow-Origin', '*'))
        return res

    @route('topology', '/nodes')
    def node_handler(self, req, **kwargs):
        nodes = self.haec_api_app.get_nodes()
        data = {
            u.decode(): dict(links={v.decode(): e.cost for v, e in n.neighbors.items()})
            for u, n in nodes.items()
        }
        body = json.dumps(data)
        res = Response(content_type='application/json', body=body)
        # res._headerlist.append(('Access-Control-Allow-Origin', '*'))
        return res

    @route('topology', '/nodes/{source}/links/{dest}', methods=['PUT'])
    def cost_handler(self, req, **kwargs):
        cost = float(req.body)
        self.haec_api_app.set_cost(kwargs["source"].encode(), kwargs["dest"].encode(), cost)
        res = Response(status=200)
        return res

    @route('topology', '/{filename:.*}')
    def static_handler(self, req, **kwargs):
        if kwargs['filename']:
            req.path_info = kwargs['filename']
        return self.static_app(req)


# app_manager.require_app('ryu.app.rest_topology')
app_manager.require_app('ryu.app.ws_topology')
# app_manager.require_app('ryu.app.ofctl_rest')

if __name__ == '__main__':
    import sys
    from ryu.cmd import manager
    sys.argv.append("--verbose")
    sys.argv.append("--enable-debugger")
    sys.argv.append("--observe-links")
    sys.argv.append(os.path.basename(os.path.realpath(__file__)))
    manager.main()
