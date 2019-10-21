#!/bin/sh

set -x

vnf_image=vnf-echo
vnf_name=${vnf_image}-1
vnf_args="--raw -m vnf1 -d 1 eth0"

docker run --network none --name ${vnf_name} -d ${vnf_image} ${vnf_args}
vnf_pid="$(docker inspect -f '{{.State.Pid}}' ${vnf_name})"

ln -sf /proc/${vnf_pid}/ns/net /var/run/netns/ns1
ip netns add ns2

ip link add eth0 netns ${vnf_pid} type veth peer name eth0 netns ns2

nsenter -at ${vnf_pid} /bin/sh -c "echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6"
nsenter --net=/var/run/netns/ns2 /bin/sh -c "echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6"

nsenter -at ${vnf_pid} ip addr add 10.1.0.10/8 dev eth0
nsenter --net=/var/run/netns/ns2 ip addr add 10.1.0.11/8 dev eth0

nsenter -at ${vnf_pid} ip link set dev eth0 up
nsenter --net=/var/run/netns/ns2 ip link set dev eth0 up

# nsenter -t ${vnf_pid} wireshark -k -i eth0 &
nsenter --net=/var/run/netns/ns2 wireshark -k -i eth0 &

# xterm -xrm 'XTerm.vt100.allowTitleOps: false' -T h1 -e "nsenter -at ${vnf_pid} /bin/sh" &
xterm -xrm 'XTerm.vt100.allowTitleOps: false' -T h2 -e "nsenter --net=/var/run/netns/ns2 python loop.py"

docker kill ${vnf_name}
docker rm ${vnf_name}

ip netns delete ns1
ip netns delete ns2
