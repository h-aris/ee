"""Run every block, check it against its spec, and write results/summary.md.

Each check prints PASS or FAIL with the measured number next to the limit.
The NCO block also runs a deliberately broken RTL build, which must FAIL, and
the LNA is re-simulated without its cascode, where the match must break:
a check that cannot fail proves nothing.

OPEN marks a spec the current design does not meet yet and that is a planned
next step (see README, "Ladder"). OPEN does not fail the run; FAIL does.

Usage:  python run_all.py
"""
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
for sub in ("", "tx_am_scpa", "tx_pm_nco", "tx_pa_cascode", "tx_system", "rx_lna"):
    sys.path.insert(0, os.path.join(ROOT, sub))

import lna        # noqa: E402
import pa         # noqa: E402
import polar_tx   # noqa: E402
import run_nco    # noqa: E402
import scpa       # noqa: E402

checks = []


def check(block, name, value, limit, ok, unit="", open_item=False):
    status = "PASS" if ok else ("OPEN" if open_item else "FAIL")
    checks.append((block, name, value, limit, unit, status))
    print(f"[{status}] {block:10s} {name:40s} {value:>10} {unit:4s} (spec {limit})")


def main():
    t0 = time.time()
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)

    rows, hd = scpa.main()
    gap = np.max(np.abs(rows[2:, 5] - rows[2:, 6]))
    check("TX AM", "Pout at full code", f"{1e3 * rows[-1, 3]:.2f}", ">= 4.5", rows[-1, 3] >= 4.5e-3, "mW")
    check("TX AM", "efficiency vs SCPA theory, worst gap", f"{100 * gap:.1f}", "<= 3", gap <= 0.03, "pts")
    tol16 = 0.02  # allowed |eff_sim - eff_theory| at code 16 (half scale), fraction: 0.02 = 2 pts
    r16 = rows[rows[:, 0] == 16][0]
    gap16 = abs(r16[5] - r16[6])
    check("TX AM", "efficiency vs theory at code 16/32", f"{100 * gap16:.2f}", f"<= {100 * tol16:g}",
          gap16 <= tol16, "pts")
    i3 = np.argmin(np.abs(hd[:, 0] - 1 / 3))
    i2 = np.argmin(np.abs(hd[:, 0] - 1 / 2))
    check("TX AM", "HD3 at 1/3 duty", f"{hd[i3, 2]:.1f}", "<= -40", hd[i3, 2] <= -40, "dBc")
    check("TX AM", "HD2 at 1/2 duty", f"{hd[i2, 1]:.1f}", "<= -40", hd[i2, 1] <= -40, "dBc")

    good, bad, cells = run_nco.main()
    check("TX PM", "cocotb tests on RTL", f"{sum(good.values())}/{len(good)}", "all pass", all(good.values()))
    check("TX PM", "mutant RTL caught by phase test", str(not bad["phase_modulation"]),
          "True", not bad["phase_modulation"])
    check("TX PM", "Yosys synthesis, generic gates", str(cells), "> 0", bool(cells), "cells")

    df, p = pa.main()
    check("TX PA", "saturated output power", f"{p['psat_dBm']:.1f}", ">= 17", p["psat_dBm"] >= 17, "dBm")
    check("TX PA", "peak drain efficiency", f"{100 * p['eff_peak']:.1f}", ">= 50", p["eff_peak"] >= 0.5, "%")
    e6 = pa.eff_at(df, -6)
    check("TX PA", "drain efficiency at 6 dB back-off", f"{100 * e6:.1f}", "report", True, "%")
    check("TX PA", "AM-PM at saturation", f"{p['ampm_peak_deg']:.1f}", "report", True, "deg")
    check("TX PA", "worst device Vds peak (1.2 V devices)", f"{p['vds_max']:.2f}", "<= 2.4",
          p["vds_max"] <= 2.4, "V", open_item=True)

    res, papr, eff_avg, eff_peak, lin = polar_tx.main()
    r0 = res[(res[:, 0] == 6) & (res[:, 1] == 0)][0]
    check("TX system", "EVM, 64-QAM, 6-bit phase", f"{r0[2]:.2f}", "<= 8", r0[2] <= 8, "%")
    check("TX system", "ACLR, 64-QAM, 6-bit phase", f"{r0[4]:.1f}", "<= -30", r0[4] <= -30, "dBc")
    r5 = res[(res[:, 0] == 6) & (res[:, 1] == 5)][0]
    check("TX system", "5 ns AM/PM skew degrades EVM", f"{r5[3] - r0[3]:+.1f}", "> 0", r5[3] > r0[3], "dB")
    check("TX system", f"SCPA average efficiency, {papr:.1f} dB PAPR", f"{100 * eff_avg:.1f}", "report",
          True, "%")
    check("TX system", "class-AB PA average efficiency, same", f"{100 * lin['eff_avg']:.1f}", "report",
          True, "%")
    check("TX system", "class-AB PA EVM at P1dB peaks, no DPD", f"{lin['evm_pct']:.1f}", "<= 8",
          lin["evm_pct"] <= 8, "%", open_item=True)

    s = lna.main()
    check("RX LNA", "S11 at 1 GHz", f"{s['S11']:.1f}", "<= -10", s["S11"] <= -10, "dB")
    check("RX LNA", "S21 at 1 GHz", f"{s['S21']:.1f}", ">= 15", s["S21"] >= 15, "dB")
    check("RX LNA", "noise figure at 1 GHz (Lg Q = 30)", f"{s['NF']:.2f}", "<= 2", s["NF"] <= 2, "dB")
    check("RX LNA", "cascode removed: match breaks (Miller)", f"{s['S11_no_cascode']:.1f}", "> -10",
          s["S11_no_cascode"] > -10, "dB")

    lines = ["| Block | Check | Result | Spec | |", "|---|---|---|---|---|"]
    for b, n, v, lim, u, st in checks:
        lines.append(f"| {b} | {n} | {v} {u} | {lim} | {st} |")
    with open(os.path.join(ROOT, "results", "summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    npass = sum(c[-1] == "PASS" for c in checks)
    nopen = sum(c[-1] == "OPEN" for c in checks)
    nfail = sum(c[-1] == "FAIL" for c in checks)
    print(f"\n{npass} PASS, {nopen} OPEN, {nfail} FAIL in {time.time() - t0:.0f} s; "
          "table in results/summary.md")
    return nfail == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
