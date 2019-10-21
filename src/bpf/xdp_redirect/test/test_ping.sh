#!/bin/sh

set -e
set -x

ip netns add ns1
ip netns add ns2

ip link add name h1-eth0 type veth peer name eth0 netns ns1
ip link add name h2-eth0 type veth peer name eth0 netns ns2

ip a add 10.0.2.11/24 dev h1-eth0
ip link set dev h1-eth0 up

ip a add 10.0.3.11/24 dev h2-eth0
ip link set dev h2-eth0 up

nsenter --net=/var/run/netns/ns1 ip a add 10.0.1.11/24 dev eth0
nsenter --net=/var/run/netns/ns1 ip link set dev eth0 up

nsenter --net=/var/run/netns/ns2 ip a add 10.0.1.12/24 dev eth0
nsenter --net=/var/run/netns/ns2 ip link set dev eth0 up

ulimit -l 8192  # otherwise loading of xdp progs would fail

../build/xdp_redirect_user h1-eth0 h2-eth0
../build/xdp_redirect_user h2-eth0 h1-eth0

nsenter --net=/var/run/netns/ns1 ../../xdp_pass/build/xdp_pass_user eth0
nsenter --net=/var/run/netns/ns2 ../../xdp_pass/build/xdp_pass_user eth0

nsenter --net=/var/run/netns/ns1 ping -c 3 10.0.1.12

ip netns delete ns1
ip netns delete ns2
