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

Run:  python tx_pa_cascode/pa.py   (writes results/pa_sweep.csv and pa.png)
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.models import LMIN, NMOS  # noqa: E402
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
AMPS = np.round(np.geomspace(0.02, 0.9, 16), 4)   # input sine amplitudes, V peak
OUT = os.path.join(os.path.dirname(__file__), "..", "results")


def deck(amp, cd, analysis="tran"):
    nf = round(W / 10e-6)
    lines = ["* cascode class-AB PA", NMOS,
             f"Vdd vdd 0 {VDD}", f"Vcas cg 0 {VCAS}",
             f"Vin g 0 DC {VBIAS} AC 1 SIN({VBIAS} {amp} {F0})",
             f"M1 x g 0 0 nch W={W} L={LMIN} nf={nf}",
             f"M2 d cg x 0 nch W={W} L={LMIN} nf={nf}",
             f"Ld vdd d {LD}", f"Rp vdd d {W0 * LD * LD_Q}", f"Cd d 0 {cd}",
             "Cout d out 100p", f"RL out 0 {RL}", ".control"]
    if analysis == "ac":
        lines += ["ac lin 201 0.8g 1.2g", "wrdata {dir}/ac.txt mag(v(out))"]
    else:
        lines += ["tran 1p 30n 0 1p", "wrdata {dir}/w.txt v(out) i(vdd) v(d) v(x)"]
    return "\n".join(lines + [".endc", ".end"])


def tune_tank():
    """Cd for resonance at F0: the hand value, then corrected for the
    transistors' drain capacitance by finding the small-signal gain peak."""
    cd = 1 / (W0**2 * LD)
    for _ in range(3):
        d = run(deck(0.01, cd, "ac"), ["ac.txt"])["ac.txt"]
        fpk = d[np.argmax(d[:, 1]), 0]
        cd *= (fpk / F0)**2
    return cd


def simulate(amp, cd, keep=None):
    d = run(deck(amp, cd), ["w.txt"], keep=keep)["w.txt"]
    t, vout, idd, vd, vx = d[:, 0], d[:, 1], d[:, 3], d[:, 5], d[:, 7]
    h = fourier(t, vout, F0, n_harm=3)
    last = t >= t[-1] - 10 / F0
    tl = t[last]
    pdc = -VDD * np.trapezoid(idd[last], tl) / (tl[-1] - tl[0])
    pout = abs(h[0])**2 / (2 * RL)
    return dict(amp_in=amp, vout_pk=abs(h[0]), phase_deg=np.degrees(np.angle(h[0])),
                pout_W=pout, pdc_W=pdc, eff=pout / pdc,
                hd2_dBc=20 * np.log10(abs(h[1]) / abs(h[0])),
                hd3_dBc=20 * np.log10(abs(h[2]) / abs(h[0])),
                vds1_max=vx[last].max(), vds2_max=(vd - vx)[last].max())


def main():
    os.makedirs(OUT, exist_ok=True)
    cd = tune_tank()
    df = pd.DataFrame([simulate(a, cd, keep="pa_full_drive" if a == AMPS[-1] else None)
                       for a in AMPS])
    df["pout_dBm"] = 10 * np.log10(df.pout_W / 1e-3)
    df["gain_dB"] = 20 * np.log10(df.vout_pk / df.amp_in)
    df["ampm_deg"] = df.phase_deg - df.phase_deg.iloc[0]
    df["backoff_dB"] = df.pout_dBm - df.pout_dBm.max()
    # 1 dB compression: first drive where gain has fallen 1 dB below small-signal
    g0 = df.gain_dB.iloc[0]
    comp = df[df.gain_dB <= g0 - 1]
    p1db = comp.pout_dBm.iloc[0] if len(comp) else np.nan
    df.to_csv(os.path.join(OUT, "pa_sweep.csv"), index=False, float_format="%.6g")
    plot(df)
    peak = df.loc[df.pout_W.idxmax()]
    return df, dict(cd_pF=cd * 1e12, gain_dB=g0, p1db_dBm=p1db, psat_dBm=peak.pout_dBm,
                    eff_peak=df.eff.max(), ampm_peak_deg=peak.ampm_deg,
                    vds_max=max(df.vds1_max.max(), df.vds2_max.max()))


def eff_at(df, backoff_db):
    """Efficiency at a given back-off from the peak output power, interpolated."""
    d = df.sort_values("backoff_dB")
    return float(np.interp(backoff_db, d.backoff_dB, d.eff))


def plot(df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
    ax[0].plot(df.amp_in, df.pout_dBm, "o-")
    ax[0].set(xscale="log", xlabel="input amplitude, V peak", ylabel="Pout, dBm",
              title="AM-AM: linear, then compressing")
    ax2 = ax[0].twinx()
    ax2.plot(df.amp_in, df.ampm_deg, "s--", color="C1")
    ax2.set_ylabel("AM-PM, degrees", color="C1")
    bo = np.linspace(-15, 0, 100)
    ax[1].plot(df.backoff_dB, 100 * df.eff, "o-", label="cascode class AB, ngspice")
    ax[1].plot(bo, 100 * np.pi / 4 * 10**(bo / 20), "--", label="ideal class B, (pi/4) Vp/VDD")
    ax[1].set(xlabel="output power back-off, dB", ylabel="drain efficiency, %", xlim=(-15, 0.5),
              title="Efficiency falls with the amplitude")
    ax[1].legend()
    ax[2].plot(df.pout_dBm, df.hd2_dBc, "o-", label="HD2")
    ax[2].plot(df.pout_dBm, df.hd3_dBc, "s-", label="HD3")
    ax[2].set(xlabel="Pout, dBm", ylabel="harmonic at the load, dBc",
              title="Harmonics after the tank")
    ax[2].legend()
    for a in ax:
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "pa.png"), dpi=130)


if __name__ == "__main__":
    df, s = main()
    print(df[["amp_in", "pout_dBm", "gain_dB", "eff", "ampm_deg", "hd3_dBc"]].round(3).to_string())
    print({k: round(float(v), 3) for k, v in s.items()})
    print("efficiency at -6 dB back-off:", round(eff_at(df, -6), 3))
