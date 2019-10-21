from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types


class SimpleSwitch13Custom(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13Custom, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    def add_flow(self, datapath, buffer_id, priority, match, actions):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        instuctions = [
            ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)
        ]
        mod = ofp_parser.OFPFlowMod(
            datapath=datapath,
            buffer_id=buffer_id,
            priority=priority,
            match=match,
            instructions=instuctions,
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        match = ofp_parser.OFPMatch()
        actions = [
            ofp_parser.OFPActionOutput(ofp.OFPP_CONTROLLER),
        ]
        self.add_flow(datapath, ofp.OFP_NO_BUFFER, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg_in = ev.msg
        pkt = packet.Packet(msg_in.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        datapath = msg_in.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        print(datapath.address)

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        in_port = msg_in.match['in_port']
        self.mac_to_port[dpid][src] = in_port

        msg_out = ofp_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg_in.buffer_id,
            in_port=in_port,
            data=msg_in.data,
        )

        if dst in self.mac_to_port[dpid]:
            msg_out.actions = [
                ofp_parser.OFPActionOutput(self.mac_to_port[dpid][dst]),
            ]
            match = ofp_parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(datapath, msg_in.buffer_id, 1, match, msg_out.actions)
            if msg_in.buffer_id != ofp.OFP_NO_BUFFER:
                return
        else:
            msg_out.actions = [
                ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD),
            ]
            if msg_in.buffer_id != ofp.OFP_NO_BUFFER:
                msg_out.data = None

        datapath.send_msg(msg_out)


if __name__ == '__main__':
    import os
    import sys
    from ryu.cmd import manager
    # sys.argv.append("--verbose")
    # sys.argv.append("--enable-debugger")
    sys.argv.append(os.path.basename(os.path.realpath(__file__)))
    manager.main()
