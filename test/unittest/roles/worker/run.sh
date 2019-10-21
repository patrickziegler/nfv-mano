#!/bin/sh

set -x

ip netns add ns1
ip netns add ns2

ip link add eth0 netns ns1 type veth peer name eth0 netns ns2

nsenter --net=/var/run/netns/ns1 ip addr add 10.0.0.1/24 dev eth0
nsenter --net=/var/run/netns/ns2 ip addr add 10.0.0.2/24 dev eth0

nsenter --net=/var/run/netns/ns2 ../../../../src/bpf/xdp_pass/build/xdp_pass_user eth0

nsenter --net=/var/run/netns/ns1 ip link set dev eth0 up
nsenter --net=/var/run/netns/ns2 ip link set dev eth0 up

nsenter --net=/var/run/netns/ns1 /bin/sh -c "echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6"
nsenter --net=/var/run/netns/ns2 /bin/sh -c "echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6"

# nsenter --net=/var/run/netns/ns1 wireshark -k -i eth0 &
nsenter --net=/var/run/netns/ns2 wireshark -k -i eth0 &

echo "Run the following commands inside 'h2'"
echo "nfvctl vnf add vnf-echo 1234 5678 '--raw -d 1 -m TEST eth0'"
echo "tell.py -l 1234 eth0 10.0.0.1"

xterm -xrm 'XTerm.vt100.allowTitleOps: false' -T h1 -e 'nsenter --net=/var/run/netns/ns1 nfvctl init worker eth0' &
xterm -xrm 'XTerm.vt100.allowTitleOps: false' -T h2 -e 'nsenter --net=/var/run/netns/ns2'

ip netns delete ns1
ip netns delete ns2
