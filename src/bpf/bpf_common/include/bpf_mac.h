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

#ifndef BPF_MAC_H
#define BPF_MAC_H

#include <linux/bpf.h>
#include <bpf_helpers.h>

#define MAC_FIELD_COUNT 6

extern struct bpf_map_def map_mac;

static inline
int write_mac(unsigned char *ptr, char *data_end)
{
    u32 i, key;
    unsigned char *value;
    if ((char *) ptr + MAC_FIELD_COUNT > data_end) {
        return 1;
    }
    for (i=0; i < MAC_FIELD_COUNT; ++i) {
        key = i;
        if ((value = bpf_map_lookup_elem(&map_mac, &key)) != NULL) {
            *ptr = *value;
        }
        ptr += 1;
    }
    return 0;
}

#endif
