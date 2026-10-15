"""Common-source amplifier three ways: hand (square law), rung 1 (BSIM4), rung 1/2 (hybrid-pi)."""
import os
import numpy as np
from tools import ac, ngspice
from models import NMOS

VDD, RD, W, L = 1.2, 2e3, 4e-6, 100e-9


def bsim_op(vgs):
    """Bias point of the real (BSIM4) transistor: Id, gm, gds, Vth."""
    d = ngspice(f"""* CS bias
{NMOS}
Vdd vdd 0 {VDD}
Vg g 0 {vgs}
RD vdd d {RD}
M1 d g 0 0 nch W={W} L={L}
.control
op
print -i(vdd) @m1[gm] @m1[gds] @m1[vth] v(d) > {{dir}}/op.txt
.endc
.end""")
    vals = [float(l.split("=")[1]) for l in open(os.path.join(d, "op.txt")) if "=" in l]
    return dict(zip(["id", "gm", "gds", "vth", "vd"], vals))


# 1. Find Vgs for Id = 200 uA by bisection: the simulator as a function
lo, hi = 0.3, 0.9
for _ in range(30):
    mid = (lo + hi) / 2
    if bsim_op(mid)["id"] < 200e-6:
        lo = mid
    else:
        hi = mid
vgs = (lo + hi) / 2
b = bsim_op(vgs)
print(f"Vgs = {vgs:.4f} V, Id = {b['id']*1e6:.1f} uA, Vd = {b['vd']:.3f} V, Vth = {b['vth']:.3f} V")

# 2. Hand, square law: gm = 2 Id / Vov
vov = vgs - b["vth"]
gm_hand = 2 * b["id"] / vov
ro = 1 / b["gds"]
print(f"gm: square law {gm_hand*1e3:.3f} mS, BSIM4 {b['gm']*1e3:.3f} mS; ro = {ro/1e3:.1f} kohm")
print(f"Av hand with BSIM4's gm and ro: {-b['gm'] * (RD * ro / (RD + ro)):.3f}")

# 3. Rung 1: the BSIM4 transistor, AC gain at 1 kHz
f, (vd,) = ac(f"""* CS rung 1
{NMOS}
Vdd vdd 0 {VDD}
Vg g 0 DC {vgs} AC 1
RD vdd d {RD}
M1 d g 0 0 nch W={W} L={L}""", 1e3, 1e3, 1, "d")
print(f"Av BSIM4 (rung 1):     {vd[0].real:.3f}")

# 4. Rung 1/2: the hybrid-pi model in its place, a VCCS and ro
f, (vd,) = ac(f"""* CS rung 1/2
Vg g 0 DC 0 AC 1
RD d 0 {RD}
G1 d 0 g 0 {b['gm']}
Ro d 0 {ro}""", 1e3, 1e3, 1, "d")
print(f"Av hybrid-pi (rung 1/2): {vd[0].real:.3f}")

# 5. Output resistance: input at AC ground, push 1 A into the drain, read the volts
f, (vd,) = ac(f"""* Rout
RD d 0 {RD}
G1 d 0 g 0 {b['gm']}
Ro d 0 {ro}
Rg g 0 1
I1 0 d DC 0 AC 1""", 1e3, 1e3, 1, "d")
print(f"Rout = {abs(vd[0]) / 1e3:.3f} kohm (hand: RD || ro = {RD * ro / (RD + ro) / 1e3:.3f} kohm)")