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


class L2SwitchMixin:

    def __init__(self):
        self.mac_to_port = {}

    def learn_mac(self, datapath, msg_in, prot_eth):
        ofp = datapath.ofproto
        ofpp = datapath.ofproto_parser
        in_port = msg_in.match['in_port']

        self.mac_to_port.setdefault(datapath.id, {})
        self.mac_to_port[datapath.id][prot_eth.src] = in_port

        msg_out = ofpp.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg_in.buffer_id,
            in_port=in_port,
            data=msg_in.data,
        )

        if prot_eth.dst in self.mac_to_port[datapath.id]:
            msg_out.actions = [
                ofpp.OFPActionOutput(port=self.mac_to_port[datapath.id][prot_eth.dst]),
            ]
            datapath.send_msg(
                ofpp.OFPFlowMod(
                    datapath=datapath,
                    buffer_id=msg_in.buffer_id,
                    table_id=3,
                    priority=1,
                    match=ofpp.OFPMatch(in_port=in_port, eth_dst=prot_eth.dst,
                                        eth_src=prot_eth.src),
                    instructions=[ofpp.OFPInstructionActions(
                        ofp.OFPIT_APPLY_ACTIONS, msg_out.actions)],
                )
            )
            if msg_in.buffer_id != ofp.OFP_NO_BUFFER:
                return
        else:
            msg_out.actions = [
                ofpp.OFPActionOutput(ofp.OFPP_FLOOD),
            ]
            if msg_in.buffer_id != ofp.OFP_NO_BUFFER:
                msg_out.data = None

        datapath.send_msg(msg_out)
