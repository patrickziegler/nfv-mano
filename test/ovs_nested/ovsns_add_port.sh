#!/bin/bash

if [ "$#" -lt 3 ]; then
    echo "Usage: $0/ovsns_add_port.sh NETNS BRIDGE IFACE"
    exit
fi

echo "Adding iface $3 to bridge $2 in netns $1"

tmpdir=/tmp/ovsns-$1

ovs-vsctl --db=unix:${tmpdir}/db.sock add-port $2 $3
