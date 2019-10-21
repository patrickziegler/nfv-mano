function lldp_looping_v3
funcs = {
    'model_1_eval', ...
    'model_2_eval', ...
    };

for i = 1:length(funcs)
    label = funcs{i};
    fn = str2func(label);
    fn();
end
end

function meas = create_measurement(parm)
meas = struct();
meas.t10 = parm.t0;
meas.t20 = parm.ts + parm.toffs + parm.t0;
meas.t11 = parm.t0 + parm.ts + parm.tr;
meas.t21 = 2*parm.ts + parm.tr + parm.t0 + parm.toffs;
end

function res = parmdiff(parm, sol, fn)
if nargin < 3
    fn = @(x) x;
end
res = struct();
res.ts = fn(parm.ts - sol.ts);
res.tr = fn(parm.tr - sol.tr);
res.toffs = fn(parm.toffs - sol.toffs);
res.t0 = fn(parm.t0 - sol.t0);
end

% function [D, td, toffs] = eval_model(fn)
% t0 = 11;
% ts = 0;
% tr = 10e-3:.01e-3:10e-3;
% td = tr - ts;
% toffs = -100:1:100;
% parm = struct();
% parm.t0 = t0;
% parm.ts = ts;
% meas = struct();
% meas.t10 = parm.t0;
% D = NaN(length(toffs), length(tr));
% for i = 1:length(tr)
%     for j = 1:length(toffs)
%         parm.tr = tr(i);
%         parm.toffs = toffs(j);
%         meas.t20 = parm.t0 + parm.ts + parm.toffs;
%         meas.t11 = parm.t0 + parm.ts + parm.tr;
%         meas.t21 = parm.t0 + 2*parm.ts + parm.tr + parm.toffs;
%         sol = fn(meas);
%         res = parmdiff(parm, sol);
%         D(j,i) = res.tr;
%     end
% end
% end

function sol = model_1(meas)
toffs = 0;
A = [
    0 0 1;
    1 0 1;
    1 1 1;
    ];
b = [
    meas.t10;
    meas.t20 - toffs;
    meas.t11;
    ];
x = A \ b;
sol = struct();
sol.ts = x(1);
sol.tr = x(2);
sol.toffs = toffs;
sol.t0 = x(3);
end

function model_1_eval()
parm = struct();
parm.t0 = 11;
parm.ts = 210e-3;
parm.tr = 210e-3;
RTT = parm.ts + parm.tr;
toffs = -RTT/2:10e-3:RTT/2;
Dts = NaN(length(toffs), 1);
Dtr = NaN(length(toffs), 1);
for i = 1:length(toffs)
    parm.toffs = toffs(i);
    meas = create_measurement(parm);
    sol = model_1(meas);
    res = parmdiff(parm, sol);
    Dts(i) = 100 * (res.ts - parm.ts) / RTT;
    Dtr(i) = 100 * (res.tr - parm.tr) / RTT;
end
td = toffs / RTT;
figure();
plot(td, Dts); hold on;
plot(td, Dtr);
xlim([-0.5, 0.5]);
ylim([-110, 110]);
legend("\Delta ts", "\Delta tr");
title("Assuming t_{offs} = 0");
xlabel("t_{offs} / RTT");
ylabel("Error / %");
grid on;
end

function sol = model_2(meas)
A = [
    0 0 1;
    1 1 1;
    2 0 1;
    ];
b = [
    meas.t10;
    meas.t20;
    meas.t11;
    ];
x = A \ b;
sol = struct();
sol.ts = x(1);
sol.tr = x(1);
sol.toffs = x(2);
sol.t0 = x(3);
end

function model_2_eval()
RTT = 100e-3;
dt = 1e-3;
ts = 0:dt:RTT;
tr = RTT - ts;
parm = struct();
parm.t0 = 11;
parm.toffs = 13e-3;
Dts = NaN(length(ts), 1);
Dtr = NaN(length(tr), 1);
for i = 1:length(ts)
    parm.ts = ts(i);
    parm.tr = tr(i);
    meas = create_measurement(parm);
    sol = model_2(meas);
    res = parmdiff(parm, sol);
    Dts(i) = 100 * (res.ts - parm.ts) / RTT;
    Dtr(i) = 100 * (res.tr - parm.tr) / RTT;
end
td = (ts - tr) / RTT;
figure();
plot(td, Dts); hold on;
plot(td, Dtr);
xlim([-0.5, 0.5]);
ylim([-110, 110]);
legend("\Delta ts", "\Delta tr");
title("Assuming t_s - t_r = 0");
xlabel("(t_s - t_r) / RTT");
ylabel("Error / %");
grid on;
end
