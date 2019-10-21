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

from ryu.lib.packet import ether_types


def get_nfvo_default_config(datapath=None):
    if datapath is None:
        from ryu.ofproto import ofproto_v1_3 as ofproto
        from ryu.ofproto import ofproto_v1_3_parser as ofproto_parser
    else:
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser

    yield ofproto_parser.OFPFlowMod(
        datapath=datapath,
        table_id=0,
        priority=0,
        instructions=[ofproto_parser.OFPInstructionGotoTable(1)],
    )

    yield ofproto_parser.OFPFlowMod(
        datapath=datapath,
        table_id=0,
        priority=1,
        match=ofproto_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP),
        instructions=[
            ofproto_parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                [
                    ofproto_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)
                ],
            ),
            ofproto_parser.OFPInstructionGotoTable(1),
        ],
    )

    yield ofproto_parser.OFPFlowMod(
        datapath=datapath,
        table_id=0,
        priority=3,
        match=ofproto_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_LLDP),
        instructions=[
            ofproto_parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                [
                    ofproto_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)
                ],
            ),
        ],
    )

    yield ofproto_parser.OFPFlowMod(
        datapath=datapath,
        table_id=0,
        priority=4,
        match=ofproto_parser.OFPMatch(
            eth_src="00:00:00:00:00:00",
            eth_type=ether_types.ETH_TYPE_LLDP
        ),
        instructions=[
            ofproto_parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                [
                    ofproto_parser.OFPActionOutput(ofproto.OFPP_IN_PORT)
                ],
            ),
        ],
    )

    yield ofproto_parser.OFPFlowMod(
        datapath=datapath,
        table_id=0,
        priority=5,
        match=ofproto_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_MPLS),
        instructions=[ofproto_parser.OFPInstructionGotoTable(2)],
    )

    yield ofproto_parser.OFPFlowMod(
        datapath=datapath,
        table_id=1,
        priority=0,
        instructions=[ofproto_parser.OFPInstructionGotoTable(3)],
    )

    yield ofproto_parser.OFPFlowMod(
        datapath=datapath,
        table_id=2,
        priority=0,
        instructions=[
            ofproto_parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                [
                    ofproto_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)
                ],
            ),
        ],
    )

    yield ofproto_parser.OFPFlowMod(
        datapath=datapath,
        table_id=3,
        priority=0,
        instructions=[
            ofproto_parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                [ofproto_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)
                 ],
            ),
        ],
    )


if __name__ == "__main__":
    with open("nfvo_default_config.json", "w") as fd:
        cfg = [msg.to_jsondict() for msg in get_nfvo_default_config()]
        fd.write(json.dumps(cfg, indent=4))
