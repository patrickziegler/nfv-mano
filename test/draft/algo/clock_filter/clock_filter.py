import random
import numpy as np
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt


class LatencyEnviroment:

    def __init__(self, toffs=0.0, rtt=(30e-3, 5e-3), asym=(0, 0.2), dt=(100e-3, 30e-3)):
        self.toffs = toffs
        self.rtt = rtt
        self.asym = asym
        self.dt = dt
        self.t = 0

    def __next__(self):
        rtt = random.gauss(*self.rtt)
        asym = random.gauss(*self.asym)
        if abs(asym) > 1:
            asym /= abs(asym)
        self.t += random.gauss(*self.dt)
        return rtt, asym

    def __iter__(self):
        return self


class LatencyMeasurement:

    def __init__(self, env: LatencyEnviroment):
        self.rtt, self.asym = next(env)
        self.data = {
            "T1": env.t,
            "T2": env.t + self.get_ts() + env.toffs,
            "T3": env.t + self.rtt,
            "T4": env.t + self.rtt + self.get_tr() + env.toffs
        }

    def __str__(self):
        return " ".join((
            "[Measurement]",
            "rtt:",
            str(self.rtt),
            "ts:",
            str(self.get_ts()),
            "tr:",
            str(self.get_tr()),
            "data:",
            str(self.data)
        ))

    def get_ts(self):
        return self.rtt * (-self.asym / 2 + 0.5)

    def get_tr(self):
        return self.rtt * (self.asym / 2 + 0.5)


class ClockFilter:

    def __init__(self):
        self.first = None
        self.data = list()

    @staticmethod
    def calc_theta(T1, T2, T3):
        return (2 * T2 - T1 - T3) / 2

    @staticmethod
    def calc_toffs(x1, y1, x2, y2):
        return ((y1 - y2) / (x2 - x1)) * x1 + y1

    def update(self, meas: LatencyMeasurement):
        if self.first is None:
            self.first = meas
        rtt = meas.data["T3"] - self.first.data["T1"]
        theta_tr = self.calc_theta(T1=self.first.data["T1"], T2=meas.data["T2"], T3=meas.data["T3"])
        theta_ts = self.calc_theta(T1=self.first.data["T1"], T2=self.first.data["T2"], T3=meas.data["T3"])
        if len(self.data) > 0:
            toffs_ts = self.calc_toffs(self.data[-1][1], self.data[-1][3], rtt, theta_ts)
            toffs_tr = self.calc_toffs(self.data[-1][1], self.data[-1][4], rtt, theta_tr)
        else:
            toffs_ts = 0
            toffs_tr = 0
        self.data.append((
            meas.rtt,
            rtt,
            self.calc_theta(T1=meas.data["T1"], T2=meas.data["T2"], T3=meas.data["T3"]),
            theta_ts,
            theta_tr,
            toffs_ts,
            toffs_tr
        ))

    def plot(self):
        data = np.asarray(self.data)
        a = np.ones(shape=(data.shape[0], 2))
        a[:, 0] = data[:, 1]
        c, _, _, _ = np.linalg.lstsq(a, data[:, 4], rcond=None)
        print("toffs:\t%f" % c[1])
        plt.figure()
        plt.subplot(3, 1, 1)
        plt.scatter(data[:, 1], data[:, 4])
        plt.scatter(data[:, 1], data[:, 3])
        plt.scatter(data[:, 0], data[:, 2])
        plt.plot(data[:, 1], data[:, 1] * c[0] + c[1], "grey")
        plt.subplot(3, 1, 2)
        plt.plot(data[:, 6])
        plt.subplot(3, 1, 3)
        plt.plot(data[:, 5])
        plt.ylim(50e-3, 150e-3)
        plt.show()


if __name__ == "__main__":
    env = LatencyEnviroment(toffs=100e-3, rtt=(30e-3, 5e-3), asym=(0, 10), dt=(100000, 10e-3))
    filt = ClockFilter()
    for i in range(100):
        meas = LatencyMeasurement(env)
        filt.update(meas)
    filt.plot()
