#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <unistd.h>
#include <uuid/uuid.h>


int get_mac(const char *iface, unsigned char *mac)
{
    int i, fd, ret = 1;
    struct ifreq ifr;
    fd = socket(AF_INET, SOCK_DGRAM, 0);
    strcpy(ifr.ifr_name, iface);
    if ((ret = ioctl(fd, SIOCGIFHWADDR, &ifr)) == 0) {
        close(fd);
        for (i = 0; i < 6; ++i) {
            mac[i] = (unsigned char) ifr.ifr_hwaddr.sa_data[i];
        }
    }
    return ret;
}

int main(int argc, char *argv[])
{
    int ifindex = 0;
    unsigned char uuid[16];
    unsigned char mac[6];
    if (argc < 2) {
        printf("USAGE: ./test_get_mac IFACE\n");
        return 1;
    }
    if ((ifindex = (int) if_nametoindex(argv[1])) == 0) {
        printf("iface '%s' does not exist!\n", argv[1]);
        return 1;
    }
    get_mac(argv[1], mac);
    uuid_generate(uuid);
    printf("ifindex %d\n", ifindex);
    printf("%02x:%02x:%02x:%02x:%02x:%02x mac hex\n", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    printf("%d:%d:%d:%d:%d:%d mac dec\n", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    printf("%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x uuid\n", uuid[0], uuid[1], uuid[2], uuid[3], uuid[4], uuid[5], uuid[6], uuid[7], uuid[8], uuid[9], uuid[10], uuid[11], uuid[12], uuid[13], uuid[14], uuid[15]);
    return 0;
}
