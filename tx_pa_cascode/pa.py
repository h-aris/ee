"""TX linear reference: a cascode (two-stack) class-AB PA at 1 GHz in CMOS.

Why it is here. The SCPA in tx_am_scpa is a switching PA: its transistors are
either fully on or off, and amplitude comes from how many capacitors switch.
This PA is the classic alternative: the input transistor works as a current
source whose current follows the input sine, and a tank turns that current
into a sine at the load. It is linear by construction and needs no polar
split, but its efficiency falls fast at back-off: in ideal class B,
eta = (pi/4) * Vp/VDD, and Vp shrinks with the square root of output power.
The comparison between the two at back-off is the reason polar SCPAs exist.

Why a cascode (stack). The drain swings to about twice VDD. Stacking a second
device, whose gate is held at a fixed bias, splits that swing between two
transistors so neither sees more than it can stand. It also hides the input
device's gate-drain capacitance from the output (no Miller), as in the LNA.

The input is an ideal sine with a DC bias, so driver power is not counted:
efficiencies here are drain efficiencies, output power over supply power.

Run:  python tx_pa_cascode/pa.py   (writes results/pa_sweep.csv and pa.png,
      shows the summary figure, then prints the table)
"""
# ---------------------------------------------------------------------------------
# Same shape as scpa.py: imports and design values -> netlist() -> simulate() ->
# main(), which ends with a commented plot template where all its variables are
# alive, then shows the summary figure.
# The sweep is a pandas table (a DataFrame) whose columns have names:
# sweep.pout_W, sweep.eff, sweep.gain_dB. Adding a column is one line: sweep["new"] = ...
# ---------------------------------------------------------------------------------
import os
import sys

import matplotlib.pyplot as plt   # plotting, MATLAB style
import numpy as np                # arrays and maths
import pandas as pd               # tables with named columns, like a MATLAB table

# Make the repo folder findable, so `common` can be imported (MATLAB: addpath).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.models import LMIN, NMOS  # noqa: E402  (the transistor model line, the channel length)
from common.spice import fourier, run  # noqa: E402

F0 = 1e9
W0 = 2 * np.pi * F0
VDD = 2.4          # PA supply: two stacked 1.2 V devices, V
VCAS = 1.6         # cascode gate bias, V
VBIAS = 0.50       # input gate bias, V: just above threshold, class AB
W = 1.2e-3         # device width, m (both devices)
RL = 50.0          # load, ohm
LD = 4e-9          # drain tank inductor, also the DC feed, H
LD_Q = 20          # its quality factor
# 16 input amplitudes spaced evenly on a log scale from 20 mV to 0.9 V (MATLAB's
# logspace), rounded to 4 decimals so the numbers in file names stay tidy.
INPUT_AMPLITUDES_V = np.round(np.geomspace(0.02, 0.9, 16), 4)   # V peak
RESULTS_FOLDER = os.path.join(os.path.dirname(__file__), "..", "results")


def netlist(input_amplitude_V, cd, analysis="tran"):
    """The PA as SPICE text, driven by a sine of that peak amplitude, with drain capacitor cd."""
    fingers = round(W / 10e-6)          # fingers of 10 um each
    lines = ["* cascode class-AB PA", NMOS,
             f"Vdd vdd 0 {VDD}", f"Vcas cg 0 {VCAS}",
             # Input: DC bias plus a sine at F0; "AC 1" serves the small-signal run.
             f"Vin g 0 DC {VBIAS} AC 1 SIN({VBIAS} {input_amplitude_V} {F0})",
             # M1 input device (drain x), M2 cascode on top (gate at VCAS, drain d).
             f"M1 x g 0 0 nch W={W} L={LMIN} nf={fingers}",
             f"M2 d cg x 0 nch W={W} L={LMIN} nf={fingers}",
             # Drain tank: LD (also brings VDD in), its loss Rp, and Cd to resonate.
             f"Ld vdd d {LD}", f"Rp vdd d {W0 * LD * LD_Q}", f"Cd d 0 {cd}",
             "Cout d out 100p", f"RL out 0 {RL}", ".control"]
    # The same circuit serves two analyses, chosen by the `analysis` argument.
    if analysis == "ac":
        # Small-signal sweep 0.8 to 1.2 GHz, to find where the tank resonates.
        lines += ["ac lin 201 0.8g 1.2g", "wrdata {dir}/ac.txt mag(v(out))"]
    else:
        # Large-signal transient, 30 periods: output, supply current, both drains.
        lines += ["tran 1p 30n 0 1p", "wrdata {dir}/w.txt v(out) i(vdd) v(d) v(x)"]
    return "\n".join(lines + [".endc", ".end"])


