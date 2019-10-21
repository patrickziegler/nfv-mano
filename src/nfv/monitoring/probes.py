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

import os
import time

CGROUP_BASEDIR = "/proc/1/root/sys/fs/cgroup"


def get_cgroup_dir(name):
    with open("/proc/self/cgroup") as fp:
        for line in fp.readlines():
            if name in line:
                path = os.sep.join((CGROUP_BASEDIR, name, line.split(":")[-1].rstrip()))
                if os.path.exists(path):
                    return path
    raise FileExistsError("Could not find cgroup info '%s'" % name)


class ProbeProcessorCore:

    PROC_STAT_KEYS = (
        "user",
        "nice",
        "system",
        "idle",
        "iowait",
        "irq",
        "softirq",
        "steal",
        "guest",
        "guest_nice"
    )

    def __init__(self, key, stat):
        self.key = key
        self.stat = stat

    def __sub__(self, other):
        if self.key != other.key:
            raise KeyError
        obj = self.__class__(self.key, {**self.stat})
        for key in self.PROC_STAT_KEYS:
            obj.stat[key] -= other.stat[key]
        return obj

    def get(self):
        cpu_busy = 0
        for key in ("user", "nice", "system", "irq", "softirq", "steal"):
            cpu_busy += self.stat[key]
        util = 100 * cpu_busy / (cpu_busy + self.stat["idle"] + self.stat["iowait"])
        return round(10**2 * util) / 10**2

    @classmethod
    def from_line(cls, line):
        words = [word for word in line.split(" ") if word != ""]
        stat = dict.fromkeys(cls.PROC_STAT_KEYS)
        for i, key in enumerate(cls.PROC_STAT_KEYS):
            stat[key] = int(words[i + 1])
        return cls(key=words[0], stat=stat)


class ProbeProcessor:

    @classmethod
    def read(cls):
        with open("/proc/stat") as fp:
            for line in fp.readlines():
                if line.startswith("cpu"):
                    yield ProbeProcessorCore.from_line(line)

    def __init__(self):
        self.proc_stat = {}
        for stat in self.read():
            self.proc_stat[stat.key] = stat

    def get(self, rebase=True):
        proc_rel = dict.fromkeys(self.proc_stat)
        for s in self.read():
            proc_rel[s.key] = s - self.proc_stat[s.key]
            if rebase:
                self.proc_stat[s.key] = s
        proc_util = dict.fromkeys(proc_rel)
        for key in proc_rel:
            proc_util[key] = proc_rel[key].get()
        return proc_util


class ProbeProcessorCgroup:

    def __init__(self):
        self.last_ts = 0
        self.last_stat = {}
        self.cgroup_dir = get_cgroup_dir("cpu,cpuacct")

    def read_usage(self):
        with open(self.cgroup_dir + "/cpuacct.usage") as fp:
            return {"cpu": int(fp.read())}

    def read_usage_percpu(self):
        with open(self.cgroup_dir + "/cpuacct.usage_percpu") as fp:
            return {"cpu%d" % i: int(value) for i, value in enumerate(fp.read().split())}

    def read_quota(self):
        with open(self.cgroup_dir + "/cpu.cfs_quota_us") as fp:
            cfs_quota = int(fp.read())
        with open(self.cgroup_dir + "/cpu.cfs_period_us") as fp:
            cfs_period = int(fp.read())
        return cfs_quota / cfs_period

    def get(self, rebase=True):
        q = self.read_quota()
        if q <= 0:
            q = 1
        ts = time.time_ns()
        stat = {**self.read_usage(), **self.read_usage_percpu()}
        stat_rel = dict(stat)
        stat_rel.update(self.last_stat)
        stat_rel = {k: 100 * (v - stat_rel[k]) / (q * (ts - self.last_ts))
                    for k, v in stat.items()}
        if rebase:
            self.last_stat = stat
            self.last_ts = ts
        return stat_rel


class ProbeMemory:

    def get(self):
        with open("/proc/meminfo") as fp:
            for line in fp.readlines():
                if line.startswith("MemAvailable"):
                    words = [word for word in line.split(" ") if word != ""]
                    return {"ram": int(words[-2]) * 1024}
        return {"ram": None}


class ProbeMemoryCgroup(ProbeMemory):

    PAGE_COUNTER_MAX = 9223372036854771712

    MEM_STAT_KEYS = (
        "cache",
        "rss",
        "rss_huge",
        "inactive_anon",
        "inactive_file"
    )

    def get(self):
        stat = dict.fromkeys(self.MEM_STAT_KEYS)
        path = get_cgroup_dir("memory")

        with open(path + "/memory.limit_in_bytes") as fp:
            mem_limit = int(fp.readline())

        if mem_limit == self.PAGE_COUNTER_MAX:
            return super().get()

        with open(path + "/memory.stat") as fp:
            for line in fp.readlines():
                words = line.split(" ")
                if words[0] in self.MEM_STAT_KEYS:
                    stat[words[0]] = int(words[1])

        mem_used = (stat["cache"] + stat["rss"] + stat["rss_huge"]
                    - stat["inactive_anon"] - stat["inactive_file"])

        return {"ram": mem_limit - mem_used}


if __name__ == "__main__":
    import json
    try:
        cpu = ProbeProcessorCgroup()
        ram = ProbeMemoryCgroup()
        while True:
            time.sleep(0.5)
            info = {
                **cpu.get(),
                **ram.get(),
            }
            print(json.dumps(info, indent=4))
    except KeyboardInterrupt:
        pass
