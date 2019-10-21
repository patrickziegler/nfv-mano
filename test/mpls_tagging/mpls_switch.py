from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.lib.packet import packet, ethernet, ether_types

OFP_PRIO_MAX = 0xFFFF


class MplsSwitch(app_manager.RyuApp):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_to_port = {}

    def add_flow(self, datapath, buffer_id, table_id, priority, match, actions):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        instuctions = [
            ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)
        ]
        mod = ofp_parser.OFPFlowMod(
            datapath=datapath,
            buffer_id=buffer_id,
            priority=priority,
            table_id=table_id,
            match=match,
            instructions=instuctions,
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        # ofp = datapath.ofproto
        # ofp_parser = datapath.ofproto_parser
        from ryu.ofproto import ofproto_v1_3 as ofp
        from ryu.ofproto import ofproto_v1_3_parser as ofp_parser
        mod = [
            ofp_parser.OFPFlowMod(
                datapath=datapath,
                table_id=0,
                priority=0,
                instructions=[ofp_parser.OFPInstructionGotoTable(table_id=1)]
            ),
            ofp_parser.OFPFlowMod(
                datapath=datapath,
                table_id=0,
                priority=1,
                match=ofp_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP),
                instructions=[ofp_parser.OFPInstructionGotoTable(table_id=3)]
            ),
            ofp_parser.OFPFlowMod(
                datapath=datapath,
                table_id=1,
                priority=0,
                instructions=[ofp_parser.OFPInstructionGotoTable(table_id=2)]
            ),
            ofp_parser.OFPFlowMod(
                datapath=datapath,
                table_id=1,
                priority=1,
                match=ofp_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP),
                instructions=[
                    ofp_parser.OFPInstructionActions(
                        type_=ofp.OFPIT_APPLY_ACTIONS,
                        actions=[
                            ofp_parser.OFPActionPushMpls(),
                            # ofp_parser.OFPActionSetField(mpls_label=0x1234),
                            ofp_parser.OFPActionPushMpls(),
                            # ofp_parser.OFPActionSetField(mpls_label=0x1235)
                        ]
                    ),
                    ofp_parser.OFPInstructionGotoTable(table_id=3)
                ]
            ),
            ofp_parser.OFPFlowMod(
                datapath=datapath,
                table_id=1,
                priority=2,
                match=ofp_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_MPLS, mpls_bos=0),
                instructions=[
                    ofp_parser.OFPInstructionActions(
                        type_=ofp.OFPIT_APPLY_ACTIONS,
                        actions=[
                            ofp_parser.OFPActionPopMpls(ether_types.ETH_TYPE_MPLS)
                        ]
                    ),
                    ofp_parser.OFPInstructionGotoTable(table_id=2),
                ]
            ),
            ofp_parser.OFPFlowMod(
                datapath=datapath,
                table_id=2,
                priority=0,
                instructions=[ofp_parser.OFPInstructionGotoTable(table_id=3)]
            ),
            ofp_parser.OFPFlowMod(
                datapath=datapath,
                table_id=2,
                priority=1,
                match=ofp_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_MPLS, mpls_bos=1),
                instructions=[
                    ofp_parser.OFPInstructionActions(
                        type_=ofp.OFPIT_APPLY_ACTIONS,
                        actions=[
                            ofp_parser.OFPActionPopMpls(ether_types.ETH_TYPE_IP)
                        ]
                    ),
                    ofp_parser.OFPInstructionGotoTable(table_id=3)
                ]
            ),
            ofp_parser.OFPFlowMod(
                datapath=datapath,
                table_id=3,
                priority=0,
                instructions=[
                    ofp_parser.OFPInstructionActions(
                        type_=ofp.OFPIT_APPLY_ACTIONS,
                        actions=[
                            ofp_parser.OFPActionOutput(port=ofp.OFPP_CONTROLLER),
                            ofp_parser.OFPActionOutput(port=ofp.OFPP_FLOOD)
                        ]
                    )
                ]
            )
        ]
        for msg in mod:
            datapath.send_msg(msg)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg_in = ev.msg
        pkt = packet.Packet(msg_in.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        datapath = msg_in.datapath

        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        in_port = msg_in.match['in_port']
        self.mac_to_port[dpid][eth.src] = in_port

        msg_out = ofp_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg_in.buffer_id,
            in_port=in_port,
            data=msg_in.data,
        )

        if eth.dst in self.mac_to_port[dpid]:
            msg_out.actions = [
                ofp_parser.OFPActionOutput(self.mac_to_port[dpid][eth.dst]),
            ]

            match = ofp_parser.OFPMatch(
                in_port=in_port,
                eth_dst=eth.dst,
                eth_src=eth.src
            )
            self.add_flow(datapath, msg_in.buffer_id, 3, 1, match, msg_out.actions)

            if msg_in.buffer_id == ofp.OFP_NO_BUFFER:
                datapath.send_msg(msg_out)
