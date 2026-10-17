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

Run:  python rx_lna/lna.py   (writes results/lna.csv and lna.png,
      shows the summary figure, then prints the design numbers)
"""
# ---------------------------------------------------------------------------------
# The design flow in this file, the way an RF designer works:
#   1. bias_point(): find the gate voltage that gives 5 mA, read gm and the input
#      capacitance from the simulator (the operating point).
#   2. hand_design(): hand formulas for Ls, Lg and the drain tank (L7 7.7).
#   3. tune(): let the simulator correct what the hand formulas missed.
#   4. analyse(): AC and noise runs give S11, S21 and the noise figure.
#   5. main(): the final numbers, plus the same design without the cascode,
#      which must lose its match (the mutation check in run_all.py). It ends with
#      a commented plot template, where every variable of main() is still
#      alive, then shows the summary figure.
# ---------------------------------------------------------------------------------
import os
import sys

import matplotlib.pyplot as plt   # plotting, MATLAB style
import numpy as np                # arrays and maths
import pandas as pd               # tables with named columns, like a MATLAB table

# Make the repo folder findable, so `common` can be imported (MATLAB: addpath).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.models import LMIN, NMOS, VDD  # noqa: E402  (the model line, channel length, 1.2 V supply)
from common.spice import run  # noqa: E402

F0 = 1e9             # carrier, Hz
RS = 50.0            # source and load, ohm
ID_TARGET = 5e-3     # drain current, A
W1 = 300e-6          # input device width, m (30 fingers of 10 um)
LG_Q = 30            # quality factor of the gate inductor
LD = 8e-9            # drain tank inductor, H
LD_Q = 10            # its quality factor
CASCODE = True       # set False to see the Miller effect break the match (L7 exercise)
BOLTZMANN = 1.380649e-23   # J/K
TEMPERATURE_K = 300.15
RESULTS_FOLDER = os.path.join(os.path.dirname(__file__), "..", "results")
W0 = 2 * np.pi * F0


def mos(name, drain, gate, source, width):
    # One SPICE transistor line: name drain gate source bulk model W L nf.
    # nf = number of fingers, one per 10 um of width (at least 1).
    fingers = max(1, round(width / 10e-6))
    return f"{name} {drain} {gate} {source} 0 nch W={width} L={LMIN} nf={fingers}"


def bias_point():
    """Gate voltage for ID_TARGET with the drain near its cascode value, then gm
    from the operating point and the input capacitance from a one-point AC run.

    Why not read Cgg from the operating point? ngspice's @m1[cgg] is the
    intrinsic (channel) capacitance only. The gate-source and gate-drain
    overlap and fringe capacitances come on top, and here they add about 80 %.
    Asking the simulator for the current into the gate at F0 counts all of it."""
    gate_voltage = 0.55        # first guess, V
    workdir = os.path.join(RESULTS_FOLDER, "lna_op")
    for step in range(8):      # 8 Newton steps, each one corrects the gate voltage
        # A small deck: one transistor, drain held at 0.6 V, gate at gate_voltage.
        # The .control lines run an operating point (op), then ask the transistor for
        # its current, gm, cgg, cgd (@m1[gm] reads an internal device value), and
        # print them to op.txt; then a one-frequency AC run measures the real input
        # capacitance from the gate current: C = Im{I}/(2 pi f V) with V = 1.
        bias_netlist = "\n".join([
            "* LNA bias", NMOS, "Vd d 0 0.6", f"Vg g 0 {gate_voltage} AC 1",
            mos("M1", "d", "g", "0", W1), ".control", "op",
            "let id = -i(vd)", "let gm = @m1[gm]", "let cgg = @m1[cgg]",
            "let cgd = @m1[cgd]", "print id gm cgg cgd > {dir}/op.txt",
            f"ac lin 1 {F0} {F0}", "let cin = real(imag(-i(vg)) / (2 * pi * frequency))",
            "print cin > {dir}/ac1.txt",
            ".endc", ".end"])
        run(bias_netlist, [], workdir=workdir)     # [] = no wrdata files; we read op.txt ourselves
        # Read lines like "gm = 2.48e-02" from both files into a dictionary,
        # name -> number: operating_point["gm"], operating_point["id"] ...
        operating_point = {}
        printed_lines = open(os.path.join(workdir, "op.txt")).readlines() + \
            open(os.path.join(workdir, "ac1.txt")).readlines()
        for line in printed_lines:
            if "=" in line:
                name, value = line.split("=")             # "gm = 2.48e-02" -> "gm ", " 2.48e-02"
                operating_point[name.strip()] = float(value)   # strip() removes the spaces
        # Newton's method: the current is off by (target - id); gm = dId/dVg says how
        # much the gate voltage moves Id, so this step lands close to the target.
        gate_voltage = gate_voltage + (ID_TARGET - operating_point["id"]) / operating_point["gm"]
    return gate_voltage, operating_point


def hand_design(operating_point):
    """Hand-calc start: Ls sets Re{Zin} = omega_T*Ls = 50 ohm; Lg + Ls resonate
    with Cgs at F0."""
    cgs = operating_point["cin"]          # everything the gate sees, drain held still
    omega_t = operating_point["gm"] / cgs   # omega_T = gm/Cgs, rad/s: the transistor's speed
    ls = RS / omega_t                     # Re{Zin} = omega_T * Ls = 50 ohm
    lg = 1 / (W0**2 * cgs) - ls           # Lg + Ls resonate with Cgs at f0: Im{Zin} = 0
    cd = 1 / (W0**2 * LD)                 # drain tank capacitor resonating with LD at f0
    return ls, lg, cd, omega_t


def netlist(gate_voltage, ls, lg, cd, lg_q, cascode=CASCODE):
    """The LNA as SPICE text, with AC and noise analyses in its .control block."""
    # The inductors' losses as series (Lg) and parallel (Ld) resistors from their Q.
    # lg_q = 0 means "ideal Lg" (Python treats 0 as false in an if).
    lg_series_resistance = W0 * lg / lg_q if lg_q else 0.0
    ld_parallel_resistance = W0 * LD * LD_Q
    # With the cascode: M1 (input) drives node x, M2 (gate at VDD) sits on top.
    # Without it: M1's drain goes straight to the output node d.
    if cascode:
        transistors = [mos("M1", "x", "g", "s", W1), f"Vcas cg 0 {VDD}", mos("M2", "d", "cg", "x", W1)]
    else:
        transistors = [mos("M1", "d", "g", "s", W1)]
    return "\n".join([
        "* 1 GHz inductively degenerated cascode LNA", NMOS,
        f"Vdd vdd 0 {VDD}",
        # The 50 ohm source: 1 V AC behind RS (the antenna).
        "Vs src 0 DC 0 AC 1", f"Rs src rfin {RS}",
        "Cin rfin g1 100p",                                          # DC block
        f"Lg g1 g2 {lg}", f"Rlg g2 g {lg_series_resistance + 1e-3}",   # inductor and its loss
        f"Vb bias 0 {gate_voltage}", "Lbias bias g 10u",             # bias tee: DC only
        f"Ls s 0 {ls}",
        *transistors,                 # the * unpacks the list: its lines go in here
        f"Ld vdd d {LD}", f"Rp vdd d {ld_parallel_resistance}", f"Cd d 0 {cd}",   # drain tank
        "Cout d out 100p", f"RL out 0 {RS}",
        ".control",
        # AC sweep: 200 points per decade from 100 MHz to 10 GHz.
        "ac dec 200 100meg 10g",
        # Input impedance = voltage at the input / current from the source.
        "let zin = v(rfin) / (-i(vs))",
        "wrdata {dir}/ac.txt real(zin) imag(zin) real(v(out)) imag(v(out))",
        # Noise analysis: noise at the output, referred back to the source Vs.
        "noise v(out) vs dec 200 100meg 10g",
        "setplot noise1",            # switch to the noise results (spectra, not totals)
        "wrdata {dir}/noise.txt inoise_spectrum",
        ".endc", ".end"])


def analyse(gate_voltage, ls, lg, cd, lg_q, cascode=CASCODE, keep=None):
    """Simulate once. Returns a table, one row per frequency: f, zin, s11, s21, nf."""
    outputs = run(netlist(gate_voltage, ls, lg, cd, lg_q, cascode), ["ac.txt", "noise.txt"], keep=keep)
    ac_data = outputs["ac.txt"]
    noise_data = outputs["noise.txt"]
    freqs_Hz = ac_data[:, 0]
    # wrdata writes (f, value) pairs: columns 1, 3, 5, 7 are the four values.
    zin = ac_data[:, 1] + 1j * ac_data[:, 3]          # 1j is Python's imaginary unit (MATLAB's 1i)
    vout = ac_data[:, 5] + 1j * ac_data[:, 7]
    # S11 in dB: how much of the incoming wave bounces back from Zin.
    s11_dB = 20 * np.log10(np.abs((zin - RS) / (zin + RS)))
    s21_dB = 20 * np.log10(np.abs(2 * vout))         # 1 V source behind 50 ohm, 50 ohm load
    # Noise figure: input-referred noise power over the source resistor's own 4kTR.
    nf_dB_on_noise_grid = 10 * np.log10(noise_data[:, 1]**2 / (4 * BOLTZMANN * TEMPERATURE_K * RS))
    nf_dB = np.interp(freqs_Hz, noise_data[:, 0], nf_dB_on_noise_grid)   # onto the AC run's frequencies
    # A table with named columns: result.f, result.s11, result.s21, result.nf ...
    return pd.DataFrame(dict(f=freqs_Hz, zin=zin, s11=s11_dB, s21=s21_dB, nf=nf_dB))


def tune(gate_voltage, ls, lg, cd, omega_t, steps=6):
    """Let the simulator finish what the hand calculation started: Lg nulls
    Im{Zin} at F0, Ls brings Re{Zin} to 50 ohm, Cd moves the gain peak to F0."""
    for step in range(steps):
        result = analyse(gate_voltage, ls, lg, cd, LG_Q)
        # The row whose frequency is closest to F0: idxmin() = the row label of the smallest value.
        row_at_f0 = (result.f - F0).abs().idxmin()
        zin_at_f0 = result.zin[row_at_f0]
        lg = lg - zin_at_f0.imag / W0                        # remove the leftover reactance: X = w L
        ls = max(ls + (RS - zin_at_f0.real) / omega_t, 1e-12)   # Re{Zin} = wT Ls: correct Ls
        gain_peak_freq_Hz = result.f[result.s21.idxmax()]    # where the gain peaks now
        cd = cd * (gain_peak_freq_Hz / F0)**2                # f ~ 1/sqrt(C): move the peak to F0
    return ls, lg, cd


def main(show_plots=False):
    # show_plots: False when run_all.py calls main(); True when you run this file.
    os.makedirs(RESULTS_FOLDER, exist_ok=True)

    # --- 1. Bias, hand design, tuning ------------------------------------------------
    gate_voltage, operating_point = bias_point()
    ls_hand, lg_hand, cd_hand, omega_t = hand_design(operating_point)
    ls, lg, cd = tune(gate_voltage, ls_hand, lg_hand, cd_hand, omega_t)

    # --- 2. The final design, three ways -----------------------------------------------
    with_ideal_lg = analyse(gate_voltage, ls, lg, cd, 0, keep="lna_q0")            # Lg without loss
    final = analyse(gate_voltage, ls, lg, cd, LG_Q, keep=f"lna_q{LG_Q}")            # Lg with Q = 30
    # Same Lg, Ls and Cd, cascode removed: how far does Miller move the match?
    no_cascode = analyse(gate_voltage, ls, lg, cd, LG_Q, cascode=False, keep="lna_no_cascode")

    row_at_f0 = (final.f - F0).abs().idxmin()     # the row closest to 1 GHz
    band = final.f[final.s11 < -10]                # frequencies where the match is better than -10 dB

    # --- 3. Save ---------------------------------------------------------------------
    # Four columns of the final design, plus the ideal-Lg noise figure as a fifth.
    table = final[["f", "s11", "s21", "nf"]].copy()
    table["nf_ideal_lg"] = with_ideal_lg.nf
    table.to_csv(os.path.join(RESULTS_FOLDER, "lna.csv"), index=False, float_format="%.6g")
    save_summary_figure(final, with_ideal_lg)

    # Everything run_all.py and the printout need, by name, with units in the names.
    summary = dict(vg_V=gate_voltage, id_mA=1e3 * operating_point["id"], gm_mS=1e3 * operating_point["gm"],
                   cgg_op_fF=1e15 * operating_point["cgg"], cin_fF=1e15 * operating_point["cin"],
                   fT_GHz=omega_t / 2 / np.pi / 1e9, Ls_nH_hand=ls_hand * 1e9, Ls_nH=ls * 1e9,
                   Lg_nH_hand=lg_hand * 1e9, Lg_nH=lg * 1e9,
                   S11=final.s11[row_at_f0], S21=final.s21[row_at_f0],
                   NF=final.nf[row_at_f0], NF_ideal=with_ideal_lg.nf[row_at_f0],
                   S11_no_cascode=no_cascode.s11[row_at_f0], S21_no_cascode=no_cascode.s21[row_at_f0],
                   band_lo_GHz=band.min() / 1e9 if len(band) else np.nan,
                   band_hi_GHz=band.max() / 1e9 if len(band) else np.nan)

    # --- 4. Your own plots: every variable above is available here --------------------
    # To add a plot: select the five lines below, press Ctrl+/ in VS Code to remove
    # the "# ", and put in real names, for example var_x -> final.f / 1e9,
    # var_y -> final.s11
    # plt.figure()
    # plt.plot(var_x, var_y, "o-")
    # plt.xlabel("x axis label")
    # plt.ylabel("y axis label")
    # plt.title("title")

    # --- 5. Show the figures, or close them -------------------------------------
    if show_plots:
        plt.show()            # opens the summary figure and yours; the script continues when you close them
    else:
        plt.close("all")      # run_all.py and GitHub: nothing to show, so free the figures

    return summary


def save_summary_figure(final, with_ideal_lg):
    # The two-panel figure saved as results/lna.png (the README shows it).
    fig, panel = plt.subplots(1, 2, figsize=(11, 4.2))
    freqs_GHz = final.f / 1e9
    panel[0].semilogx(freqs_GHz, final.s11, label="S11")     # log frequency axis
    panel[0].semilogx(freqs_GHz, final.s21, label="S21")
    panel[0].axvline(1, color="0.6", lw=0.8)
    panel[0].set(xlabel="frequency, GHz", ylabel="dB", title="Match and gain", ylim=(-35, 25))
    panel[0].legend()
    panel[1].semilogx(freqs_GHz, with_ideal_lg.nf, label="ideal Lg")
    panel[1].semilogx(freqs_GHz, final.nf, label=f"Lg with Q = {LG_Q}")
    panel[1].axvline(1, color="0.6", lw=0.8)
    panel[1].set(xlabel="frequency, GHz", ylabel="noise figure, dB", title="Noise figure",
                 ylim=(0, 8))
    panel[1].legend()
    for one_panel in panel:
        one_panel.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_FOLDER, "lna.png"), dpi=130)
    # The figure stays open: main() shows it (show_plots=True) or closes it.


# These lines run only when you start this file yourself (python rx_lna/lna.py).
if __name__ == "__main__":
    summary = main(show_plots=True)
    # .items() gives (name, value) pairs; print each design number on its own line.
    for name, value in summary.items():
        print(f"{name:14s} {value:8.3f}")
