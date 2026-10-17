"""Sweep how early the data arrives; measure clock-to-Q; find setup and hold."""
# ---------------------------------------------------------------------------------
# Uses dff.py as a toolbox: each dff.run() is a fresh ngspice simulation of the same
# flip-flop with the data edge at a different time. Two experiments:
#   1. setup: D rises earlier and earlier before the edge; plot t_cq against it.
#      Setup time = the latest arrival whose t_cq is still within 10 % of normal.
#   2. hold: D falls around the edge; does the flip-flop keep D's old 1 or catch the new 0?
# ---------------------------------------------------------------------------------
import numpy as np
import matplotlib.pyplot as plt
import dff       # loads dff.py from this folder; its functions become dff.run, dff.tcq ...

# setup: data rises 0 -> 1 this many ps before the clock edge
setups = [300, 200, 150, 100, 90, 80, 75, 70, 65, 60, 55, 52, 50, 48, 47, 46, 45, 40]
tcqs = []
for s in setups:
    t, q, m1, m2 = dff.run(dff.T_EDGE - s * 1e-12)     # ps -> s
    c = dff.tcq(t, q)
    # Store t_cq in ps, or NaN ("not a number") when missed, so the plot leaves a gap.
    tcqs.append(c * 1e12 if c is not None else np.nan)
    print(f"setup {s:4} ps   tcq {tcqs[-1]:7.2f} ps")     # tcqs[-1] = the value just added

nominal = tcqs[0]       # t_cq with data 300 ps early: the flip-flop's normal delay
# The smallest setup whose t_cq is within 10 % of nominal. zip pairs each setup with
# its t_cq; NaN compares as False, so missed runs drop out of the min().
setup_time = min(s for s, c in zip(setups, tcqs) if c <= 1.1 * nominal)
print(f"nominal tcq {nominal:.1f} ps; setup time (tcq within 10 %) {setup_time} ps")

# hold: data falls 1 -> 0 this many ps after the edge (negative = before); the old 1 must be kept
# q is 0 before the edge (dff.py). If the flip-flop catches D's old value 1, q rises
# after the edge and tcq() finds the crossing; if it catches the new 0, q stays at 0
# and tcq() returns None. So "if c" reads as "the old 1 was kept".
for h in [-60, -40, -35, -30, -20, 0, 20]:
    t, q, m1, m2 = dff.run(dff.T_EDGE + h * 1e-12, rising=False)
    c = dff.tcq(t, q)
    print(f"data changes {h:4} ps after the edge: {'old 1 kept' if c else 'new 0 caught'}")

# The plot: t_cq against arrival time, with the 10 % line.
plt.plot(setups, tcqs, "o-")
plt.axhline(1.1 * nominal, ls="--", c="grey")      # horizontal line at 1.1 x nominal
plt.xlabel("data arrives this long before the clock edge, ps")
plt.ylabel("clock-to-Q, ps")
plt.ylim(0, 600)
plt.grid(alpha=0.3)
plt.savefig("ff_sweep.png", dpi=120)    # saved in the folder you run from
plt.show()                              # opens a window (needs python3-tk, installed 16 Oct)
