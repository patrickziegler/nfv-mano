# nfv-mano

## Getting started

### Prerequisites

The following packages are needed:

* `python` (>= 3.5)
* `setuptools`
* `virtualenv` (for local deployment)
* `docker`
* `openvswitch`
* `iperf`
* `net-tools-deprecated` (`ifconfig` etc. for mininet)

### :hammer: Build and Install

1. Clone this repository
```bash
git clone --recurse-submodules git@git.comnets.net:patrickziegler/nfv-mano.git
cd nfv-mano
```

2. Create and activate a virtual environment
```bash
python3 -m virtualenv .virtualenv --system-site-packages
source .virtualenv/bin/activate
```

3. Install mininet from submodule
```bash
cd extern/mininet
make mnexec
mv -v mnexec ../../.virtualenv/bin
python setup.py develop
```

4. Build and install the package and its dependencies (in virtual environment)
```bash
pip install -r requirements.txt
python setup.py develop
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
