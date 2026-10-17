"""Run every block, check it against its spec, and write results/summary.md.

Each check prints PASS or FAIL with the measured number next to the limit.
The NCO block also runs a deliberately broken RTL build, which must FAIL, and
the LNA is re-simulated without its cascode, where the match must break:
a check that cannot fail proves nothing.

OPEN marks a spec the current design does not meet yet and that is a planned
next step (see README, "Ladder"). OPEN does not fail the run; FAIL does.

Usage:  python run_all.py
"""
# ---------------------------------------------------------------------------------
# The regression run of the whole testbench (L7 7.14: "regression").
# It imports each block's script as a module, calls its main() to simulate, takes
# the numbers that come back and compares each with its specification through
# check(). GitHub Actions runs this same file on every push (.github/workflows).
# Read it top to bottom once: it is the table of contents of the repo.
# ---------------------------------------------------------------------------------
import os
import sys      # sys.path (where Python looks for modules) and sys.exit (exit code)
import time     # time.time(): seconds since 1970, used to time the run

import numpy as np

# ROOT = the folder this file is in. abspath makes it a full path; dirname drops
# the file name. Everything else is found relative to it, so the run works from
# any current folder.
ROOT = os.path.dirname(os.path.abspath(__file__))
# Python finds `import x` only in the script's folder, installed packages and the
# folders listed in sys.path. Each block lives in its own folder, so add them all.
# ("" adds ROOT itself, where common/ is.)
for sub in ("", "tx_am_scpa", "tx_pm_nco", "tx_pa_cascode", "tx_system", "rx_lna"):
    sys.path.insert(0, os.path.join(ROOT, sub))

# Now the block scripts can be imported by file name (lna.py -> lna).
# "# noqa: E402" only tells the style checker that imports after code are intended.
import lna        # noqa: E402   receiver: cascode LNA, S11, S21, noise figure
import pa         # noqa: E402   cascode class-AB PA, the linear reference
import polar_tx   # noqa: E402   the system: 64-QAM through the polar TX, EVM, ACLR
import run_nco    # noqa: E402   phase path: Verilog NCO, cocotb tests, Yosys
import scpa       # noqa: E402   amplitude path: switched-capacitor PA

# The list every check() call appends to; the summary table is built from it.
checks = []


def check(block, name, value, limit, ok, unit="", open_item=False):
    # ok is a True/False the caller computes, e.g. full_code.pout_W >= 4.5e-3.
    # A conditional expression: "PASS" if ok, else OPEN for a known, planned gap,
    # else FAIL. Only FAIL makes the whole run fail (see the end of main()).
    status = "PASS" if ok else ("OPEN" if open_item else "FAIL")
    # A tuple (fixed-length list) per check, appended to the global list.
    checks.append((block, name, value, limit, unit, status))
    # Format codes inside the f-string braces: :10s pads text to 10 characters,
    # :>10 right-aligns in 10. That is what lines up the columns on screen.
    print(f"[{status}] {block:10s} {name:40s} {value:>10} {unit:4s} (spec {limit})")


