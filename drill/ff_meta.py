"""Close in on the setup that fails, then watch the flip-flop hesitate."""
# ---------------------------------------------------------------------------------
# Two steps, both calling dff.run() many times:
#   1. Find the critical arrival time, the boundary between "captured" and "missed",
#      by bisection (the same search as finding a root by halving an interval).
#   2. Arrive 1, 0.1, 0.01, 0.001 ps on the safe side of it and measure t_cq:
#      the closer, the longer the flip-flop hesitates (metastability, L6 6.7).
# ---------------------------------------------------------------------------------
import numpy as np
import dff

lo, hi = 40e-12, 60e-12          # lo fails, hi passes
for _ in range(14):              # bisection: halve the gap 14 times
    mid = (lo + hi) / 2          # try the middle
    t, q, m1, m2 = dff.run(dff.T_EDGE - mid)
    if dff.tcq(t, q) is None:
        lo = mid                 # missed: the boundary is above mid
    else:
        hi = mid                 # captured: the boundary is below mid
# After 14 halvings the 20 ps gap is 20 ps / 2^14 = about 0.001 ps wide.
print(f"critical setup between {lo*1e12:.4f} and {hi*1e12:.4f} ps")

# hi is the earliest-known passing arrival; arrive dt earlier than that.
for dt in [1e-12, 1e-13, 1e-14, 1e-15]:   # how far above the critical setup
    t, q, m1, m2 = dff.run(dff.T_EDGE - (hi + dt))
    c = dff.tcq(t, q)
    # Each step is 10 times closer to the boundary; t_cq should grow by the same
    # amount each time, tau * ln(10) (L6 6.7). The last step is limited by how
    # precisely the bisection found the boundary (about 0.001 ps).
    print(f"{dt*1e12:7.3f} ps above critical: tcq = {c*1e12:6.1f} ps" if c else f"{dt*1e12:7.3f} ps: not resolved by 1.6 ns")
