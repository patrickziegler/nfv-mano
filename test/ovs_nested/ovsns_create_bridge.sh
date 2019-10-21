#!/bin/bash

if [ "$#" -lt 2 ]; then
    echo "Usage: $0/ovsns_create_bridge.sh NETNS BRIDGE"
    exit
fi

echo "Creating bridge $2 in netns $1"

tmpdir=/tmp/ovsns-$1
# mode=standalone
mode=secure

ovs-vsctl --db=unix:${tmpdir}/db.sock add-br $2
ovs-vsctl --db=unix:${tmpdir}/db.sock set-fail-mode $2 "${mode}"
ovs-vsctl --db=unix:${tmpdir}/db.sock add-port $2 eth0
ovs-vsctl --db=unix:${tmpdir}/db.sock add-port $2 eth1
ovs-vsctl --db=unix:${tmpdir}/db.sock set-controller $2 tcp:11.0.0.1:6633
ovs-vsctl --db=unix:${tmpdir}/db.sock show
