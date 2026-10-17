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

Run:  python tx_am_scpa/scpa.py      (writes results/scpa_*.csv and .png,
      shows the summary figure, then prints the table)
"""
# ---------------------------------------------------------------------------------
# The shape of this file, which every block script in the repo shares:
#   imports and design values (SI units)
#   netlist(): builds the circuit as text
#   simulate(): runs it through common/spice.run() and turns waveforms into numbers
#   main(): the sweeps, saved as tables (CSV files); ends with a commented plot
#       template, where every variable of main() is still alive, then shows the
#       summary figure.
#   the last lines: run only when you start this file yourself, and print a table.
# run_all.py imports this file and calls main(); you can also run it alone.
# Physics: L7 7.4. The layout of one unit cell: L7 7.15 (ee/layout/).
# ---------------------------------------------------------------------------------
import os
import sys

import matplotlib.pyplot as plt   # plotting, MATLAB style
import numpy as np                # arrays and maths
import pandas as pd               # tables with named columns, like a MATLAB table

# Make the repo folder (one level up, "..") findable, so `common` can be imported
# whether this file is run alone or through run_all.py (MATLAB: addpath).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# Two functions from common/spice.py, then called as run(...) and fourier(...).
from common.spice import fourier, run  # noqa: E402  (tells the style checker this late import is on purpose)

# --- Design values. Change one, rerun, and watch the numbers move (L7 exercises). ---
F0 = 1e9          # carrier, Hz
VDD = 1.1         # switch supply, V
N = 32            # number of unit capacitors (5-bit amplitude: codes 0 to 32)
RL = 50.0         # load, ohm
Q = 4.0           # loaded Q of the series output network
RON_UNIT = 16.0   # on-resistance of one unit switch, ohm (0.5 ohm for all 32)
TR = 20e-12       # drive rise and fall time, s

# Derived values. ** is "to the power of" (MATLAB's ^).
W0 = 2 * np.pi * F0
CTOT = 1 / (W0 * RL * Q)        # total array capacitance, F (0.80 pF): Q = 1/(w0 R C)
LSER = 1 / (W0**2 * CTOT)       # series inductor, H (31.8 nH), resonates with CTOT
RESULTS_FOLDER = os.path.join(os.path.dirname(__file__), "..", "results")


def netlist(code, duty=0.5):
    """The circuit as SPICE text, for amplitude code 0..N and a drive duty cycle."""
    period_s = 1 / F0
    pulse_width_s = duty * period_s - TR       # the edges take TR each
    # The netlist is built as a Python list of text lines, joined at the end.
    lines = [f"* SCPA code {code}/{N}", f"Vdd vdd 0 DC {VDD}"]
    if code > 0:
        # The switching units in parallel = one branch with `code` times the
        # capacitance and 1/code the switch resistance (equal resistors in parallel).
        switch_resistance = RON_UNIT / code
        # Two drive signals, ctl and its opposite ctlb: PULSE(low high delay rise fall width period).
        lines += [f"Vc ctl 0 PULSE(0 1 0 {TR} {TR} {pulse_width_s} {period_s})",
                  f"Vcb ctlb 0 PULSE(1 0 0 {TR} {TR} {pulse_width_s} {period_s})",
                  # An ideal voltage-controlled switch: on (that resistance) when its
                  # control is above 0.5 V, off (1 Gohm) below.
                  f".model swn sw(vt=0.5 vh=0 ron={switch_resistance} roff=1e9)",
                  # The inverter as two switches: node asw is the bottom plate.
                  "Sup asw vdd ctl 0 swn",       # pull-up, on while ctl is high
                  "Sdn asw 0 ctlb 0 swn",        # pull-down, on while ctl is low
                  # The switching part of the array, bottom plate asw, top plate "top".
                  f"Csw asw top {CTOT * code / N}"]
    if code < N:
        # The N - code idle units: bottom plates held at ground through their pull-downs.
        lines += [f"Rgnd 0 agnd {RON_UNIT / (N - code)}",   # held low: pull-down always on
                  f"Cgnd agnd top {CTOT * (N - code) / N}"]
    # Series L to the load. Total array C is the same for every code, so the
    # resonance (and the tuning) never moves with amplitude.
    lines += [f"L1 top out {LSER}",
              f"RL out 0 {RL}",
              # Transient: 1 ps print step, 40 ns long (40 periods), max step 1 ps.
              ".tran 1p 40n 0 1p",
              ".control", "run",
              # Write time and v(out), then time and the supply current, to w.txt.
              "wrdata {dir}/w.txt v(out) i(vdd)",
              ".endc", ".end"]
    return "\n".join(lines)


def simulate(code, duty=0.5):
    """Simulate one code. Returns the output's harmonics (complex amplitudes,
    [0] = fundamental, [1] = 2nd, [2] = 3rd ...), the output power and the supply power, W."""
    # run() returns a dictionary of tables; ["w.txt"] takes the one we asked for.
    waveforms = run(netlist(code, duty), ["w.txt"])["w.txt"]
    # waveforms[:, k] is column k (":" = all rows), MATLAB's waveforms(:, k+1).
    # wrdata writes (time, value) pairs: columns 0, 1 = time, v(out); 2, 3 = time, i(vdd).
    time_s = waveforms[:, 0]
    vout = waveforms[:, 1]
    supply_current = waveforms[:, 3]
    harmonics = fourier(time_s, vout, F0, n_harm=5)
    # Power of a sine of peak amplitude A into R: A^2 / (2R). abs() of a complex number = its magnitude.
    pout_W = abs(harmonics[0])**2 / (2 * RL)
    # Average the supply power over the last 10 periods (start-up has settled).
    settled = time_s >= time_s[-1] - 10 / F0     # True/False for each sample: is it in the last 10 periods?
    # i(vdd) is the current into the rail's + terminal, so the rail delivers -VDD * i.
    # np.trapezoid integrates over time (MATLAB: trapz); dividing by the span gives the average.
    settled_time = time_s[settled]
    psupply_W = -VDD * np.trapezoid(supply_current[settled], settled_time) / (settled_time[-1] - settled_time[0])
    return harmonics, pout_W, psupply_W     # a function can return several values at once


def theory_efficiency(code):
    """Ideal SCPA drain efficiency (Yoo et al., JSSC 2011), switch loss excluded."""
    # The charge-sharing loss between switching and idle capacitors, against Q:
    # 100 % at full code (code = N), falling as more units sit idle.
    if code == 0:
        return 0.0
    return 4 * code * Q / (4 * code * Q + np.pi * (N - code))


def main(show_plots=False):
    # show_plots: False when run_all.py calls main(); True when you run this file.
    os.makedirs(RESULTS_FOLDER, exist_ok=True)

    # --- 1. Sweep the amplitude code: 0, 2, 4, ..., 32 -----------------------------
    # range(start, stop, step) stops before stop, so N + 1 includes 32.
    rows_of_code_sweep = []
    for code in range(0, N + 1, 2):
        harmonics, pout_W, psupply_W = simulate(code)
        efficiency = pout_W / psupply_W if psupply_W > 0 else 0.0
        fundamental = harmonics[0]
        # One row: a dictionary, column name -> value.
        rows_of_code_sweep.append(dict(code=code,
                                       vout_peak_V=abs(fundamental),
                                       vout_phase_deg=np.degrees(np.angle(fundamental)),
                                       pout_W=pout_W, psupply_W=psupply_W,
                                       eff_sim=efficiency, eff_theory=theory_efficiency(code)))
    # The list of rows becomes a table with named columns: code_sweep.pout_W, ...
    code_sweep = pd.DataFrame(rows_of_code_sweep)
    # float_format "%.18e": every digit kept; polar_tx.py reads this file.
    code_sweep.to_csv(os.path.join(RESULTS_FOLDER, "scpa_codes.csv"), index=False, float_format="%.18e")

    # --- 2. Sweep the drive duty cycle at full code -----------------------------------
    # 25 points from 0.2 to 0.8 (MATLAB: linspace), plus exactly 1/3 and 2/3;
    # np.unique sorts them and drops duplicates.
    duty_cycles = np.unique(np.concatenate([np.linspace(0.2, 0.8, 25), [1 / 3, 2 / 3]]))
    rows_of_duty_sweep = []
    for duty in duty_cycles:
        harmonics, pout_W, psupply_W = simulate(N, duty)
        # HD2 and HD3 in dBc: 20 log10 of harmonic over fundamental. The tiny 1e-12
        # keeps log10 away from zero when a harmonic vanishes.
        hd2_dBc = 20 * np.log10(abs(harmonics[1]) / abs(harmonics[0]) + 1e-12)
        hd3_dBc = 20 * np.log10(abs(harmonics[2]) / abs(harmonics[0]) + 1e-12)
        rows_of_duty_sweep.append(dict(duty=duty, HD2_dBc=hd2_dBc, HD3_dBc=hd3_dBc))
    duty_sweep = pd.DataFrame(rows_of_duty_sweep)
    duty_sweep.to_csv(os.path.join(RESULTS_FOLDER, "scpa_duty.csv"), index=False, float_format="%.18e")

    save_summary_figure(code_sweep, duty_sweep)

    # --- 3. Your own plots: every variable above is available here --------------------
    # To add a plot: select the five lines below, press Ctrl+/ in VS Code to remove
    # the "# ", and put in real names, for example var_x -> duty_sweep.duty,
    # var_y -> duty_sweep.HD3_dBc
    # plt.figure()
    # plt.plot(var_x, var_y, "o-")
    # plt.xlabel("x axis label")
    # plt.ylabel("y axis label")
    # plt.title("title")

    # --- 4. Show the figures, or close them -------------------------------------
    if show_plots:
        plt.show()            # opens the summary figure and yours; the script continues when you close them
    else:
        plt.close("all")      # run_all.py and GitHub: nothing to show, so free the figures

    return code_sweep, duty_sweep


def save_summary_figure(code_sweep, duty_sweep):
    # The three-panel figure saved as results/scpa.png (the README shows it).
    # subplots(1, 3): one figure, three plots side by side, panel[0] to panel[2].
    fig, panel = plt.subplots(1, 3, figsize=(15, 4.2))
    full_code = code_sweep.iloc[-1]                      # the last row: code 32
    above_zero = code_sweep[code_sweep.code > 0]         # code 0 sends no power: no dB for it
    backoff_dB = 10 * np.log10(above_zero.pout_W / full_code.pout_W)

    panel[0].plot(code_sweep.code, code_sweep.vout_peak_V, "o-")
    panel[0].plot(code_sweep.code, full_code.vout_peak_V * code_sweep.code / N, "--", label="ideal n/N")
    panel[0].set(xlabel="amplitude code n", ylabel="output fundamental, V peak",
                 title="AM-AM: the array is an RF DAC")
    panel[0].legend()

    panel[1].plot(backoff_dB, 100 * above_zero.eff_sim, "o-", label="ngspice")
    panel[1].plot(backoff_dB, 100 * above_zero.eff_theory, "--", label="theory, ideal switches")
    panel[1].set(xlabel="output power back-off, dB", ylabel="efficiency, %",
                 title="Efficiency vs back-off", xlim=(-15, 0.5))
    panel[1].legend()

    panel[2].plot(duty_sweep.duty, duty_sweep.HD2_dBc, "o-", label="HD2")
    panel[2].plot(duty_sweep.duty, duty_sweep.HD3_dBc, "s-", label="HD3")
    for guide in (1 / 3, 1 / 2, 2 / 3):
        panel[2].axvline(guide, color="0.6", lw=0.8)    # grey vertical guide lines
    panel[2].set(xlabel="drive duty cycle", ylabel="harmonic at the load, dBc",
                 title="Harmonics vs duty (HD3 nulls at 1/3, 2/3)")
    panel[2].legend()

    for one_panel in panel:
        one_panel.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_FOLDER, "scpa.png"), dpi=130)
    # The figure stays open: main() shows it (show_plots=True) or closes it.


# These lines run only when you start this file yourself (python tx_am_scpa/scpa.py).
if __name__ == "__main__":
    code_sweep, duty_sweep = main(show_plots=True)
    # Print chosen columns of the table; Pout in mW for reading.
    printout = code_sweep[["code", "vout_peak_V", "pout_W", "eff_sim", "eff_theory"]].copy()
    printout["pout_W"] = 1e3 * printout.pout_W
    printout = printout.rename(columns={"pout_W": "pout_mW"})
    print(printout.round(3).to_string(index=False))
    # The duty-sweep row nearest 1/3: idxmin() gives the row label where |duty - 1/3| is smallest.
    nearest_third = duty_sweep.loc[(duty_sweep.duty - 1 / 3).abs().idxmin()]
    print(f"HD3 at duty {nearest_third.duty:.3f}: {nearest_third.HD3_dBc:.1f} dBc")
