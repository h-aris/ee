"""TX amplitude path: a switched-capacitor PA (SCPA) at 1 GHz, simulated in ngspice.

Architecture: N unit capacitors share a top plate that drives a series L into
a 50 ohm load. For amplitude code n, n units are switched by a 1 GHz square
wave (0 to VDD) and N - n units are held at ground. The output amplitude is
then proportional to n / N, so the capacitor array is an RF DAC. L resonates
with the total array capacitance, which stays the same for every code, so the
tuning does not move with amplitude.

Switch level on purpose: each unit's inverter is two ideal switches (ngspice
`sw` elements, on-resistance Ron_unit) tying the bottom plate to a DC VDD rail
or to ground. Driving from a rail through a switch, not from a ramped source,
is what makes the charge-sharing (CV^2 f) loss show up, as it does on silicon.
Identical units in parallel are lumped into two branches (switching and
grounded), which is electrically exact and keeps the deck small.

Run:  python tx_am_scpa/scpa.py      (writes results/scpa_*.csv and .png)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.spice import fourier, run  # noqa: E402

F0 = 1e9          # carrier, Hz
VDD = 1.1         # switch supply, V
N = 32            # unit capacitors (5-bit amplitude)
RL = 50.0         # load, ohm
Q = 4.0           # loaded Q of the series output network
RON_UNIT = 16.0   # on-resistance of one unit switch, ohm (0.5 ohm for all 32)
TR = 20e-12       # drive rise and fall time, s

W0 = 2 * np.pi * F0
CTOT = 1 / (W0 * RL * Q)        # total array capacitance, F (0.80 pF): Q = 1/(w0 R C)
LSER = 1 / (W0**2 * CTOT)       # series inductor, H (31.8 nH), resonates with CTOT
OUT = os.path.join(os.path.dirname(__file__), "..", "results")


def deck(n, duty=0.5):
    """Netlist for amplitude code n (0..N) and drive duty cycle."""
    per = 1 / F0
    pw = duty * per - TR
    lines = [f"* SCPA code {n}/{N}", f"Vdd vdd 0 DC {VDD}"]
    if n > 0:
        r = RON_UNIT / n
        lines += [f"Vc ctl 0 PULSE(0 1 0 {TR} {TR} {pw} {per})",
                  f"Vcb ctlb 0 PULSE(1 0 0 {TR} {TR} {pw} {per})",
                  f".model swn sw(vt=0.5 vh=0 ron={r} roff=1e9)",
                  "Sup asw vdd ctl 0 swn",       # pull-up, on while ctl is high
                  "Sdn asw 0 ctlb 0 swn",        # pull-down, on while ctl is low
                  f"Csw asw top {CTOT * n / N}"]
    if n < N:
        lines += [f"Rgnd 0 agnd {RON_UNIT / (N - n)}",   # held low: pull-down always on
                  f"Cgnd agnd top {CTOT * (N - n) / N}"]
    lines += [f"L1 top out {LSER}",
              f"RL out 0 {RL}",
              ".tran 1p 40n 0 1p",
              ".control", "run",
              "wrdata {dir}/w.txt v(out) i(vdd)",
              ".endc", ".end"]
    return "\n".join(lines)


def simulate(n, duty=0.5):
    """Return harmonic phasors at the load, fundamental Pout and supply power (W)."""
    d = run(deck(n, duty), ["w.txt"])["w.txt"]
    t, vout, idd = d[:, 0], d[:, 1], d[:, 3]   # wrdata writes (time, value) pairs
    h = fourier(t, vout, F0, n_harm=5)
    pout = abs(h[0])**2 / (2 * RL)            # fundamental power into the load
    last = t >= t[-1] - 10 / F0
    tl = t[last]
    # i(vdd) is the current into the rail's + terminal, so the rail delivers -VDD*i
    psup = -VDD * np.trapezoid(idd[last], tl) / (tl[-1] - tl[0])
    return h, pout, psup


def theory_eff(n):
    """Ideal SCPA drain efficiency (Yoo et al., JSSC 2011), switch loss excluded."""
    return 4 * n * Q / (4 * n * Q + np.pi * (N - n)) if n > 0 else 0.0


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for n in range(0, N + 1, 2):
        h, pout, psup = simulate(n)
        eff = pout / psup if psup > 0 else 0.0
        rows.append((n, abs(h[0]), np.degrees(np.angle(h[0])), pout, psup, eff, theory_eff(n)))
    rows = np.array(rows)
    np.savetxt(os.path.join(OUT, "scpa_codes.csv"), rows, delimiter=",",
               header="code,vout_peak_V,vout_phase_deg,pout_W,psupply_W,eff_sim,eff_theory",
               comments="")

    duties = np.unique(np.concatenate([np.linspace(0.2, 0.8, 25), [1 / 3, 2 / 3]]))
    hd = []
    for dty in duties:
        h, _, _ = simulate(N, dty)
        hd.append((dty, 20 * np.log10(abs(h[1]) / abs(h[0]) + 1e-12),
                   20 * np.log10(abs(h[2]) / abs(h[0]) + 1e-12)))
    hd = np.array(hd)
    np.savetxt(os.path.join(OUT, "scpa_duty.csv"), hd, delimiter=",",
               header="duty,HD2_dBc,HD3_dBc", comments="")
    plot(rows, hd)
    return rows, hd


def plot(rows, hd):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    pmax = rows[-1, 3]
    backoff = 10 * np.log10(np.maximum(rows[1:, 3], 1e-15) / pmax)
    ax[0].plot(rows[:, 0], rows[:, 1], "o-")
    ax[0].plot(rows[:, 0], rows[-1, 1] * rows[:, 0] / N, "--", label="ideal n/N")
    ax[0].set(xlabel="amplitude code n", ylabel="output fundamental, V peak",
              title="AM-AM: the array is an RF DAC")
    ax[0].legend()
    ax[1].plot(backoff, 100 * rows[1:, 5], "o-", label="ngspice")
    ax[1].plot(backoff, 100 * rows[1:, 6], "--", label="theory, ideal switches")
    ax[1].set(xlabel="output power back-off, dB", ylabel="efficiency, %",
              title="Efficiency vs back-off", xlim=(-15, 0.5))
    ax[1].legend()
    ax[2].plot(hd[:, 0], hd[:, 1], "o-", label="HD2")
    ax[2].plot(hd[:, 0], hd[:, 2], "s-", label="HD3")
    for d in (1 / 3, 1 / 2, 2 / 3):
        ax[2].axvline(d, color="0.6", lw=0.8)
    ax[2].set(xlabel="drive duty cycle", ylabel="harmonic at the load, dBc",
              title="Harmonics vs duty (HD3 nulls at 1/3, 2/3)")
    ax[2].legend()
    for a in ax:
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "scpa.png"), dpi=130)


if __name__ == "__main__":
    rows, hd = main()
    print("code  Vpk[V]  Pout[mW]  eff_sim  eff_theory")
    for r in rows:
        print(f"{int(r[0]):4d}  {r[1]:.3f}  {1e3 * r[3]:7.3f}  {r[5]:.3f}  {r[6]:.3f}")
    i3 = np.argmin(np.abs(hd[:, 0] - 1 / 3))
    print(f"HD3 at duty {hd[i3, 0]:.3f}: {hd[i3, 2]:.1f} dBc")
