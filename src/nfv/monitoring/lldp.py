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

import struct
import uuid

import ryu.lib.packet as packet
from ryu.lib.packet import ether_types

from nfv.monitoring.probes import ProbeMemoryCgroup, ProbeProcessorCgroup
from nfv.placement.topo import NetworkModel as nm


class TLVParser:

    parsers = dict()

    def __init__(self, subtype, fieldname, category=None):
        self.subtype = subtype
        self.fieldname = fieldname
        self.category = category

    def __call__(self, fn):
        if self.category is None:
            def _fn(*args, attr, **kwargs):
                attr.update({self.fieldname: fn(*args, **kwargs)})
        else:
            def _fn(*args, attr, **kwargs):
                attr[self.category].update({self.fieldname: fn(*args, **kwargs)})

        self.__class__.parsers[self.subtype] = _fn
        return _fn


class LLDPMonitor:

    PROJECT_OID = b'\x1e\xa5\xed'
    TLV_STATE_RTT = 1
    TLV_STATE_RTT_QUEUE = 2

    @classmethod
    def interpret_node_id(cls, node_id):
        if isinstance(node_id, uuid.UUID):
            return {
                "chassis_id": struct.pack("!Q", 0),
                "port_id": node_id.bytes,
                "node_id": node_id.hex,
                "node_type": nm.NODE_TYPE_WORKER,
            }
        else:
            return {
                "chassis_id": struct.pack("!Q", node_id),
                "port_id": struct.pack("!QQ", 0, 0),
                "node_id": node_id,
                "node_type": nm.NODE_TYPE_SWITCH,
            }

    @classmethod
    def build_probing_packet(cls, chassis_id, port_id, ttl=3):
        prot_eth = packet.ethernet.ethernet(
            dst=packet.lldp.LLDP_MAC_NEAREST_BRIDGE,
            src="00:00:00:00:00:00",
            ethertype=ether_types.ETH_TYPE_LLDP,
        )
        prot_lldp = packet.lldp.lldp(tlvs=[
            packet.lldp.ChassisID(
                subtype=packet.lldp.ChassisID.SUB_LOCALLY_ASSIGNED,
                chassis_id=chassis_id,
            ),
            packet.lldp.PortID(
                subtype=packet.lldp.PortID.SUB_LOCALLY_ASSIGNED,
                port_id=port_id,
            ),
            packet.lldp.TTL(
                ttl=ttl,
            ),
            packet.lldp.OrganizationallySpecific(
                oui=cls.PROJECT_OID,
                subtype=cls.TLV_STATE_RTT,
                info=struct.pack("!Q", 0),
            ),
            packet.lldp.OrganizationallySpecific(
                oui=cls.PROJECT_OID,
                subtype=cls.TLV_STATE_RTT_QUEUE,
                info=struct.pack("!Q", 0),
            ),
            packet.lldp.End(),
        ])
        pkt = packet.packet.Packet()
        pkt.add_protocol(prot_eth)
        pkt.add_protocol(prot_lldp)
        pkt.serialize()
        return pkt

    def __init__(self, period=1):
        self.pool = dict()
        self.period = period

    def add(self, datapath, node_id=None):
        if datapath in self.pool:
            return
        fields = self.interpret_node_id(
            node_id=node_id if node_id else datapath.id
        )
        pkt = self.build_probing_packet(
            chassis_id=fields["chassis_id"],
            port_id=fields["port_id"],
        )
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser
        msg = ofproto_parser.OFPPacketOut(
            datapath=datapath,
            in_port=ofproto.OFPP_CONTROLLER,
            buffer_id=ofproto.OFP_NO_BUFFER,
            actions=[ofproto_parser.OFPActionOutput(ofproto.OFPP_FLOOD)],
            data=pkt.data,
        )
        self.pool[datapath] = {
            "msg": msg,
            "node_id": fields["node_id"],
            "node_type": fields["node_type"],
        }

    def remove(self, datapath):
        del self.pool[datapath]

    def flood(self):
        for datapath in self.pool:
            datapath.send_msg(self.pool[datapath]["msg"])

    @TLVParser(subtype=TLV_STATE_RTT, category="link", fieldname="rtt")
    def parse_tlv_rtt(self, tlv: packet.lldp.OrganizationallySpecific):
        return struct.unpack("=Q", tlv.info)[0] / 1e6

    @TLVParser(subtype=TLV_STATE_RTT_QUEUE, category="link", fieldname="rtt_queue")
    def parse_tlv_rtt_queue(self, tlv: packet.lldp.OrganizationallySpecific):
        return struct.unpack("=Q", tlv.info)[0] / 1e6

    def parse(self, datapath, match, eth_frame, lldp_frame):
        if lldp_frame.tlvs[0].subtype != packet.lldp.ChassisID.SUB_LOCALLY_ASSIGNED or \
           lldp_frame.tlvs[1].subtype != packet.lldp.PortID.SUB_LOCALLY_ASSIGNED:
            raise ValueError("Wrong LLDP format")

        node_id = struct.unpack("!Q", lldp_frame.tlvs[0].chassis_id)[0]
        node_type = nm.NODE_TYPE_SWITCH

        if not node_id:
            node_id = uuid.UUID(bytes=lldp_frame.tlvs[1].port_id).hex
            node_type = nm.NODE_TYPE_WORKER

        attr = {
            "src": {
                "node_id": node_id,
                "node_type": node_type,
            },
            "dst": {
                "node_id": self.pool[datapath]["node_id"],
                "node_type": self.pool[datapath]["node_type"],
            },
            "link": {
                "port": match["in_port"],
                "addr": eth_frame.src,
            },
        }

        for i in range(3, len(lldp_frame.tlvs) - 1):
            tlv = lldp_frame.tlvs[i]
            try:
                if tlv.oui == self.__class__.PROJECT_OID:
                    handler = TLVParser.parsers[tlv.subtype]
                    handler(self, attr=attr, tlv=tlv)
            except (AttributeError, struct.error) as err:
                print(err)

        return attr


class LLDPMonitorWorker(LLDPMonitor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.probes = {
            "cpu": ProbeProcessorCgroup(),
            "ram": ProbeMemoryCgroup(),
        }

    def parse(self, *args, **kwargs):
        attrs = super().parse(*args, **kwargs)
        attrs["dst"].setdefault("probes", {})
        for key in self.probes:
            attrs["dst"]["probes"].update(self.probes[key].get())
        return attrs
