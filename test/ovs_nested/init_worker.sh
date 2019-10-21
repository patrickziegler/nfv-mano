#!/bin/sh

set -e
set -x

XDP_DIR=$(realpath "$(readlink -f "$0" | xargs dirname)/../../")

host=$1
netns="$host-ns1"

tmpdir=$(mktemp -d -t nfvmano-XXXXXXXXXX)

function nsexec() {
    nsenter --net="/var/run/netns/$netns" $@
}

function create_link() {
    ip link add name "sw-$1" type veth peer name "$1" netns "$netns"
    ip address add "$2" dev "sw-$1"
    ip link set dev "sw-$1" up
    nsexec ip address add "$3" dev "$1"
    nsexec ip link set dev "$1" up
}

function init_ovs {
    ovsdb-tool create \
        "${tmpdir}/conf.db" \
        /usr/share/openvswitch/vswitch.ovsschema

    ovsdb-server "${tmpdir}/conf.db" \
        -vconsole:emer \
        -vsyslog:err \
        -vfile:info \
        --remote=punix:"${tmpdir}/db.sock" \
        --private-key=db:Open_vSwitch,SSL,private_key \
        --certificate=db:Open_vSwitch,SSL,certificate \
        --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert \
        --log-file="${tmpdir}/ovsdb-server.log" \
        --pidfile="${tmpdir}/ovsdb-server.pid" \
        --no-chdir \
        --detach

    ovs-vsctl \
        --db=unix:"${tmpdir}/db.sock" \
        --no-wait \
        init

    ovs-vswitchd unix:"${tmpdir}/db.sock" \
        -vconsole:emer \
        -vsyslog:err \
        -vfile:info \
        --log-file="${tmpdir}/ovs-vswitchd.log" \
        --pidfile="${tmpdir}/ovs-vswitchd.pid" \
        --mlockall \
        --no-chdir \
        --detach
}

ip netns add "${netns}"

create_link ctrl 10.1.0.1/28 10.1.0.2/28
create_link data 10.2.0.1/28 10.2.0.2/28

eval "$XDP_DIR/xdp_node_ingress/build/xdp_node_ingress_user" "$host-eth0" sw-data
eval "$XDP_DIR/xdp_node_egress/build/xdp_node_egress_user" sw-data "$host-eth0"

mode=secure

ovs-vsctl --db=unix:${tmpdir}/db.sock add-br $2
ovs-vsctl --db=unix:${tmpdir}/db.sock set-fail-mode $2 "${mode}"
ovs-vsctl --db=unix:${tmpdir}/db.sock add-port $2 eth0
ovs-vsctl --db=unix:${tmpdir}/db.sock add-port $2 eth1
ovs-vsctl --db=unix:${tmpdir}/db.sock set-controller $2 tcp:11.0.0.1:6633
ovs-vsctl --db=unix:${tmpdir}/db.sock show
ovs-vsctl --db=unix:${tmpdir}/db.sock add-port $2 $3
