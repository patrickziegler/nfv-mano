#!/bin/sh

set -x

ip netns add ns1
ip netns add ns2
ip netns add ns3

ip link add name eth0 netns ns1 type veth peer name eth0 netns ns2
ip link add name eth1 netns ns2 type veth peer name eth0 netns ns3
ip link add name ctl0 netns ns2 type veth peer name ns2-ctl0

ip a add 11.0.0.1/8 dev ns2-ctl0
ip link set dev ns2-ctl0 up

# -- ns1

nsenter --net=/var/run/netns/ns1 ip a add 10.1.0.11/8 dev eth0

nsenter --net=/var/run/netns/ns1 ip link set dev lo up
nsenter --net=/var/run/netns/ns1 ip link set dev eth0 up

# -- ns2

nsenter --net=/var/run/netns/ns2 ip a add 11.0.0.2/8 dev ctl0

nsenter --net=/var/run/netns/ns2 ip link set dev lo up
nsenter --net=/var/run/netns/ns2 ip link set dev ctl0 up
nsenter --net=/var/run/netns/ns2 ip link set dev eth0 up
nsenter --net=/var/run/netns/ns2 ip link set dev eth1 up

nsenter --net=/var/run/netns/ns2 ip route add 11.0.0.0/8 dev ctl0

# -- ns3

nsenter --net=/var/run/netns/ns3 ip a add 10.1.0.12/8 dev eth0

nsenter --net=/var/run/netns/ns3 ip link set dev lo up
nsenter --net=/var/run/netns/ns3 ip link set dev eth0 up
