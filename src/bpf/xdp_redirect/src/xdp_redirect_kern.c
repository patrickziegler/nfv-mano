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

#include <linux/bpf.h>
#include <bpf_helpers.h>

extern struct bpf_map_def tx_port;
struct bpf_map_def SEC("maps") tx_port = {
        .type = BPF_MAP_TYPE_DEVMAP,
        .key_size = sizeof(int),
        .value_size = sizeof(int),
        .max_entries = 1,
        };

SEC("prog")
int xdp_redirect(struct xdp_md *ctx)
{
    return bpf_redirect_map(&tx_port, 0, 0);
}

extern char _license[];
char _license[] SEC("license") = "GPL";
