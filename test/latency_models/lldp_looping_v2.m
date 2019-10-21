function [parm, meas, sol] = lldp_looping_v2
parm = create_parameter();
meas = create_measurement(parm);

funcs = {
    'model_1', ...
    'model_2', ...
    'model_3', ...
    };

for i = 1:length(funcs)
    label = funcs{i};
    fh = str2func(label);
    sol = fh(meas);
    fprintf('Solution for ''%s'':\n', label);
    disp(sol);
end
end

function param = create_parameter()
param = struct();
param.ts = 160e-3;
param.tr = 130e-3;
param.toffs = 10e-3;
param.t0 = 10;
end

function meas = create_measurement(parm)
meas = struct();
meas.t10 = parm.t0;
meas.t20 = parm.ts + parm.toffs + parm.t0;
meas.t11 = parm.t0 + parm.ts + parm.tr;
meas.t21 = 2*parm.ts + parm.tr + parm.t0 + parm.toffs;
end

function x = model_1(meas)
A = [
    1 0 1;
    1 1 0;
    2 1 1;
    ];
b = [
    meas.t20 - meas.t10;
    meas.t11 - meas.t10;
    meas.t21 - meas.t10;
    ];
x = A \ b;
end

function x = model_2(meas)
A = [
    1 0 1;
    1 1 0;
    2 1 1;
    0.5 -0.5 1
    ];
b = [
    meas.t20 - meas.t10;
    meas.t11 - meas.t10;
    meas.t21 - meas.t10;
    meas.t20 - (meas.t10 + meas.t11) / 2
    ];
x = A \ b;
end

function x = model_3(meas)
% this only works when ts == tr
toffs = (2*meas.t20 - meas.t10 - meas.t11) / 2;
A = [
    1 0 1;
    1 1 1;
    2 1 1;
    ];
b = [
    meas.t20 - toffs;
    meas.t11;
    meas.t21 - toffs;
    ];
x = A \ b;
end