def tune_tank():
    """Cd for resonance at F0: the hand value, then corrected for the
    transistors' drain capacitance by finding the small-signal gain peak."""
    cd = 1 / (W0**2 * LD)          # hand value: resonance with LD alone
    for attempt in range(3):       # three corrections
        ac_sweep = run(netlist(0.01, cd, "ac"), ["ac.txt"])["ac.txt"]
        freqs_Hz = ac_sweep[:, 0]
        gain = ac_sweep[:, 1]
        peak_freq_Hz = freqs_Hz[np.argmax(gain)]     # argmax = index of the largest value
        # The transistors add their own capacitance, so the peak sits low; since
        # f ~ 1/sqrt(C), scaling cd by (peak/F0)^2 moves the peak onto F0.
        cd = cd * (peak_freq_Hz / F0)**2
    return cd


def simulate(input_amplitude_V, cd, keep=None):
    """One drive level. Returns a dictionary of numbers: one row of the sweep table."""
    waveforms = run(netlist(input_amplitude_V, cd), ["w.txt"], keep=keep)["w.txt"]
    # wrdata pairs: (t, vout), (t, idd), (t, vd), (t, vx) -> values in columns 1, 3, 5, 7.
    time_s = waveforms[:, 0]
    vout = waveforms[:, 1]
    supply_current = waveforms[:, 3]
    v_drain_top = waveforms[:, 5]       # node d: M2's drain, the output side
    v_drain_bottom = waveforms[:, 7]    # node x: M1's drain, between the two devices
    harmonics = fourier(time_s, vout, F0, n_harm=3)   # [0] fundamental, [1] 2nd, [2] 3rd
    settled = time_s >= time_s[-1] - 10 / F0         # the last 10 periods, settled
    settled_time = time_s[settled]
    pdc_W = -VDD * np.trapezoid(supply_current[settled], settled_time) / (settled_time[-1] - settled_time[0])
    pout_W = abs(harmonics[0])**2 / (2 * RL)
    return dict(amp_in=input_amplitude_V,
                vout_pk=abs(harmonics[0]),
                phase_deg=np.degrees(np.angle(harmonics[0])),
                pout_W=pout_W, pdc_W=pdc_W, eff=pout_W / pdc_W,
                hd2_dBc=20 * np.log10(abs(harmonics[1]) / abs(harmonics[0])),
                hd3_dBc=20 * np.log10(abs(harmonics[2]) / abs(harmonics[0])),
                # Largest drain-source voltage on each device: x for M1, d - x for M2.
                # This is the stress check that is OPEN in run_all.py.
                vds1_max=v_drain_bottom[settled].max(),
                vds2_max=(v_drain_top - v_drain_bottom)[settled].max())


