# :bulb: nfv-mano

## Getting started

### Prerequisites

The following packages are needed:

* `clang` (incl. `libclang`)
* `python` (>= 3.5, incl. `virtualenv` and `setuptools`)
* `net-tools-deprecated` (`ifconfig` etc. for mininet)
* `openvswitch`
* `docker`

### :hammer: Build and Install

1. Clone and bootstrap this repository (as unpriviliged user)
```bash
git clone https://github.com/patrickziegler/nfv-mano.git
cd nfv-mano
./bootstrap.sh
```

2. Become super user and activate the virtual environment
```bash
su
source venv
```

### Usage

Before executing the scripts, some services may be invoked first:
```bash
service openvswitch start
service docker start
```

If starting `openvswitch` fails due to missing `/var/run/openvswitch/db.sock` or similar, it may be necessary to start the `ovsdb` server manually with the following command:
```bash
/usr/share/openvswitch/scripts/ovs-ctl start --system-id
```

## Authors

*  Patrick Ziegler

## License

This project is licensed under the GPL - see the [LICENSE](LICENSE) file for details
