function ret = test
t0 = 10;
ts = 12;
tr = 15;
toffs = 30;
T1 = 10;
T2 = t0 + ts + tr;
T3 = t0 + ts + toffs;
T4 = (2*T1 - T3):(2*T2 - T3);
x = cell(length(T4), 1);
for i = 1:length(T4)
    x{i} = model1(T1, T2, T3, T4(i));
end
ret = struct();
ret.data = cell2mat(x);
ret.time = T4';
ret.T3 = T3;
ret.T2 = T2;
ret.T1 = T1;
plot_model(ret);
end

function x = model1(T1, T2, T3, T4)
A = [1 0 1; 0 1 1; 1 1 0];
b = [T3 - T1; T2 - T4; T2 - T1];
x = (A \ b)';
end

function plot_model(ret)
figure();
plot(ret.time, ret.data(:,1)); hold on
plot(ret.time, ret.data(:,2));
plot(ret.time, ret.data(:,3));
plot(ret.time, ret.time, 'Color', 0.85 * ones(3,1));
grid on;
legend("t_s", "t_r", "t_{offs}", "T_4");
% ylim([-100, 100]);
end
