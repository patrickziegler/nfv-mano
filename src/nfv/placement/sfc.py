# Copyright (C) 2019 Patrick Ziegler
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import importlib
import json
import random


def get_id():
    return random.randint(0, 0xfffff)  # mpls labels are 20 bit


class ServiceHook:

    def __init__(self, src_ip, dst_ip, src_dp=None, dst_dp=None):
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_dp = src_dp
        self.dst_dp = dst_dp

    def __eq__(self, other):
        try:
            if self.src_ip == other.src_ip and self.dst_ip == other.dst_ip:
                return True
            else:
                return False
        except AttributeError:
            return False

    def as_dict(self):
        return {
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_dpid": self.src_dp.id,
            "dst_dpid": self.dst_dp.id,
        }

    @classmethod
    def from_json(cls, msg):
        nsd = json.loads(msg)
        return cls(
            src_ip=nsd["hook"]["src_ip"],
            dst_ip=nsd["hook"]["dst_ip"],
        )


class ServiceFunction:

    def __init__(self, image, label_in, label_out=None, param=None,
                 public=False, immediate=True, timeout=30):
        if label_out is None:
            label_out = get_id()
        self.image = image
        self.label_in = label_in
        self.label_out = label_out
        self.param = param
        self.public = public
        self.immediate = immediate
        self.timeout = timeout
        self.node_id = None
        self.iface = None
        self.port = None
        self.container = None
        self.removed = None

    def as_dict(self, slim=False):
        data = {
            "image": self.image,
            "label_in": self.label_in,
            "label_out": self.label_out,
            "param": self.param,
            "public": self.public,
            "immediate": self.immediate,
            "timeout": self.timeout,
        }
        if not slim:
            data.update({
                "node_id": self.node_id,
                "iface": self.iface,
                "port": self.port,
                "removed": self.removed,
            })
        return data

    def as_json(self, **kwargs):
        return json.dumps(self.as_dict(slim=True), **kwargs)

    @classmethod
    def from_json(cls, msg):
        param = json.loads(msg)
        obj = cls(**param)
        return obj


class ServiceFunctionChain:

    def __init__(self, hook, placement, immediate, timeout):
        self.label = get_id()
        self.hook = hook
        self.placement = placement
        self.immediate = immediate
        self.timeout = timeout
        self.jobs = []

    def embedding(self, model):
        self.placement.prepare(model)
        self.placement.calc()
        for i in range(len(self.placement.paths) - 1):
            self.jobs[i].node_id = self.placement.paths[i][-1]

    def get_paths(self):
        labels = [self.label, *[e.label_out for e in self.jobs]]
        for i, path in enumerate(self.placement.paths):
            yield labels[i], path

    def get_vnfs(self):
        for vnf in self.jobs:
            yield vnf

    def as_dict(self):
        return {
            "label": self.label,
            "hook": self.hook.as_dict(),
            "placement": {
                "paths": self.placement.paths,
                "expected_latency": self.placement.expected_latency,
            },
            "immediate": self.immediate,
            "timeout": self.timeout,
            "jobs": [job.as_dict() for job in self.jobs],
        }

    @classmethod
    def from_json(cls, msg, ip_to_dp):
        nsd = json.loads(msg)
        nsd.setdefault("placement", {})
        nsd["placement"].setdefault("immediate", False)
        nsd["placement"].setdefault("timeout", 30)
        nsd["placement"].setdefault("algorithm", {"name": "RandomPlacement", "kwargs": {}})
        nsd["placement"]["algorithm"].setdefault("kwargs", {})
        hook = ServiceHook(
            src_ip=nsd["hook"]["src_ip"],
            dst_ip=nsd["hook"]["dst_ip"],
            src_dp=ip_to_dp[nsd["hook"]["src_ip"]],
            dst_dp=ip_to_dp[nsd["hook"]["dst_ip"]],
        )
        placement_cls = getattr(
            importlib.import_module("nfv.placement.algo"),
            nsd["placement"]["algorithm"]["name"]
        )
        placement = placement_cls(
            node_src=ip_to_dp[nsd["hook"]["src_ip"]].id,
            node_dst=ip_to_dp[nsd["hook"]["dst_ip"]].id,
            chain_length=len(nsd["jobs"]),
            **nsd["placement"]["algorithm"]["kwargs"],
        )
        sfc = ServiceFunctionChain(
            hook=hook,
            placement=placement,
            immediate=nsd["placement"]["immediate"],
            timeout=nsd["placement"]["timeout"],
        )
        last_label = sfc.label
        for job in nsd["jobs"]:
            job.setdefault("param", None)
            job.setdefault("public", False)
            vnf = ServiceFunction(
                image=job["name"],
                label_in=last_label,
                label_out=get_id(),
                param=job["param"],
                public=job["public"],
                immediate=sfc.immediate,
                timeout=round(1.1 * sfc.timeout),  # +10% timeout for safety
            )
            sfc.jobs.append(vnf)
            last_label = vnf.label_out
        return sfc
