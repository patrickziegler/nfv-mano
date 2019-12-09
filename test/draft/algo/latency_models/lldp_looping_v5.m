RTT = 10;

ts = 0:1:RTT;
tr = RTT - ts;

toffs = -100:20:100;

fun1 = @(toffs) 1 ./ (1 + tr ./ ts) + toffs ./ (ts + tr);
fun2 = @(toffs) 1 ./ (2 * (1 + tr ./ ts)) - 1 ./ (2 * (1 + ts ./ tr));
fun3 = @(ts, tr) (ts - tr) ./ (2 * (ts + tr));

figure();
for i = 1:length(toffs)
    plot(100 * (ts - tr) / RTT, -100 * fun3(ts, tr)); hold on;
    plot(100 * (ts - tr) / RTT,  100 * fun3(ts, tr)); hold on;
end

grid on;
