#!/bin/bash
#
# [1] https://techandtrains.com/2014/02/08/running-open-vswitch-in-network-namespace/

if [ "$#" -lt 1 ]; then
    echo "Usage: $0/ovsns_init.sh NETNS"
    exit
fi

echo "Starting OVS in netns $1"

tmpdir=/tmp/ovsns-$1

if [ -e "${tmpdir}/conf.db" ]; then
   echo "Database '${tmpdir}/conf.db' already exists"
   exit
fi

mkdir -p "${tmpdir}"

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
--detach \
#--monitor

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
--detach \
#--monitor
