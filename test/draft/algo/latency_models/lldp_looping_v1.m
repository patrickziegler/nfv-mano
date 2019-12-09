function roundhouse
funcs = {
    'model_1_eval', ...
    };

for i = 1:length(funcs)
    label = funcs{i};
    fn = str2func(label);
    fn();
end
end

function parm = create_parm(q1, q2, q3)
parm = struct();
parm.RTT1 = 50e-3;
parm.RTT2 = 50e-3;
parm.RTT3 = 100e-3;
parm.t11 = q1 * parm.RTT1;
parm.t12 = parm.RTT1 - parm.t11;
parm.t21 = q2 * parm.RTT2;
parm.t22 = parm.RTT2 - parm.t21;
parm.t31 = q3 * parm.RTT3;
parm.t32 = parm.RTT3 - parm.t31;
end

function meas = create_meas(parm)
meas = struct();
meas.RTT1 = parm.t11 + parm.t12;
meas.RTT2 = parm.t21 + parm.t22;
meas.RTT3 = parm.t11 + parm.t31 + parm.t22;
meas.RTT4 = parm.t21 + parm.t32 + parm.t12;
end

function sol = model_1(meas)
A = [
    2 0 0 0;
    0 2 0 0;
    1 1 1 0;
    1 1 0 1;
    ];
b = [
    meas.RTT1;
    meas.RTT2;
    meas.RTT3;
    meas.RTT4;
    ];
x = A \ b;
sol = struct();
sol.t11 = x(1);
sol.t12 = x(1);
sol.t21 = x(2);
sol.t22 = x(2);
sol.t31 = x(3);
sol.t32 = x(4);
end

function model_1_eval_2d()
q1 = 0:.01:1;
q2 = 0:.01:1;
Dt31 = NaN(length(q1), length(q2));
Dt32 = NaN(length(q1), length(q2));
td1 = NaN(length(q1), 1);
td2 = NaN(length(q2), 1);
for i = 1:length(q1)
    for j = 1:length(q2)
        parm = create_parm(q1(i), q2(j), 0.3);
        meas = create_meas(parm);
        sol = model_1(meas);
        Dt31(i,j) = 100 * (sol.t31 - parm.t31) / parm.t31;
        Dt32(i,j) = 100 * (sol.t32 - parm.t32) / parm.t32;
        td1(i) = (parm.t11 - parm.t12) / parm.RTT1;
        td2(j) = (parm.t21 - parm.t22) / parm.RTT2;
    end
end
lim = [-33, 33];
figure();
surf(td1, td2, Dt31);
zlim(lim);
set(gca, 'clim', lim);
view(90, -90);
colorbar();
shading flat;
colormap winter;
end

function model_1_eval()
q = 0:.1:1;
Dt31 = NaN(length(q), 1);
Dt32 = NaN(length(q), 1);
td = NaN(length(q), 1);
for i = 1:length(q)
    q1 = q(i);
    q2 = 1 - q(i);
    parm = create_parm(q1, q2, 0.5);
    meas = create_meas(parm);
    sol = model_1(meas);
    Dt31(i) = 100 * (sol.t31 - parm.t31) / parm.t31;
    Dt32(i) = 100 * (sol.t32 - parm.t32) / parm.t32;
    td(i) = (parm.t11 - parm.t12) / parm.RTT1;
end
figure();
plot(td, Dt31); hold on;
plot(td, Dt32);
grid on;
ylim([-33, 33]);
end
