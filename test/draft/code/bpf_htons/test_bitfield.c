#include <stdio.h>
#include <linux/byteorder/little_endian.h>
// #include <asm_goto_workaround.h>

#define ETH_P_LLDP 0x88cc

struct tlv_header
{
    unsigned length : 9;
    unsigned type : 7;
};

__be16 my_htons(__be16 data)
{
    return ((data & 0x00ff) << 8u) | ((data & 0xff00) >> 8u);
}

int main()
{
    unsigned int data = 0xCC880502;
    unsigned short tmp = __constant_htons(data);
    struct tlv_header *tlv = (void *) &tmp;
    char *ptr = (void*) &data;
    unsigned short *type = (unsigned short*) (ptr + 2);
    *(ptr + 2) = 'Z';
    printf(
                "type:\t0x%02x\nlength:\t0x%02x\n",
                tlv->type,
                tlv->length
                );
    if (tlv->type == my_htons(ETH_P_LLDP)) {
        printf("Detected LLDP via 'custom_htons'\n");
    }
    if (tlv->type == __constant_htons(ETH_P_LLDP)) {
        printf("Detected LLDP via '__constant_htons'\n");
    }
    printf("sizeof(tlv):\t%lu\n", sizeof(*tlv));
    printf("sizeof(float):\t%lu\n", sizeof(float));
    return 0;
}
