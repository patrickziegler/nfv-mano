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

#ifndef BPF_LLDP_TLV_H
#define BPF_LLDP_TLV_H

#define TLV_SIZE_OID 3
#define TLV_SIZE_SUBTYPE 1

#include <linux/bpf.h>
#include <bpf_helpers.h>

struct tlv_header {
    unsigned length : 9;
    unsigned type : 7;
} __attribute__((packed));

static inline
int tlv_parse_head(char **ptr, short *head, char *data_end)
{
    if (*ptr + 1 > data_end) {
        return 1;
    }
    *head = (short) (**ptr << 8 | *(*ptr + 1));  // ntohs
    *ptr += sizeof(struct tlv_header);
    return *ptr > data_end;
}

static inline
int tlv_jump_next(char **ptr, struct tlv_header *tlv, char *data_end)
{
    *ptr += tlv->length;
    return *ptr > data_end;
}

static inline
int tlv_skip(char **ptr, short *head, struct tlv_header *tlv, char *data_end)
{
    int err = 0;
    if ((err = tlv_parse_head(ptr, head, data_end))) {
        return err;
    }
    if ((err = tlv_jump_next(ptr, tlv, data_end))) {
        return err;
    }
    return err;
}

static inline
int tlv_get_ttl(u16 *ttl, char **ptr, short *head, struct tlv_header *tlv, char *data_end)
{
    int err = 0;
    if ((err = tlv_parse_head(ptr, head, data_end))) {
        return err;
    }
    if (*ptr + sizeof(u16) > data_end) {
        return 1;
    }
    *ttl = __constant_ntohs(*((u16 *) (void *) *ptr));
    return tlv_jump_next(ptr, tlv, data_end);
}

static inline
int tlv_decr_ttl(u16 *ttl, char **ptr, short *head, struct tlv_header *tlv, char *data_end)
{
    int err = 0;
    if ((err = tlv_parse_head(ptr, head, data_end))) {
        return err;
    }
    if (*ptr + sizeof(u16) > data_end) {
        return 1;
    }
    if ((*ttl = __constant_ntohs(*((u16 *) (void *) *ptr))) > 0) {
        *ttl -= 1;
        *((u16 *) (void *) *ptr) = __constant_htons(*ttl);
    }
    return tlv_jump_next(ptr, tlv, data_end);
}

static inline
int write_rtt(char **ptr, short *head, struct tlv_header *tlv, char *data_end)
{
    int err = 0;
    char *ptr_cpy;
    if ((err = tlv_parse_head(ptr, head, data_end))) {
        return err;
    }
    ptr_cpy = *ptr + TLV_SIZE_OID + TLV_SIZE_SUBTYPE;
    if (ptr_cpy + sizeof(u64) > data_end) {
        return 1;
    }
    u64 *value = (u64 *) (void *) ptr_cpy;
    *value = bpf_ktime_get_ns() - *value;
    return tlv_jump_next(ptr, tlv, data_end);
}

#endif
