import numpy as np
import matplotlib.pyplot as plt
from tools import op

for rl in (6e3,):
    v = op(f"* D1\nV1 in 0 12\nR1 in out 4k\nR2 out 0 12k\nRL out 0 {rl}")
    print(f"RL = {rl:.0f} ohm: v(out) = {v['v(out)']:.3f} V, I_L = {v['v(out)'] / rl * 1e3:.3f} mA")

# Sweep the load and plot the line V = Vth - Rth * I
rls = np.geomspace(100, 1e6, 30)
vs = np.array([op(f"* D1\nV1 in 0 12\nR1 in out 4k\nR2 out 0 12k\nRL out 0 {r}")["v(out)"] for r in rls])
i = vs / rls
slope, icpt = np.polyfit(i, vs, 1)
print(f"fitted line: Vth = {icpt:.3f} V, Rth = {-slope:.1f} ohm")
plt.plot(i * 1e3, vs, "o")
plt.xlabel("load current, mA"); plt.ylabel("v(out), V"); plt.grid(alpha=0.3)
plt.savefig("d1.png")   