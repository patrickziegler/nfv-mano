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
#include "bpf_lldp_looping.h"

extern struct bpf_map_def map_mac;
struct bpf_map_def SEC("maps") map_mac = {
        .type = BPF_MAP_TYPE_ARRAY,
        .key_size = sizeof(u32),
        .value_size = sizeof(u8),
        .max_entries = MAC_FIELD_COUNT,
        };

SEC("prog")
int xdp_lldp_ingress(struct xdp_md *ctx)
{
    char *ptr = (char *) (long) ctx->data;
    char *data_end = (char *) (long) ctx->data_end;

    ptr += sizeof(struct ethhdr);
    if (ptr > data_end) {
        goto ignore;
    }
    struct ethhdr *eth = (void *) (long) ctx->data;

    if (eth->h_proto == __constant_htons(ETH_P_LLDP)) {
        return lldp_looping_ingress(ptr, eth, data_end);
    }

ignore:
    return XDP_PASS;
}

extern char _license[];
char _license[] SEC("license") = "GPL";
