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

// glibc
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// libbpf
#include <bpf/bpf.h>
#include <bpf/libbpf.h>

// linux
#include <sys/ioctl.h>
#include <net/if.h>
#include <linux/if_link.h>

#define MAC_FIELD_COUNT 6

struct xdp_loader_param {
    char* filename;
    char* iface;
    int ifindex;
    __u32 xdp_flags;
};

int parse_args(struct xdp_loader_param *param, int argc, char **argv)
{
    param->xdp_flags = XDP_FLAGS_UPDATE_IF_NOEXIST;
    int opt;

    while ((opt = getopt(argc, argv, "hm:f")) != -1) {
        switch (opt)
        {
        case 'h':
            printf("Usage: %s [-h] [-m hw|drv|skb] IFACE\n", argv[0]);
            exit(EXIT_SUCCESS);
        case 'm':
            if (strcmp(optarg, "hw") == 0) {
                param->xdp_flags |= XDP_FLAGS_HW_MODE;
            } else if (strcmp(optarg, "drv") == 0) {
                param->xdp_flags |= XDP_FLAGS_DRV_MODE;
            } else if (strcmp(optarg, "skb") == 0) {
                param->xdp_flags |= XDP_FLAGS_SKB_MODE;
            } else {
                fprintf(stderr, "ERROR: unknown xdp mode %s\n", optarg);
                return EXIT_FAILURE;
            }
            break;
        default:
            fprintf(stderr, "WARNING: unknown option %c\n", opt);
            break;
        }
    }
    if ((argc - optind) < 1) {
        fprintf(stderr, "ERROR: not enough arguments\n");
        return EXIT_FAILURE;
    }

    param->ifindex = (int) if_nametoindex(argv[optind]);
    param->iface = argv[optind];

    if (param->ifindex == 0) {
        fprintf(stderr, "ERROR: no such interface %s\n", argv[optind]);
        return EXIT_FAILURE;
    }

    char *filename = malloc(sizeof(char) * 1024);
    strcpy(filename, argv[0]);
    strcpy(filename + strlen(filename) - 5, "_kern.o");
    param->filename = filename;

    return EXIT_SUCCESS;
}

int get_mac(const char *iface, unsigned char *mac)
{
    int i, sock, ret;
    struct ifreq ifr;
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    strcpy(ifr.ifr_name, iface);
    if ((ret = ioctl(sock, SIOCGIFHWADDR, &ifr))) {
        return ret;
    }
    close(sock);
    for (i = 0; i < 6; ++i) {
        mac[i] = (unsigned char) ifr.ifr_hwaddr.sa_data[i];
    }
    return 0;
}

int main(int argc, char **argv)
{
    struct xdp_loader_param param;
    struct bpf_object *bpf_obj;
    unsigned char mac[MAC_FIELD_COUNT];
    int err, prog_fd, map_mac_fd;

    if ((err = parse_args(&param, argc, argv))) {
        return err;
    }

    if ((err = bpf_prog_load(param.filename, BPF_PROG_TYPE_XDP, &bpf_obj, &prog_fd))) {
        fprintf(stderr, "ERROR %d: %s\nCould not load xdp program\n", -err, strerror(-err));
        return err;
    }

    if (!(map_mac_fd = bpf_object__find_map_fd_by_name(bpf_obj, "map_mac"))) {
        fprintf(stderr, "ERROR %d: %s\nCould not find map 'map_mac'\n", -err, strerror(-err));
        return err;
    }

    get_mac(param.iface, mac);

    for (uint32_t i = 0; i < MAC_FIELD_COUNT; ++i) {
        bpf_map_update_elem(map_mac_fd, &i, &mac[(size_t) i], 0);
    }

    if ((err = bpf_set_link_xdp_fd(param.ifindex, prog_fd, param.xdp_flags))) {
        fprintf(stderr, "ERROR %d: %s\nCould not attach xdp program\n", -err, strerror(-err));
        return err;
    }

    printf("Successfully loaded %s\n", param.filename);
    return EXIT_SUCCESS;
}
