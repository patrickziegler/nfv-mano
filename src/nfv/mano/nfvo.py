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

import requests
from ryu.app.wsgi import ControllerBase, Response, WSGIApplication, route
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (CONFIG_DISPATCHER, MAIN_DISPATCHER,
                                    set_ev_cls)
from ryu.lib import hub
from ryu.lib.packet import ether_types, ethernet, ipv4, lldp, mpls, packet
from ryu.ofproto import ofproto_v1_4

from nfv.mano.config.nfvo_default_config import get_nfvo_default_config
from nfv.mano.mixin.learning_switch import L2SwitchMixin
from nfv.monitoring.lldp import LLDPMonitor
from nfv.placement.sfc import ServiceFunctionChain, ServiceHook
from nfv.placement.topo import NetworkModel


class NFVOrchestrator(app_manager.RyuApp, L2SwitchMixin):

    _CONTEXTS = {"wsgi": WSGIApplication}
    OFP_VERSIONS = [ofproto_v1_4.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        L2SwitchMixin.__init__(self)
        self.wsgi = kwargs["wsgi"]
        self.wsgi.register(NFVOrchestratorREST, {"nfvo": self})
        self.monitor = LLDPMonitor()
        self.model = NetworkModel()
        self.services = {}
        self.datapaths = {}
        self.ip_to_dp = {}
        hub.spawn(self.lldp_loop)

    def stop(self):
        print(self.model.as_json(indent=4))
        super().stop()

    def lldp_loop(self):
        while True:
            hub.sleep(self.monitor.period)
            self.monitor.flood()

    def find_service(self, hook):
        for sfc in self.services.values():
            if sfc.hook == hook:
                return sfc

    def send_vnf_requests(self, sfc, cmd="add"):
        for vnf in sfc.get_vnfs():
            addr = self.model.get_addr(vnf.node_id)
            requests.post(
                url="http://%s:8080/vnf/%s" % (addr, cmd),
                headers={"Content-type": "application/json"},
                data=vnf.as_json(),
            )

    def implant_service_route(self, sfc, buffer_id):
        buffer_port = None
        for label, path in sfc.get_paths():
            for i in range(len(path) - 1):
                try:
                    port = self.model.get_port(path[i], path[i + 1])
                    datapath = self.datapaths[path[i]]
                except KeyError:
                    continue
                ofproto = datapath.ofproto
                ofproto_parser = datapath.ofproto_parser
                if buffer_port is None:
                    buffer_port = port
                else:
                    buffer_id = ofproto.OFP_NO_BUFFER
                datapath.send_msg(
                    ofproto_parser.OFPFlowMod(
                        datapath=datapath,
                        buffer_id=buffer_id,
                        table_id=2,
                        priority=1,
                        match=ofproto_parser.OFPMatch(
                            eth_type=ether_types.ETH_TYPE_MPLS,
                            mpls_label=label,
                        ),
                        instructions=[
                            ofproto_parser.OFPInstructionActions(
                                ofproto.OFPIT_APPLY_ACTIONS,
                                [
                                    ofproto_parser.OFPActionOutput(port=port)
                                ]
                            ),
                        ],
                        idle_timeout=sfc.timeout
                    )
                )
            if path[-1] in self.datapaths:
                datapath = self.datapaths[path[-1]]
                ofproto = datapath.ofproto
                ofproto_parser = datapath.ofproto_parser
                datapath.send_msg(
                    ofproto_parser.OFPFlowMod(
                        datapath=datapath,
                        table_id=2,
                        priority=1,
                        match=ofproto_parser.OFPMatch(
                            eth_type=ether_types.ETH_TYPE_MPLS,
                            mpls_label=label,
                        ),
                        instructions=[
                            ofproto_parser.OFPInstructionActions(
                                ofproto.OFPIT_APPLY_ACTIONS,
                                [
                                    ofproto_parser.OFPActionPopMpls()
                                ],
                            ),
                            ofproto_parser.OFPInstructionGotoTable(table_id=3)
                        ],
                        idle_timeout=sfc.timeout
                    )
                )
        return buffer_port

    @classmethod
    def add_service_hook(cls, sfc):
        datapath = sfc.hook.src_dp
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser
        datapath.send_msg(
            ofproto_parser.OFPFlowMod(
                datapath=datapath,
                table_id=1,
                priority=1,
                match=ofproto_parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_IP,
                    ipv4_src=sfc.hook.src_ip,
                    ipv4_dst=sfc.hook.dst_ip,
                ),
                instructions=[
                    ofproto_parser.OFPInstructionActions(
                        type_=ofproto.OFPIT_APPLY_ACTIONS,
                        actions=[
                            ofproto_parser.OFPActionPushMpls(),
                            ofproto_parser.OFPActionSetField(mpls_label=sfc.label),
                        ],
                    ),
                    ofproto_parser.OFPInstructionGotoTable(table_id=2),
                ],
            )
        )

    @classmethod
    def remove_service_hook(cls, sfc):
        datapath = sfc.hook.src_dp
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser
        datapath.send_msg(
            ofproto_parser.OFPFlowMod(
                command=ofproto.OFPFC_DELETE,
                datapath=datapath,
                table_id=1,
                priority=1,
                match=ofproto_parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_IP,
                    ipv4_src=sfc.hook.src_ip,
                    ipv4_dst=sfc.hook.dst_ip,
                ),
                buffer_id=ofproto.OFPCML_NO_BUFFER,
                out_port=ofproto.OFPP_ANY,
                out_group=ofproto.OFPG_ANY,
            )
        )

    @staticmethod
    def send_packet_out(datapath, port, **kwargs):
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser
        kwargs.setdefault("buffer_id", ofproto.OFP_NO_BUFFER)
        kwargs.setdefault("in_port", ofproto.OFPP_CONTROLLER)
        msg_out = ofproto_parser.OFPPacketOut(
            datapath=datapath,
            actions=[ofproto_parser.OFPActionOutput(port=port)],
            **kwargs
        )
        datapath.send_msg(msg_out)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        for msg in get_nfvo_default_config(datapath):
            datapath.send_msg(msg)
        self.datapaths[datapath.id] = datapath
        self.monitor.add(datapath)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg_in = ev.msg
        datapath = msg_in.datapath
        in_port = msg_in.match["in_port"]

        pkt = packet.Packet(msg_in.data)
        prot_eth = pkt.get_protocol(ethernet.ethernet)

        if prot_eth.ethertype == ether_types.ETH_TYPE_LLDP:
            prot_lldp = pkt.get_protocol(lldp.lldp)
            attr = self.monitor.parse(datapath, msg_in.match, prot_eth, prot_lldp)
            self.model.update(attr)

        elif prot_eth.ethertype == ether_types.ETH_TYPE_IP and msg_in.table_id == 0:
            ofproto_parser = datapath.ofproto_parser
            datapath.send_msg(
                ofproto_parser.OFPFlowMod(
                    datapath=datapath,
                    table_id=0,
                    priority=2,
                    match=ofproto_parser.OFPMatch(
                        in_port=msg_in.match["in_port"],
                    ),
                    instructions=[
                        ofproto_parser.OFPInstructionGotoTable(1),
                    ],
                )
            )
            prot_ip = pkt.get_protocol(ipv4.ipv4)
            self.ip_to_dp.setdefault(prot_ip.src, datapath)

        elif prot_eth.ethertype == ether_types.ETH_TYPE_MPLS:
            prot_mpls = pkt.get_protocol(mpls.mpls)
            sfc = self.services[prot_mpls.label]
            sfc.embedding(self.model.model)
            self.send_vnf_requests(sfc, "add")
            buffer_port = self.implant_service_route(
                sfc=sfc,
                buffer_id=msg_in.buffer_id
            )
            if msg_in.buffer_id == datapath.ofproto.OFP_NO_BUFFER:
                self.send_packet_out(
                    datapath=datapath,
                    buffer_id=msg_in.buffer_id,
                    in_port=in_port,
                    data=msg_in.data,
                    port=buffer_port,
                )

        else:
            self.learn_mac(datapath, msg_in, prot_eth)


