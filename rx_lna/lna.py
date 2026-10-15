"""RX front end: a 1 GHz inductively degenerated cascode LNA in CMOS, designed
from ngspice's operating point and checked with ngspice AC and noise analyses.

Why this topology. A source inductor Ls makes the input look resistive without
a resistor: the gate current through Cgs and the drain current gm*vgs both
flow through Ls, which turns into Re{Zin} = gm*Ls/Cgs = omega_T*Ls. A noiseless
inductor sets the 50 ohm, so the match costs almost no noise. A gate inductor
Lg tunes out Cgs at f0, so the match holds at one frequency (a band of about
f0/Q_in). The cascode device M2 holds M1's drain still, so M1's gate-drain
overlap capacitance is not multiplied by the stage gain (the Miller effect):
the input match stops depending on the load. CASCODE = False shows the
difference. The drain tank Ld || Cd resonates at f0 and its loss resistance
Rp (set by Ld's Q) sits in parallel with the 50 ohm load.

Lg is given a finite Q because the inductor's series resistance sits right at
the input and adds its noise before any gain.

Run:  python rx_lna/lna.py   (writes results/lna.csv and lna.png)
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.models import LMIN, NMOS, VDD  # noqa: E402
from common.spice import run  # noqa: E402

F0 = 1e9             # carrier, Hz
RS = 50.0            # source and load, ohm
ID_TARGET = 5e-3     # drain current, A
W1 = 300e-6          # input device width, m (30 fingers of 10 um)
LG_Q = 30            # quality factor of the gate inductor
LD = 8e-9            # drain tank inductor, H
LD_Q = 10            # its quality factor
CASCODE = True
K, T = 1.380649e-23, 300.15
OUT = os.path.join(os.path.dirname(__file__), "..", "results")
W0 = 2 * np.pi * F0


def mos(name, d, g, s, w):
    return f"{name} {d} {g} {s} 0 nch W={w} L={LMIN} nf={max(1, round(w / 10e-6))}"


def bias_point():
    """Gate voltage for ID_TARGET with the drain near its cascode value, then gm
    from the operating point and the input capacitance from a one-point AC run.

    Why not read Cgg from the operating point? ngspice's @m1[cgg] is the
    intrinsic (channel) capacitance only. The gate-source and gate-drain
    overlap and fringe capacitances come on top, and here they add about 80 %.
    Asking the simulator for the current into the gate at F0 counts all of it."""
    vg = 0.55
    workdir = os.path.join(OUT, "lna_op")
    for _ in range(8):
        net = "\n".join(["* LNA bias", NMOS, "Vd d 0 0.6", f"Vg g 0 {vg} AC 1",
                         mos("M1", "d", "g", "0", W1), ".control", "op",
                         "let id = -i(vd)", "let gm = @m1[gm]", "let cgg = @m1[cgg]",
                         "let cgd = @m1[cgd]", "print id gm cgg cgd > {dir}/op.txt",
                         f"ac lin 1 {F0} {F0}", "let cin = real(imag(-i(vg)) / (2 * pi * frequency))",
                         "print cin > {dir}/ac1.txt",
                         ".endc", ".end"])
        run(net, [], workdir=workdir)
        vals = {}
        for line in open(os.path.join(workdir, "op.txt")).readlines() + \
                open(os.path.join(workdir, "ac1.txt")).readlines():
            if "=" in line:
                k, v = line.split("=")
                vals[k.strip()] = float(v)
        vg += (ID_TARGET - vals["id"]) / vals["gm"]      # Newton step on Id(Vg)
    return vg, vals


def design(vals):
    """Hand-calc start: Ls sets Re{Zin} = omega_T*Ls = 50 ohm; Lg + Ls resonate
    with Cgs at F0."""
    cgs = vals["cin"]          # everything the gate sees, drain held still
    wt = vals["gm"] / cgs
    ls = RS / wt
    lg = 1 / (W0**2 * cgs) - ls
    cd = 1 / (W0**2 * LD)
    return ls, lg, cd, wt


def deck(vg, ls, lg, cd, lg_q, cascode=CASCODE):
    rlg = W0 * lg / lg_q if lg_q else 0.0
    rp = W0 * LD * LD_Q
    stack = ([mos("M1", "x", "g", "s", W1), f"Vcas cg 0 {VDD}", mos("M2", "d", "cg", "x", W1)]
             if cascode else [mos("M1", "d", "g", "s", W1)])
    return "\n".join([
        "* 1 GHz inductively degenerated cascode LNA", NMOS,
        f"Vdd vdd 0 {VDD}",
        "Vs src 0 DC 0 AC 1", f"Rs src rfin {RS}",
        "Cin rfin g1 100p",                              # DC block
        f"Lg g1 g2 {lg}", f"Rlg g2 g {rlg + 1e-3}",      # inductor and its loss
        f"Vb bias 0 {vg}", "Lbias bias g 10u",           # bias tee: DC only
        f"Ls s 0 {ls}",
        *stack,
        f"Ld vdd d {LD}", f"Rp vdd d {rp}", f"Cd d 0 {cd}",   # drain tank
        "Cout d out 100p", f"RL out 0 {RS}",
        ".control",
        "ac dec 200 100meg 10g",
        "let zin = v(rfin) / (-i(vs))",
        "wrdata {dir}/ac.txt real(zin) imag(zin) real(v(out)) imag(v(out))",
        "noise v(out) vs dec 200 100meg 10g",
        "setplot noise1",
        "wrdata {dir}/noise.txt inoise_spectrum",
        ".endc", ".end"])


def analyse(vg, ls, lg, cd, lg_q, cascode=CASCODE, keep=None):
    d = run(deck(vg, ls, lg, cd, lg_q, cascode), ["ac.txt", "noise.txt"], keep=keep)
    ac, nz = d["ac.txt"], d["noise.txt"]
    f = ac[:, 0]
    zin = ac[:, 1] + 1j * ac[:, 3]
    vout = ac[:, 5] + 1j * ac[:, 7]
    s11 = 20 * np.log10(np.abs((zin - RS) / (zin + RS)))
    s21 = 20 * np.log10(np.abs(2 * vout))         # 1 V source behind 50 ohm, 50 ohm load
    nf = 10 * np.log10(nz[:, 1]**2 / (4 * K * T * RS))
    nf = np.interp(f, nz[:, 0], nf)
    return pd.DataFrame(dict(f=f, zin=zin, s11=s11, s21=s21, nf=nf))


def tune(vg, ls, lg, cd, wt, steps=6):
    """Let the simulator finish what the hand calculation started: Lg nulls
    Im{Zin} at F0, Ls brings Re{Zin} to 50 ohm, Cd moves the gain peak to F0."""
    for _ in range(steps):
        r = analyse(vg, ls, lg, cd, LG_Q)
        k = (r.f - F0).abs().idxmin()
        z = r.zin[k]
        lg -= z.imag / W0
        ls = max(ls + (RS - z.real) / wt, 1e-12)
        fpk = r.f[r.s21.idxmax()]
        cd *= (fpk / F0)**2
    return ls, lg, cd


def main():
    os.makedirs(OUT, exist_ok=True)
    vg, vals = bias_point()
    ls0, lg0, cd0, wt = design(vals)
    ls, lg, cd = tune(vg, ls0, lg0, cd0, wt)
    res = {q: analyse(vg, ls, lg, cd, q, keep=f"lna_q{q}") for q in (0, LG_Q)}
    r = res[LG_Q]
    k = (r.f - F0).abs().idxmin()
    # Same Lg, Ls and Cd, cascode removed: how far does Miller move the match?
    nc = analyse(vg, ls, lg, cd, LG_Q, cascode=False, keep="lna_no_cascode")
    band = r.f[r.s11 < -10]
    table = r[["f", "s11", "s21", "nf"]].assign(nf_ideal_lg=res[0].nf)
    table.to_csv(os.path.join(OUT, "lna.csv"), index=False, float_format="%.6g")
    plot(res, r.f.values)
    return dict(vg_V=vg, id_mA=1e3 * vals["id"], gm_mS=1e3 * vals["gm"],
                cgg_op_fF=1e15 * vals["cgg"], cin_fF=1e15 * vals["cin"],
                fT_GHz=wt / 2 / np.pi / 1e9, Ls_nH_hand=ls0 * 1e9, Ls_nH=ls * 1e9,
                Lg_nH_hand=lg0 * 1e9, Lg_nH=lg * 1e9, S11=r.s11[k], S21=r.s21[k],
                NF=r.nf[k], NF_ideal=res[0].nf[k], S11_no_cascode=nc.s11[k],
                S21_no_cascode=nc.s21[k],
                band_lo_GHz=band.min() / 1e9 if len(band) else np.nan,
                band_hi_GHz=band.max() / 1e9 if len(band) else np.nan)


def plot(res, f):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].semilogx(f / 1e9, res[LG_Q].s11, label="S11")
    ax[0].semilogx(f / 1e9, res[LG_Q].s21, label="S21")
    ax[0].axvline(1, color="0.6", lw=0.8)
    ax[0].set(xlabel="frequency, GHz", ylabel="dB", title="Match and gain", ylim=(-35, 25))
    ax[0].legend()
    ax[1].semilogx(f / 1e9, res[0].nf, label="ideal Lg")
    ax[1].semilogx(f / 1e9, res[LG_Q].nf, label=f"Lg with Q = {LG_Q}")
    ax[1].axvline(1, color="0.6", lw=0.8)
    ax[1].set(xlabel="frequency, GHz", ylabel="noise figure, dB", title="Noise figure",
              ylim=(0, 8))
    ax[1].legend()
    for a in ax:
        a.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "lna.png"), dpi=130)


if __name__ == "__main__":
    for key, val in main().items():
        print(f"{key:12s} {val:8.3f}")
