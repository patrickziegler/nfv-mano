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
import socket
import time
import uuid

import requests
from ryu import cfg as RyuCfg
from ryu.app.wsgi import ControllerBase, Response, WSGIApplication, route
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (CONFIG_DISPATCHER, MAIN_DISPATCHER,
                                    set_ev_cls)
from ryu.lib import hub
from ryu.lib.packet import ether_types, ethernet, lldp, mpls, packet
from ryu.ofproto import ofproto_v1_4

from nfv.mano.config.nfvm_default_config import get_nfvm_default_config
from nfv.mano.vim import VIMAgent
from nfv.monitoring.lldp import LLDPMonitorWorker
from nfv.placement.sfc import ServiceFunction

ETH_P_ALL = 0x03


class NFVManager(app_manager.RyuApp):

    _CONTEXTS = {"wsgi": WSGIApplication}
    OFP_VERSIONS = [ofproto_v1_4.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if RyuCfg.CONF.iface is None:
            raise ValueError("Parameter "iface" was None")
        self.wsgi = kwargs["wsgi"]
        self.wsgi.register(NFVManagerREST, {"nfvm": self})
        self.iface = RyuCfg.CONF.iface
        self.node_id = uuid.uuid4()
        self.datapath = None
        self.monitor = LLDPMonitorWorker()
        self.vim = VIMAgent(self.iface)
        self.vim.start()
        self.vnfs = {}
        hub.spawn(self.clean_up_vnfs)

    def stop(self):
        self.vim.stop()
        super().stop()

    def clean_up_vnfs(self):
        while True:
            hub.sleep(100 * self.monitor.period)
            for label in list(self.vnfs.keys()):
                vnf = self.vnfs[label]
                if vnf.removed and (time.time() - vnf.removed) > vnf.timeout:
                    del self.vnfs[label]

    def start_vnf(self, vnf, buffer_id=None):
        self.vim.start_vnf(vnf)
        self.send_flow_mpls_encap(self.datapath, vnf)
        self.send_flow_mpls_decap(self.datapath, vnf, buffer_id)

    @staticmethod
    def send_attr(attr):
        requests.post(
            url="http://10.0.0.1:8080/lldp",
            headers={"Content-type": "application/json"},
            data=json.dumps(attr),
        )

    @staticmethod
    def send_raw(iface, pkt):
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
        sock.bind((iface, 0))
        try:
            sock.send(pkt.data)
        finally:
            sock.close()

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

    @staticmethod
    def send_flow_mpls_encap(datapath, vnf):
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser
        datapath.send_msg(
            ofproto_parser.OFPFlowMod(
                datapath=datapath,
                table_id=1,
                priority=1,
                match=ofproto_parser.OFPMatch(in_port=vnf.port),
                instructions=[
                    ofproto_parser.OFPInstructionActions(
                        type_=ofproto.OFPIT_APPLY_ACTIONS,
                        actions=[
                            ofproto_parser.OFPActionPushMpls(),
                            ofproto_parser.OFPActionSetField(mpls_label=vnf.label_out),
                            ofproto_parser.OFPActionOutput(port=1)
                        ],
                    ),
                ],
                idle_timeout=vnf.timeout,
            )
        )

    @staticmethod
    def send_flow_mpls_decap(datapath, vnf, buffer_id):
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser
        if buffer_id is None:
            buffer_id = ofproto.OFP_NO_BUFFER
        datapath.send_msg(
            ofproto_parser.OFPFlowMod(
                datapath=datapath,
                buffer_id=buffer_id,
                table_id=2,
                priority=1,
                match=ofproto_parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_MPLS,
                    mpls_label=vnf.label_in,
                ),
                instructions=[
                    ofproto_parser.OFPInstructionActions(
                        type_=ofproto.OFPIT_APPLY_ACTIONS,
                        actions=[
                            ofproto_parser.OFPActionPopMpls(),
                            ofproto_parser.OFPActionOutput(port=vnf.port)
                        ],
                    ),
                ],
                idle_timeout=vnf.timeout,
                flags=ofproto.OFPFF_SEND_FLOW_REM,
            )
        )

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        self.datapath = ev.msg.datapath
        data_port = self.vim.ovs_get_port(self.vim.IFACE_DATA_NETNS)
        for msg in get_nfvm_default_config(self.datapath, data_port):
            self.datapath.send_msg(msg)
        self.monitor.add(self.datapath, node_id=self.node_id)

    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def flow_removed_handler(self, ev):
        try:
            vnf = self.vnfs[ev.msg.match["mpls_label"]]
            self.vim.stop_vnf(vnf)
        except KeyError:
            pass

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg_in = ev.msg
        datapath = msg_in.datapath
        in_port = msg_in.match["in_port"]

        pkt = packet.Packet(msg_in.data)
        prot_eth = pkt.get_protocols(ethernet.ethernet)[0]

        if prot_eth.ethertype == ether_types.ETH_TYPE_LLDP:
            prot_lldp = pkt.get_protocol(lldp.lldp)
            attr = self.monitor.parse(datapath, msg_in.match, prot_eth, prot_lldp)
            self.send_attr(attr)
            self.send_packet_out(
                datapath=datapath,
                data=self.monitor.pool[datapath]["msg"].data,
                port=in_port,
            )

        elif prot_eth.ethertype == ether_types.ETH_TYPE_MPLS:
            prot_mpls = pkt.get_protocol(mpls.mpls)
            vnf = self.vnfs[prot_mpls.label]
            self.start_vnf(
                vnf=vnf,
                buffer_id=msg_in.buffer_id,
            )
            if msg_in.buffer_id == datapath.ofproto.OFP_NO_BUFFER:
                time.sleep(0.5)
                self.send_raw(self.vim.IFACE_DATA, msg_in)
                #
                # Sending the packet via OpenFlow as done below does
                # for some reason not work when the VNF was just started
                #
                # self.send_packet_out(
                #     datapath=datapath,
                #     in_port=in_port,
                #     data=msg_in.data,
                #     port=vnf.port,
                # )


class NFVManagerREST(ControllerBase):

    def __init__(self, req, link, data, **config):
        super().__init__(req, link, data, **config)
        self.app = data["nfvm"]

    @route("status", "/vnf", methods=["GET"])
    def req_handler_vnf(self, req, **kwargs):
        return Response(
            content_type="application/json",
            body=json.dumps([vnf.as_dict() for vnf in self.app.vnfs.values()], indent=4),
        )

    @route("vim", "/vnf/add", methods=["POST"])
    def req_handler_vnf_add(self, req, **kwargs):
        vnf = ServiceFunction.from_json(req.body)
        print(vnf.as_json(indent=4))
        self.app.vnfs[vnf.label_in] = vnf
        if vnf.immediate:
            self.app.start_vnf(vnf)
        return Response(status=200)

    @route("vim", "/vnf/remove", methods=["POST"])
    def req_handler_vnf_remove(self, req, **kwargs):
        vnf = ServiceFunction.from_json(req.body)
        try:
            self.app.vnfs[vnf.label_in].removed = time.time()
        except KeyError:
            pass
        return Response(status=200)