class NFVOrchestratorREST(ControllerBase):

    def __init__(self, req, link, data, **config):
        super().__init__(req, link, data, **config)
        self.app = data["nfvo"]
        self.app: NFVOrchestrator

    @route("monitoring", "/lldp", methods=["POST"])
    def req_handler_lldp(self, req, **kwargs):
        attr = json.loads(req.body)
        attr["dst"]["addr"] = req.remote_addr
        self.app.model.update(attr)
        return Response(status=200)

    @route("monitoring", "/lldp/period", methods=["GET", "POST"])
    def req_handler_lldp_period(self, req, **kwargs):
        if req.method == "GET":
            return Response(
                content_type="application/json",
                body=json.dumps({"period": self.app.monitor.period}, indent=2),
            )
        else:
            data = json.loads(req.body)
            self.app.monitor.period = data["period"]
            return Response(status=200)

    @route("status", "/model", methods=["GET"])
    def req_handler_model(self, req, **kwargs):
        return Response(
            content_type="application/json",
            body=self.app.model.as_json(indent=2),
        )

    @route("status", "/sfc", methods=["GET"])
    def req_handler_sfc(self, req, **kwargs):
        return Response(
            content_type="application/json",
            body=json.dumps([sfc.as_dict() for sfc in self.app.services.values()], indent=2),
        )

    @route("status", "/plot", methods=["GET"])
    def req_handler_plot(self, req, **kwargs):
        self.app.model.plot()
        return Response(status=200)

    @route("mano", "/sfc/add", methods=["POST"])
    def req_handler_sfc_add(self, req, **kwargs):
        sfc = ServiceFunctionChain.from_json(req.body, self.app.ip_to_dp)
        if self.app.find_service(sfc.hook):
            return Response(status=409)
        self.app.add_service_hook(sfc)
        self.app.services[sfc.label] = sfc
        return Response(status=200)

    @route("mano", "/sfc/remove", methods=["POST"])
    def req_handler_sfc_remove(self, req, **kwargs):
        hook = ServiceHook.from_json(req.body)
        sfc = self.app.find_service(hook)
        if sfc:
            self.app.remove_service_hook(sfc)
            del self.app.services[sfc.label]
            self.app.send_vnf_requests(sfc, "remove")
        return Response(status=200)
