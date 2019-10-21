/*
 * Copyright (C) 2019 Patrick Ziegler
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include <linux/if_ether.h>
#include <linux/pkt_cls.h>
#include "bpf_lldp_tlv.h"

static inline
int lldp_looping_egress(char *ptr, char *data_end)
{
    u16 ttl;
    short head = 0;
    struct tlv_header *tlv = (void *) &head;

    if (tlv_skip(&ptr, &head, tlv, data_end)) {  // skip ChassisID
        goto ignore;
    }

    if (tlv_skip(&ptr, &head, tlv, data_end)) {  // skip PortID
        goto ignore;
    }

    if (tlv_get_ttl(&ttl, &ptr, &head, tlv, data_end)) {
        goto ignore;
    }

    switch (ttl)
    {
    case 3:
        if (tlv_skip(&ptr, &head, tlv, data_end)) {
            return TC_ACT_SHOT;
        }
        if (write_rtt(&ptr, &head, tlv, data_end)) {
            return TC_ACT_SHOT;
        }
        return TC_ACT_OK;
    case 2:
        if (write_rtt(&ptr, &head, tlv, data_end)) {
            return TC_ACT_SHOT;
        }
        return TC_ACT_OK;
    }

ignore:
    return TC_ACT_OK;
}

SEC("classifier")
int bpf_lldp_egress(struct __sk_buff *skb)
{
    char *ptr = (char *) (long) skb->data;
    char *data_end = (char *) (long) skb->data_end;

    ptr += sizeof(struct ethhdr);
    if (ptr > data_end) {
        goto ignore;
    }
    struct ethhdr *eth = (void *) (long) skb->data;

    if (eth->h_proto == __constant_htons(ETH_P_LLDP)) {
        return lldp_looping_egress(ptr, data_end);
    }

ignore:
    return TC_ACT_OK;
}

extern char _license[];
char _license[] SEC("license") = "GPL";
