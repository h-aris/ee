"""Master-slave transmission-gate D flip-flop in ngspice: clock-to-Q against data arrival."""
# ---------------------------------------------------------------------------------
# What this file is: a MODULE, a toolbox the other two scripts load with
# `import dff`. It holds no flip-flop "object" that lives between runs. Every call
# to run() builds a fresh netlist of the same flip-flop with the data edge at a
# chosen time, simulates it from scratch in ngspice, and hands back the waveforms.
# ff_sweep.py and ff_meta.py just call dff.run() many times with different data times.
#
#   deck(t_data)   ->  the netlist as text (one transistor per line)
#   run(t_data)    ->  simulate it, return the waveforms t, q, m1, m2 (NumPy arrays)
#   tcq(t, q)      ->  read the clock-to-Q delay off the waveforms, or None if missed
#
# Node names (L6 6.5): d -> TG1 -> m1 -> inv1 -> m2 -> inv2 -> m3 -> TG2 -> back to m1
# (the master), m2 -> TG3 -> s1 -> inv3 -> q -> inv4 -> s3 -> TG4 -> back to s1 (the slave).
# ---------------------------------------------------------------------------------
import os
import numpy as np
from tools import ngspice      # drill/tools.py: writes deck.cir, runs "ngspice -b", returns the folder
from models import NMOS, PMOS  # the two .model lines shared with the testbench (common/models.py copy)

VDD = 1.2
WN, WP, L = 0.4e-6, 0.8e-6, 100e-9   # every NMOS 0.4 um wide, every PMOS 0.8 um, all 100 nm long
T_EDGE = 1.0e-9   # rising clock edge, s
TR = 20e-12       # clock and data rise/fall time, s


def inv(name, a, y):
    # An inverter as two netlist lines: a PMOS from vdd to the output y and an NMOS
    # from y to ground, gates both on the input a. Returns a list of two strings.
    # SPICE line: name drain gate source bulk model W L.
    return [f"MP{name} {y} {a} vdd vdd pch W={WP} L={L}", f"MN{name} {y} {a} 0 0 nch W={WN} L={L}"]


def tg(name, a, b, on_n, on_p):
    """Transmission gate between a and b: NMOS gate on_n, PMOS gate on_p."""
    # The switch of L6 6.4: an NMOS and a PMOS side by side between a and b. It
    # conducts when on_n is high and on_p is low, so its two gates get opposite clocks.
    return [f"MTN{name} {a} {on_n} {b} 0 nch W={WN} L={L}", f"MTP{name} {a} {on_p} {b} vdd pch W={WP} L={L}"]


def deck(t_data, rising=True, t_stop=1.6e-9, extra=""):
    # rising=True : D goes 0 -> 1 at t_data (the setup experiments).
    # rising=False: D goes 1 -> 0 at t_data (the hold experiments).
    # In both, q is 0 before the clock edge, so "q rises after the edge" always
    # means "the flip-flop caught a 1" (checked 16 Oct). See tcq() below.
    v0, v1 = (0, VDD) if rising else (VDD, 0)    # D's value before and after its edge
    # The netlist is built as a Python list of text lines ("lines"), joined at the end.
    lines = ["* TG master-slave DFF", NMOS, PMOS, f"Vdd vdd 0 {VDD}",
             # Clock: rises at T_EDGE (its 20 ps ramp centred on it), period 2 ns.
             # PULSE(low high delay rise fall width period)
             f"Vclk clk 0 PULSE(0 {VDD} {T_EDGE - TR/2} {TR} {TR} 1n 2n)",
             # The inverted clock, needed by every transmission gate's PMOS.
             f"Vclkb clkb 0 PULSE({VDD} 0 {T_EDGE - TR/2} {TR} {TR} 1n 2n)",
             # Data: a piecewise-linear source. Stays at v0, ramps to v1 over TR centred
             # on t_data, then stays at v1 to 10 ns. PWL(time value time value ...)
             f"Vd d 0 PWL(0 {v0} {t_data - TR/2} {v0} {t_data + TR/2} {v1} 10n {v1})"]
    # master: transparent while clk is low
    # tg(...) + inv(...) + ... : adding lists joins them into one longer list.
    lines += tg("1", "d", "m1", "clkb", "clk") + inv("1", "m1", "m2") + inv("2", "m2", "m3") + tg("2", "m3", "m1", "clk", "clkb")
    # slave: transparent while clk is high
    lines += tg("3", "m2", "s1", "clk", "clkb") + inv("3", "s1", "q") + inv("4", "q", "s3") + tg("4", "s3", "s1", "clkb", "clk")
    lines += ["Cq q 0 5f",      # 5 fF load on q: the next gates' input capacitance
              # .ic: starting voltages for m1 and s1 ("%g" is filled from the tuple after %).
              # Only a starting guess: within about 100 ps m1 follows D through the open
              # input switch and the slave settles holding q = 0.
              ".ic v(m1)=%g v(s1)=%g" % ((VDD, VDD) if rising else (0, 0)),
              # tran 0.5p t_stop uic: transient with 0.5 ps steps; uic = start from the
              # .ic values instead of solving for a DC operating point first.
              # wrdata: write (t, value) pairs for clk, q, m1, m2 into w.txt.
              # extra: room for more .control lines; ff_meta and 6.11 step 4 use the default "".
              ".control", f"tran 0.5p {t_stop} uic", "wrdata {dir}/w.txt v(clk) v(q) v(m1) v(m2)", extra, ".endc", ".end"]
    return "\n".join(lines)     # one text, lines separated by line breaks


def run(t_data, rising=True):
    # Simulate one flip-flop with D's edge at t_data. ngspice() returns the folder it
    # ran in; w.txt in it holds 8 columns: t, clk, t, q, t, m1, t, m2 (wrdata pairs).
    d = ngspice(deck(t_data, rising))
    a = np.loadtxt(os.path.join(d, "w.txt"))
    return a[:, 0], a[:, 3], a[:, 5], a[:, 7]   # t, q, m1, m2


def tcq(t, q, rising=True):
    """Time from the clock edge to q crossing VDD/2 in the captured direction; None if it never does."""
    after = t > T_EDGE              # True for every time sample after the clock edge
    if rising:
        # np.where(condition)[0] = the indices where the condition is True:
        # samples after the edge where q is above half the supply.
        idx = np.where(after & (q > VDD / 2))[0]
    else:
        idx = np.where(after & (q < VDD / 2))[0]
    # The first such sample is the crossing; no such sample means q never moved: missed.
    return (t[idx[0]] - T_EDGE) if len(idx) else None


# Run alone (python3 dff.py): seven data times, from early to too late.
if __name__ == "__main__":
    for ts in (300e-12, 100e-12, 50e-12, 30e-12, 20e-12, 10e-12, 0.0):
        t, q, m1, m2 = run(T_EDGE - ts)         # data ts before the edge
        c = tcq(t, q)
        print(f"data {ts*1e12:3.0f} ps before the edge: " + (f"tcq = {c*1e12:.1f} ps" if c else "not captured"))