def main(show_plots=False):
    # show_plots: False when run_all.py calls main(); True when you run this file.
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    cd_tuned = tune_tank()

    # --- 1. The power sweep: one simulation per input amplitude -------------------
    rows_of_sweep = []
    for input_amplitude_V in INPUT_AMPLITUDES_V:
        # Only the strongest drive keeps its netlist folder (results/decks/pa_full_drive),
        # so it can be opened in interactive ngspice. None = don't keep.
        keep_folder = "pa_full_drive" if input_amplitude_V == INPUT_AMPLITUDES_V[-1] else None
        rows_of_sweep.append(simulate(input_amplitude_V, cd_tuned, keep=keep_folder))
    sweep = pd.DataFrame(rows_of_sweep)      # one row per drive level, named columns

    # --- 2. New columns, computed from existing ones, whole columns at a time ---------
    sweep["pout_dBm"] = 10 * np.log10(sweep.pout_W / 1e-3)
    sweep["gain_dB"] = 20 * np.log10(sweep.vout_pk / sweep.amp_in)
    sweep["ampm_deg"] = sweep.phase_deg - sweep.phase_deg.iloc[0]    # phase change from the weakest drive
    sweep["backoff_dB"] = sweep.pout_dBm - sweep.pout_dBm.max()

    # --- 3. Headline numbers ---------------------------------------------------------
    small_signal_gain_dB = sweep.gain_dB.iloc[0]          # .iloc[0] = first row
    # 1 dB compression: the first drive where the gain has fallen 1 dB.
    compressed = sweep[sweep.gain_dB <= small_signal_gain_dB - 1]
    p1db_dBm = compressed.pout_dBm.iloc[0] if len(compressed) else np.nan
    peak_row = sweep.loc[sweep.pout_W.idxmax()]            # the row with the highest output power
    headline = dict(cd_pF=cd_tuned * 1e12, gain_dB=small_signal_gain_dB, p1db_dBm=p1db_dBm,
                    psat_dBm=peak_row.pout_dBm, eff_peak=sweep.eff.max(),
                    ampm_peak_deg=peak_row.ampm_deg,
                    vds_max=max(sweep.vds1_max.max(), sweep.vds2_max.max()))

    sweep.to_csv(os.path.join(RESULTS_FOLDER, "pa_sweep.csv"), index=False, float_format="%.6g")
    save_summary_figure(sweep)

    # --- 4. Your own plots: every variable above is available here --------------------
    # To add a plot: select the five lines below, press Ctrl+/ in VS Code to remove
    # the "# ", and put in real names, for example var_x -> sweep.pout_dBm,
    # var_y -> sweep.gain_dB
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

    return sweep, headline


def efficiency_at_backoff(sweep, backoff_dB):
    """Drain efficiency at a given back-off from peak power, interpolated."""
    by_backoff = sweep.sort_values("backoff_dB")       # np.interp needs increasing x values
    return float(np.interp(backoff_dB, by_backoff.backoff_dB, by_backoff.eff))


def save_summary_figure(sweep):
    # The three-panel figure saved as results/pa.png (the README shows it).
    fig, panel = plt.subplots(1, 3, figsize=(15, 4.4))
    panel[0].plot(sweep.amp_in, sweep.pout_dBm, "o-")
    panel[0].set(xscale="log", xlabel="input amplitude, V peak", ylabel="Pout, dBm",
                 title="AM-AM: linear, then compressing")
    right_axis = panel[0].twinx()            # a second y axis on the right of the same plot
    right_axis.plot(sweep.amp_in, sweep.ampm_deg, "s--", color="C1")
    right_axis.set_ylabel("AM-PM, degrees", color="C1")

    backoff_axis_dB = np.linspace(-15, 0, 100)
    panel[1].plot(sweep.backoff_dB, 100 * sweep.eff, "o-", label="cascode class AB, ngspice")
    # Ideal class B for comparison: (pi/4) Vp/VDD, with Vp/VDD = 10^(back-off/20).
    panel[1].plot(backoff_axis_dB, 100 * np.pi / 4 * 10**(backoff_axis_dB / 20), "--",
                  label="ideal class B, (pi/4) Vp/VDD")
    panel[1].set(xlabel="output power back-off, dB", ylabel="drain efficiency, %", xlim=(-15, 0.5),
                 title="Efficiency falls with the amplitude")
    panel[1].legend()

    panel[2].plot(sweep.pout_dBm, sweep.hd2_dBc, "o-", label="HD2")
    panel[2].plot(sweep.pout_dBm, sweep.hd3_dBc, "s-", label="HD3")
    panel[2].set(xlabel="Pout, dBm", ylabel="harmonic at the load, dBc",
                 title="Harmonics after the tank")
    panel[2].legend()

    for one_panel in panel:
        one_panel.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_FOLDER, "pa.png"), dpi=130)
    # The figure stays open: main() shows it (show_plots=True) or closes it.


# These lines run only when you start this file yourself (python tx_pa_cascode/pa.py).
if __name__ == "__main__":
    sweep, headline = main(show_plots=True)
    # Print six chosen columns, rounded, as a text table.
    print(sweep[["amp_in", "pout_dBm", "gain_dB", "eff", "ampm_deg", "hd3_dBc"]].round(3).to_string(index=False))
    for name, value in headline.items():     # .items() gives (name, value) pairs
        print(f"{name:14s} {value:8.3f}")
    print("efficiency at -6 dB back-off:", round(efficiency_at_backoff(sweep, -6), 3))
