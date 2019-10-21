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

#ifndef BPF_LLDP_LOOPING_H
#define BPF_LLDP_LOOPING_H

#include <linux/if_ether.h>
#include "bpf_lldp_tlv.h"
#include "bpf_mac.h"

static inline
int lldp_looping_ingress(char *ptr, struct ethhdr *eth, char *data_end)
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

    if (tlv_decr_ttl(&ttl, &ptr, &head, tlv, data_end)) {
        goto ignore;
    }

    switch (ttl)
    {
    case 1:
        if (tlv_skip(&ptr, &head, tlv, data_end)) {
            return XDP_DROP;
        }
        if (write_rtt(&ptr, &head, tlv, data_end)) {
            return XDP_DROP;
        }
        return XDP_TX;
    case 0:
        if (write_rtt(&ptr, &head, tlv, data_end)) {
            return XDP_DROP;
        }
        if (write_mac(eth->h_source, data_end)) {
            return XDP_DROP;
        }
        return XDP_PASS;
    }

ignore:
    return XDP_PASS;
}

#endif
