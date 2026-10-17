"""The cascode PA at full drive: Xyce against ngspice, on the same circuit.

Reads the waveforms of two simulators:
  ngspice: results/decks/pa_full_drive/w.txt, kept by pa.py at its strongest drive
  Xyce:    tx_pa_cascode/xyce/pa_full_drive_xyce.cir.prn, written by
           Xyce pa_full_drive_xyce.cir (inside the IIC-OSIC-TOOLS image)
and computes from each the same numbers pa.py reports: output amplitude and
phase, output power, supply power, drain efficiency, and the largest
drain-source voltage on each transistor. Then it prints them side by side.

Run:  python tx_pa_cascode/xyce/compare_xyce.py   (from ~/edu/ee, after pa.py
      or run_all.py and the Xyce run; shows the summary figure, then the table)
"""
# ---------------------------------------------------------------------------------
# Why compare two simulators? Each solves the same circuit equations with its own
# numerics: time-step control, convergence, its own copy of the BSIM4 model code.
# If two independent tools agree to a fraction of a percent, the numbers belong to
# the circuit, not to one tool. That is a standard verification step (L7 7.14).
#
# How the file is laid out, as in pa.py:
#   imports and constants
#   functions: read_ngspice, read_xyce, pa_numbers
#   main(): reads both, computes, prints; ends with a commented plot template
#       where every variable is alive, then shows the summary figure.
# ---------------------------------------------------------------------------------
import os
import sys

import matplotlib.pyplot as plt   # plotting, MATLAB style
import numpy as np                # arrays and maths
import pandas as pd               # tables with named columns, like a MATLAB table

HERE = os.path.dirname(os.path.abspath(__file__))       # this folder: tx_pa_cascode/xyce
REPO = os.path.join(HERE, "..", "..")                    # ~/edu/ee
sys.path.insert(0, REPO)                                 # so `common` can be imported (MATLAB: addpath)
from common.spice import fourier  # noqa: E402  (the harmonics of a waveform, as pa.py uses)

NGSPICE_WAVEFORMS = os.path.join(REPO, "results", "decks", "pa_full_drive", "w.txt")
XYCE_WAVEFORMS = os.path.join(HERE, "pa_full_drive_xyce.cir.prn")
F0 = 1e9          # carrier, Hz
VDD = 2.4         # PA supply, V
RL = 50.0         # load, ohm


def read_ngspice():
    # wrdata wrote (time, value) pairs: v(out), i(vdd), v(d), v(x) -> columns 1, 3, 5, 7.
    columns = np.loadtxt(NGSPICE_WAVEFORMS)
    return pd.DataFrame(dict(time_s=columns[:, 0], vout=columns[:, 1], idd=columns[:, 3],
                             v_drain=columns[:, 5], v_mid=columns[:, 7]))


def read_xyce():
    # The .prn file: a header row (Index TIME V(OUT) I(V_DD) V(DRAIN) V(MID)), one
    # row per time step, and a last line "End of Xyce(TM) Simulation".
    # sep=r"\s+": columns separated by any number of spaces; skipfooter=1: drop the last line.
    prn = pd.read_csv(XYCE_WAVEFORMS, sep=r"\s+", skipfooter=1, engine="python")
    return pd.DataFrame(dict(time_s=prn["TIME"], vout=prn["V(OUT)"], idd=prn["I(V_DD)"],
                             v_drain=prn["V(DRAIN)"], v_mid=prn["V(MID)"]))


def pa_numbers(waveforms):
    """The numbers pa.py reports, from one simulator's waveforms (a table)."""
    time_s = waveforms.time_s.to_numpy()                 # .to_numpy(): the column as a plain array
    harmonics = fourier(time_s, waveforms.vout.to_numpy(), F0, n_harm=3)
    settled = time_s >= time_s[-1] - 10 / F0             # the last 10 periods
    settled_time = time_s[settled]
    # Average supply power: -VDD x the average current into the source's + pin.
    pdc_W = -VDD * np.trapezoid(waveforms.idd.to_numpy()[settled], settled_time) / (settled_time[-1] - settled_time[0])
    pout_W = abs(harmonics[0])**2 / (2 * RL)
    v_drain = waveforms.v_drain.to_numpy()
    v_mid = waveforms.v_mid.to_numpy()
    return dict(vout_pk_V=abs(harmonics[0]),
                phase_deg=np.degrees(np.angle(harmonics[0])),
                pout_mW=1e3 * pout_W,
                pdc_mW=1e3 * pdc_W,
                eff_pct=100 * pout_W / pdc_W,
                vds_in_max_V=v_mid[settled].max(),                  # M_IN: from MID to VSS
                vds_cas_max_V=(v_drain - v_mid)[settled].max())    # M_CAS: from DRAIN to MID


def main(show_plots=False):
    # --- 1. Read both simulators' waveforms ------------------------------------------
    ngspice_waveforms = read_ngspice()
    xyce_waveforms = read_xyce()

    # --- 2. The same numbers from each, side by side ----------------------------------
    ngspice_numbers = pa_numbers(ngspice_waveforms)
    xyce_numbers = pa_numbers(xyce_waveforms)
    # A table: one row per quantity, one column per simulator.
    comparison = pd.DataFrame(dict(ngspice=ngspice_numbers, xyce=xyce_numbers))
    comparison["difference_pct"] = 100 * (comparison.xyce - comparison.ngspice) / comparison.ngspice.abs()

    # --- 3. Summary figure: the last 3 periods of each waveform, on top of each other ---
    fig, panel = plt.subplots(1, 2, figsize=(12, 4.2))
    for name, waveforms, style in (("ngspice", ngspice_waveforms, "-"), ("Xyce", xyce_waveforms, "--")):
        last_3_periods = waveforms[waveforms.time_s >= 27e-9]
        time_ns = 1e9 * last_3_periods.time_s
        panel[0].plot(time_ns, last_3_periods.vout, style, label=f"v(OUT), {name}")
        panel[1].plot(time_ns, last_3_periods.v_drain - last_3_periods.v_mid, style, label=f"Vds of M_CAS, {name}")
        panel[1].plot(time_ns, last_3_periods.v_mid, style, label=f"Vds of M_IN, {name}")
    panel[0].set(xlabel="time, ns", ylabel="V", title="Output at full drive: the two simulators")
    panel[1].axhline(2.4, color="r", lw=0.8, label="run_all's limit, 2.4 V")
    panel[1].set(xlabel="time, ns", ylabel="V", title="Drain-source voltage of each transistor")
    for one_panel in panel:
        one_panel.legend(fontsize=8)
        one_panel.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "compare_xyce.png"), dpi=130)

    # --- 4. Your own plots: every variable above is available here --------------------
    # To add a plot: select the five lines below, press Ctrl+/ in VS Code to remove
    # the "# ", and put in real names, for example var_x -> xyce_waveforms.time_s,
    # var_y -> xyce_waveforms.idd
    # plt.figure()
    # plt.plot(var_x, var_y, "o-")
    # plt.xlabel("x axis label")
    # plt.ylabel("y axis label")
    # plt.title("title")

    # --- 5. Show the figures, or close them -------------------------------------
    if show_plots:
        plt.show()            # opens the summary figure and yours; the script continues when you close them
    else:
        plt.close("all")

    return comparison


# These lines run only when you start this file yourself.
if __name__ == "__main__":
    comparison = main(show_plots=True)
    print(comparison.round(4).to_string())