def main():
    start_time = time.time()
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)

    # --- TX AM: the switched-capacitor PA (tx_am_scpa/scpa.py) --------------------
    # scpa.main() returns two tables: code_sweep, one row per amplitude code, and
    # duty_sweep, one row per drive duty cycle. Columns by name: code_sweep.pout_W ...
    code_sweep, duty_sweep = scpa.main()
    full_code = code_sweep.iloc[-1]             # .iloc[-1] = the last row: code 32
    # Worst gap between simulated and textbook efficiency, as a fraction. Codes 0
    # and 2 are left out: tiny powers, noisy ratios.
    from_code_4 = code_sweep[code_sweep.code >= 4]
    worst_gap = np.max(np.abs(from_code_4.eff_sim - from_code_4.eff_theory))
    check("TX AM", "Pout at full code", f"{1e3 * full_code.pout_W:.2f}", ">= 4.5", full_code.pout_W >= 4.5e-3, "mW")
    check("TX AM", "efficiency vs SCPA theory, worst gap", f"{100 * worst_gap:.1f}", "<= 3", worst_gap <= 0.03, "pts")
    tolerance_at_16 = 0.02  # allowed |eff_sim - eff_theory| at code 16 (half scale), fraction: 0.02 = 2 pts
    code_16 = code_sweep[code_sweep.code == 16].iloc[0]     # the row whose code is 16
    gap_at_16 = abs(code_16.eff_sim - code_16.eff_theory)
    check("TX AM", "efficiency vs theory at code 16/32", f"{100 * gap_at_16:.2f}", f"<= {100 * tolerance_at_16:g}",
          gap_at_16 <= tolerance_at_16, "pts")
    # The duty-sweep rows nearest 1/3 duty, where a pulse has no 3rd harmonic (your
    # thesis's trick), and nearest 1/2, where HD2 vanishes. idxmin() = the row label
    # of the smallest |duty - target|; .loc[label] takes that row.
    at_third = duty_sweep.loc[(duty_sweep.duty - 1 / 3).abs().idxmin()]
    at_half = duty_sweep.loc[(duty_sweep.duty - 1 / 2).abs().idxmin()]
    check("TX AM", "HD3 at 1/3 duty", f"{at_third.HD3_dBc:.1f}", "<= -40", at_third.HD3_dBc <= -40, "dBc")
    check("TX AM", "HD2 at 1/2 duty", f"{at_half.HD2_dBc:.1f}", "<= -40", at_half.HD2_dBc <= -40, "dBc")

    # --- TX PM: the NCO in Verilog (tx_pm_nco/) -----------------------------------
    # run_nco.main() returns: rtl_results = {test name: True/False} for the real RTL,
    # mutant_results = the same for a deliberately broken copy, yosys_cells = Yosys's count.
    rtl_results, mutant_results, yosys_cells = run_nco.main()
    # sum() of True/False counts the Trues: "3/3" means all tests passed.
    check("TX PM", "cocotb tests on RTL", f"{sum(rtl_results.values())}/{len(rtl_results)}", "all pass",
          all(rtl_results.values()))
    # The mutant must FAIL the phase test, so "not mutant_results[...]" must be True.
    mutant_caught = not mutant_results["phase_modulation"]
    check("TX PM", "mutant RTL caught by phase test", str(mutant_caught), "True", mutant_caught)
    check("TX PM", "Yosys synthesis, generic gates", str(yosys_cells), "> 0", bool(yosys_cells), "cells")

    # --- TX PA: the cascode class-AB PA (tx_pa_cascode/pa.py) ---------------------
    # sweep = the power sweep as a table; headline = a dictionary of headline numbers.
    pa_sweep, pa_headline = pa.main()
    check("TX PA", "saturated output power", f"{pa_headline['psat_dBm']:.1f}", ">= 17",
          pa_headline["psat_dBm"] >= 17, "dBm")
    check("TX PA", "peak drain efficiency", f"{100 * pa_headline['eff_peak']:.1f}", ">= 50",
          pa_headline["eff_peak"] >= 0.5, "%")
    eff_at_6dB_backoff = pa.efficiency_at_backoff(pa_sweep, -6)
    # "report" checks always pass (ok=True): they are there to print the number.
    check("TX PA", "drain efficiency at 6 dB back-off", f"{100 * eff_at_6dB_backoff:.1f}", "report", True, "%")
    check("TX PA", "AM-PM at saturation", f"{pa_headline['ampm_peak_deg']:.1f}", "report", True, "deg")
    # The known gap: the stacked device sees more than twice its rated voltage (OPEN).
    check("TX PA", "worst device Vds peak (1.2 V devices)", f"{pa_headline['vds_max']:.2f}", "<= 2.4",
          pa_headline["vds_max"] <= 2.4, "V", open_item=True)

    # --- TX system: 64-QAM through both transmitters (tx_system/polar_tx.py) -------
    # tx_results = the results table, one row per (phase bits, skew) case; papr_dB;
    # average and peak efficiency; class_ab = the class-AB PA's results, same signal.
    tx_results, papr_dB, eff_avg, eff_peak, class_ab = polar_tx.main()
    # The nominal case: the row with 6 phase bits and 0 ns skew ("&" = and, row by row).
    nominal = tx_results[(tx_results.pm_bits == 6) & (tx_results.skew_ns == 0)].iloc[0]
    check("TX system", "EVM, 64-QAM, 6-bit phase", f"{nominal.evm_pct:.2f}", "<= 8", nominal.evm_pct <= 8, "%")
    check("TX system", "ACLR, 64-QAM, 6-bit phase", f"{nominal.aclr_dBc:.1f}", "<= -30", nominal.aclr_dBc <= -30, "dBc")
    # The same with 5 ns between the AM and PM paths: EVM in dB must get worse (rise).
    skewed = tx_results[(tx_results.pm_bits == 6) & (tx_results.skew_ns == 5)].iloc[0]
    check("TX system", "5 ns AM/PM skew degrades EVM", f"{skewed.evm_dB - nominal.evm_dB:+.1f}", "> 0",
          skewed.evm_dB > nominal.evm_dB, "dB")
    check("TX system", f"SCPA average efficiency, {papr_dB:.1f} dB PAPR", f"{100 * eff_avg:.1f}", "report",
          True, "%")
    check("TX system", "class-AB PA average efficiency, same", f"{100 * class_ab['eff_avg']:.1f}", "report",
          True, "%")
    check("TX system", "class-AB PA EVM at P1dB peaks, no DPD", f"{class_ab['evm_pct']:.1f}", "<= 8",
          class_ab["evm_pct"] <= 8, "%", open_item=True)

    # --- RX: the cascode LNA (rx_lna/lna.py) ---------------------------------------
    lna_summary = lna.main()   # a dictionary: lna_summary["S11"], ["S21"], ["NF"], ["S11_no_cascode"]
    check("RX LNA", "S11 at 1 GHz", f"{lna_summary['S11']:.1f}", "<= -10", lna_summary["S11"] <= -10, "dB")
    check("RX LNA", "S21 at 1 GHz", f"{lna_summary['S21']:.1f}", ">= 15", lna_summary["S21"] >= 15, "dB")
    check("RX LNA", "noise figure at 1 GHz (Lg Q = 30)", f"{lna_summary['NF']:.2f}", "<= 2",
          lna_summary["NF"] <= 2, "dB")
    # The mutation check: without the cascode the match MUST break (S11 above -10 dB).
    check("RX LNA", "cascode removed: match breaks (Miller)", f"{lna_summary['S11_no_cascode']:.1f}", "> -10",
          lna_summary["S11_no_cascode"] > -10, "dB")

    # --- The summary table, as markdown, in results/summary.md ---------------------
    lines = ["| Block | Check | Result | Spec | |", "|---|---|---|---|---|"]
    # Each stored check is a tuple of six; unpack it into six names in one go.
    for block, name, value, limit, unit, status in checks:
        lines.append(f"| {block} | {name} | {value} {unit} | {limit} | {status} |")
    with open(os.path.join(ROOT, "results", "summary.md"), "w") as summary_file:
        summary_file.write("\n".join(lines) + "\n")   # "\n".join puts a line break between rows
    # Count the statuses: each check's last element is its status; True counts as 1.
    n_pass = sum(one_check[-1] == "PASS" for one_check in checks)
    n_open = sum(one_check[-1] == "OPEN" for one_check in checks)
    n_fail = sum(one_check[-1] == "FAIL" for one_check in checks)
    print(f"\n{n_pass} PASS, {n_open} OPEN, {n_fail} FAIL in {time.time() - start_time:.0f} s; "
          "table in results/summary.md")
    return n_fail == 0   # True when nothing failed


# This block runs only when the file is started directly (python run_all.py), not
# when another file imports it. sys.exit(0) = success, 1 = failure: GitHub Actions
# reads that exit code to mark the run green or red.
if __name__ == "__main__":
    sys.exit(0 if main() else 1)
