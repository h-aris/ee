"""TX system: a polar 64-QAM transmitter built from the two simulated paths.

AM path: the SCPA's amplitude codes, using the AM-AM and AM-PM curves that
ngspice produced (results/scpa_codes.csv). PM path: the NCO's P-bit phase word
(tx_pm_nco). Python recombines them and measures what a transmitter is judged
on: EVM, ACLR and the average efficiency at the signal's back-off.

Also sweeps the AM-to-PM timing skew. In a polar TX the two paths travel
through different circuits, and a delay between them shows up as spectral
regrowth and EVM; aligning them is part of every polar bring-up.

Run:  python tx_system/polar_tx.py   (needs results/scpa_codes.csv first)
"""
import os

import numpy as np
from scipy import signal

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
RS = 5e6          # symbol rate, Hz
OS = 32           # samples per symbol
FS = RS * OS      # 160 MHz sample rate of the digital front end
ALPHA = 0.25      # root-raised-cosine roll-off
NSYM = 4096
EVM_LIMIT = 0.08  # 8 %: LTE requirement for 64-QAM
ACLR_LIMIT = -30  # dBc, adjacent channel


def rrc(alpha=ALPHA, span=12, os_=OS):
    t = np.arange(-span * os_ // 2, span * os_ // 2 + 1) / os_
    h = np.zeros_like(t)
    for i, x in enumerate(t):
        if abs(x) < 1e-9:
            h[i] = 1 - alpha + 4 * alpha / np.pi
        elif abs(abs(4 * alpha * x) - 1) < 1e-9:
            h[i] = alpha / np.sqrt(2) * ((1 + 2 / np.pi) * np.sin(np.pi / (4 * alpha))
                                         + (1 - 2 / np.pi) * np.cos(np.pi / (4 * alpha)))
        else:
            h[i] = (np.sin(np.pi * x * (1 - alpha)) + 4 * alpha * x * np.cos(np.pi * x * (1 + alpha))) \
                / (np.pi * x * (1 - (4 * alpha * x)**2))
    return h / np.sqrt(np.sum(h**2))


def qam64(n, rng):
    lv = np.arange(-7, 8, 2)
    return (rng.choice(lv, n) + 1j * rng.choice(lv, n)) / np.sqrt(42)


def load_scpa():
    d = np.loadtxt(os.path.join(OUT, "scpa_codes.csv"), delimiter=",", skiprows=1)
    codes = np.arange(0, int(d[-1, 0]) + 1)
    amp = np.interp(codes, d[:, 0], d[:, 1])
    ph = np.interp(codes, d[:, 0], np.unwrap(np.radians(d[:, 2])))
    ph -= ph[-1]                                   # AM-PM relative to full code
    return codes, amp, ph, d


def transmit(x, codes, amp, ampm, pm_bits, skew_s=0.0):
    """Polar TX: quantize |x| to an SCPA code and angle(x) to a pm_bits word."""
    n = codes[-1]
    a = np.abs(x)
    if skew_s:                                     # AM path arrives late by skew_s
        t = np.arange(len(a)) / FS
        a = np.interp(t - skew_s, t, a)
    code = np.clip(np.round(a / a.max() * n), 0, n).astype(int)
    steps = 2**pm_bits
    phi = np.round(np.angle(x) / (2 * np.pi) * steps) * 2 * np.pi / steps
    return amp[code] * np.exp(1j * (phi + ampm[code])), code


def evm(y, ref, mf):
    """EVM after the matched filter, sampled at the symbol instants (gain fitted)."""
    yr = np.convolve(y, mf)[len(mf) - 1::OS][:NSYM]
    rr = np.convolve(ref, mf)[len(mf) - 1::OS][:NSYM]
    k = slice(20, NSYM - 20)                       # skip filter edges
    g = np.vdot(rr[k], yr[k]) / np.vdot(rr[k], rr[k])
    e = yr[k] - g * rr[k]
    return np.sqrt(np.mean(np.abs(e)**2) / np.mean(np.abs(g * rr[k])**2)), yr[k] / g


def aclr(y):
    f, p = signal.welch(y, fs=FS, nperseg=4096, return_onesided=False, detrend=False)
    bw = RS * (1 + ALPHA)
    main = np.sum(p[np.abs(f) <= bw / 2])
    adj = [np.sum(p[np.abs(f - s * bw) <= bw / 2]) for s in (-1, 1)]
    return 10 * np.log10(max(adj) / main), f, p


def main():
    rng = np.random.default_rng(7)
    codes, amp, ampm, d = load_scpa()
    h = rrc()
    sym = qam64(NSYM, rng)
    up = np.zeros(NSYM * OS, complex)
    up[::OS] = sym
    x = np.convolve(up, h)                         # ideal baseband TX signal
    papr = 10 * np.log10(np.max(np.abs(x)**2) / np.mean(np.abs(x)**2))

    rows, keep = [], {}
    for pm_bits in (6, 8, 10):
        for skew_ns in (0, 1, 2, 5):
            y, code = transmit(x, codes, amp, ampm, pm_bits, skew_ns * 1e-9)
            e, const = evm(y, x, h)
            a, f, p = aclr(y)
            rows.append((pm_bits, skew_ns, 100 * e, 20 * np.log10(e), a))
            keep[(pm_bits, skew_ns)] = (const, f, p, code)

    # Average efficiency at this signal's back-off, from the per-code simulation
    _, code = transmit(x, codes, amp, ampm, 6)
    pout = np.interp(code, d[:, 0], d[:, 3])
    psup = np.interp(code, d[:, 0], d[:, 4])
    eff_avg = pout.mean() / psup.mean()
    eff_peak = d[-1, 3] / d[-1, 4]

    # The same signal through the cascode class-AB PA instead (no polar split):
    # its AM-AM and AM-PM from ngspice, peaks placed at its 1 dB compression.
    lin = linear_pa(x, h)

    rows = np.array(rows)
    np.savetxt(os.path.join(OUT, "polar_tx.csv"), rows, delimiter=",",
               header="pm_bits,skew_ns,evm_pct,evm_dB,aclr_dBc", comments="")
    plot(rows, keep, x, papr)
    return rows, papr, eff_avg, eff_peak, lin


def linear_pa(x, h):
    path = os.path.join(OUT, "pa_sweep.csv")
    if not os.path.exists(path):
        return None
    import pandas as pd
    df = pd.read_csv(path).sort_values("amp_in")
    g0 = df.gain_dB.iloc[0]
    a_p1 = float(df[df.gain_dB <= g0 - 1].amp_in.iloc[0])     # drive at P1dB
    a = np.abs(x) / np.abs(x).max() * a_p1                     # envelope as drive amplitude
    amp = np.interp(a, df.amp_in, df.vout_pk, left=0)
    ph = np.radians(np.interp(a, df.amp_in, df.ampm_deg))
    y = amp * np.exp(1j * (np.angle(x) + ph))
    e, _ = evm(y, x, h)
    acl, _, _ = aclr(y)
    pout = np.interp(a, df.amp_in, df.pout_W, left=0)
    pdc = np.interp(a, df.amp_in, df.pdc_W)
    return dict(evm_pct=100 * e, aclr_dBc=acl, eff_avg=pout.mean() / pdc.mean())


def plot(rows, keep, x, papr):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
    const = keep[(6, 0)][0]
    ax[0].plot(const.real, const.imag, ".", ms=2)
    ax[0].set(title="64-QAM after the polar TX (6-bit phase, 5-bit amplitude)",
              xlabel="I", ylabel="Q", aspect="equal")
    for skew in (0, 5):
        _, f, p, _ = keep[(6, skew)]
        o = np.argsort(f)
        ax[1].plot(f[o] / 1e6, 10 * np.log10(p[o] / p.max()), lw=0.8, label=f"skew {skew} ns")
    bw = RS * (1 + ALPHA) / 1e6
    for s in (-1.5, -0.5, 0.5, 1.5):
        ax[1].axvline(s * bw, color="0.6", lw=0.6)
    ax[1].set(xlim=(-20, 20), ylim=(-80, 5), xlabel="offset from carrier, MHz",
              ylabel="PSD, dB", title="Spectrum: AM/PM skew regrows the skirts")
    ax[1].legend()
    for b in (6, 8, 10):
        r = rows[rows[:, 0] == b]
        ax[2].plot(r[:, 1], r[:, 3], "o-", label=f"{b}-bit phase")
    ax[2].axhline(20 * np.log10(EVM_LIMIT), color="r", lw=0.8, label="8 % limit")
    ax[2].set(xlabel="AM-to-PM skew, ns", ylabel="EVM, dB", title=f"EVM vs skew (PAPR {papr:.1f} dB)")
    ax[2].legend()
    for a in ax:
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "polar_tx.png"), dpi=130)


if __name__ == "__main__":
    rows, papr, eff_avg, eff_peak, lin = main()
    print("cascode class-AB PA, same signal:", lin)
    print(f"PAPR {papr:.1f} dB, efficiency peak {100 * eff_peak:.1f} %, "
          f"average at this back-off {100 * eff_avg:.1f} %")
    print("pm_bits skew_ns  EVM%   EVM_dB  ACLR_dBc")
    for r in rows:
        print(f"{int(r[0]):6d} {r[1]:7.0f} {r[2]:6.2f} {r[3]:7.1f} {r[4]:8.1f}")
