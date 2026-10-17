"""TX system: a polar 64-QAM transmitter built from the two simulated paths.

AM path: the SCPA's amplitude codes, using the AM-AM and AM-PM curves that
ngspice produced (results/scpa_codes.csv). PM path: the NCO's P-bit phase word
(tx_pm_nco). Python recombines them and measures what a transmitter is judged
on: EVM, ACLR and the average efficiency at the signal's back-off.

Also sweeps the AM-to-PM timing skew. In a polar TX the two paths travel
through different circuits, and a delay between them shows up as spectral
regrowth and EVM; aligning them is part of every polar bring-up.

Run:  python tx_system/polar_tx.py   (needs results/scpa_codes.csv first;
      shows the summary figure, then prints the results table)
"""
# ---------------------------------------------------------------------------------
# No circuit simulation in this file: it is the "MATLAB part" of the testbench.
# It builds a real 64-QAM signal in NumPy (as in your ELCA DPD work), passes it
# through models of the two paths that ngspice measured, and computes EVM and ACLR
# the way a signal analyser does. Signals are complex baseband: one complex number
# per sample, magnitude = envelope (amplitude path), angle = phase (phase path).
#
# How the file is laid out:
#   imports and constants
#   functions (the tools): rrc_filter, qam64_symbols, load_scpa_curves, transmit,
#       measure_evm, measure_aclr, then main(), then class_ab_comparison and
#       save_summary_figure
#   main(): uses the tools, step by step; ends with a commented plot template,
#       where every variable of main() is still alive, then shows the summary figure.
#   the last lines: run only when you start this file yourself (not from run_all).
# ---------------------------------------------------------------------------------
import os

import matplotlib.pyplot as plt   # plotting, MATLAB style: plt.plot, plt.title ...
import numpy as np                # arrays and maths: np.abs, np.exp, np.log10 ...
import pandas as pd               # tables with named columns, like a MATLAB table
from scipy import signal          # signal processing; here welch() for the spectrum

# Where the results live: the folder "results", one level up from this file.
RESULTS_FOLDER = os.path.join(os.path.dirname(__file__), "..", "results")

SYMBOL_RATE_HZ = 5e6                                  # 5 Msymbol/s: 200 ns per symbol
SAMPLES_PER_SYMBOL = 32
SAMPLE_RATE_HZ = SYMBOL_RATE_HZ * SAMPLES_PER_SYMBOL  # 160 MHz, the digital front end's rate
RRC_ROLLOFF = 0.25                                    # root-raised-cosine roll-off (alpha)
N_SYMBOLS = 4096
EVM_LIMIT = 0.08                                      # 8 %: LTE requirement for 64-QAM
ACLR_LIMIT_DBC = -30                                  # adjacent channel limit, dBc


def rrc_filter(rolloff=RRC_ROLLOFF, span_symbols=12, samples_per_symbol=SAMPLES_PER_SYMBOL):
    # The root-raised-cosine pulse: the standard shaping filter that keeps the
    # spectrum inside SYMBOL_RATE * (1 + rolloff) and, used again at the receiver
    # (matched filter), gives zero interference between symbols.
    # The arguments have defaults (the "=" values), so rrc_filter() with nothing in
    # the brackets uses them; rrc_filter(rolloff=0.35) changes only that one.
    half_span = span_symbols * samples_per_symbol // 2   # "//" divides and drops the fraction
    time_in_symbols = np.arange(-half_span, half_span + 1) / samples_per_symbol
    taps = np.zeros_like(time_in_symbols)                # zeros, same size as time_in_symbols
    # enumerate() hands out each element with its index: i = 0, 1, 2 ... and t = time_in_symbols[i].
    for i, t in enumerate(time_in_symbols):
        # The textbook formula has 0/0 at two points; those get their limit values.
        if abs(t) < 1e-9:
            taps[i] = 1 - rolloff + 4 * rolloff / np.pi
        elif abs(abs(4 * rolloff * t) - 1) < 1e-9:
            taps[i] = rolloff / np.sqrt(2) * ((1 + 2 / np.pi) * np.sin(np.pi / (4 * rolloff))
                                              + (1 - 2 / np.pi) * np.cos(np.pi / (4 * rolloff)))
        else:
            taps[i] = (np.sin(np.pi * t * (1 - rolloff)) + 4 * rolloff * t * np.cos(np.pi * t * (1 + rolloff))) \
                / (np.pi * t * (1 - (4 * rolloff * t)**2))
    return taps / np.sqrt(np.sum(taps**2))     # scaled to unit energy


def qam64_symbols(n_symbols, random_generator):
    # 64-QAM: I and Q each take one of 8 levels -7, -5, ..., 7 (np.arange steps by 2).
    # random_generator.choice picks n_symbols random levels; dividing by sqrt(42)
    # makes the average power 1.
    levels = np.arange(-7, 8, 2)
    i_part = random_generator.choice(levels, n_symbols)
    q_part = random_generator.choice(levels, n_symbols)
    return (i_part + 1j * q_part) / np.sqrt(42)    # 1j is Python's imaginary unit (MATLAB: 1i)


def load_scpa_curves():
    # Read the SCPA sweep that scpa.py saved: one row per even code 0, 2, ..., 32,
    # with the output amplitude (AM-AM) and phase (AM-PM) at each.
    scpa_table = pd.read_csv(os.path.join(RESULTS_FOLDER, "scpa_codes.csv"))
    # Every code 0..32, odd ones included, filled in by interpolation.
    all_codes = np.arange(0, scpa_table.code.max() + 1)
    amplitude_per_code = np.interp(all_codes, scpa_table.code, scpa_table.vout_peak_V)
    # np.unwrap removes jumps of 2 pi in the phase before interpolating.
    phase_rad = np.unwrap(np.radians(scpa_table.vout_phase_deg))
    ampm_per_code = np.interp(all_codes, scpa_table.code, phase_rad)
    ampm_per_code = ampm_per_code - ampm_per_code[-1]   # AM-PM relative to full code ([-1] = last)
    return all_codes, amplitude_per_code, ampm_per_code, scpa_table


def transmit(ideal_signal, all_codes, amplitude_per_code, ampm_per_code, pm_bits, skew_s=0.0):
    """Polar TX: round |signal| to an SCPA code and angle(signal) to a pm_bits word."""
    top_code = all_codes[-1]                        # 32
    envelope = np.abs(ideal_signal)                 # the AM path's input
    if skew_s:                                      # AM path arrives late by skew_s
        time_s = np.arange(len(envelope)) / SAMPLE_RATE_HZ
        envelope = np.interp(time_s - skew_s, time_s, envelope)   # read skew_s earlier = delay
    # Amplitude: scale to 0..32, round to whole codes, keep in range, make integers.
    code_per_sample = np.clip(np.round(envelope / envelope.max() * top_code), 0, top_code).astype(int)
    # Phase: 2^pm_bits steps per turn, the NCO's phase word. ** is MATLAB's ^.
    steps_per_turn = 2**pm_bits
    phase_rad = np.round(np.angle(ideal_signal) / (2 * np.pi) * steps_per_turn) * 2 * np.pi / steps_per_turn
    # Recombine: the amplitude the SCPA really gives for that code, and the phase
    # plus the SCPA's own phase shift at that code (its AM-PM).
    # amplitude_per_code[code_per_sample] looks up one value per sample (MATLAB: same).
    tx_output = amplitude_per_code[code_per_sample] * np.exp(1j * (phase_rad + ampm_per_code[code_per_sample]))
    return tx_output, code_per_sample


def measure_evm(measured_signal, reference_signal, matched_filter):
    """EVM after the matched filter, at the symbol instants, gain and rotation fitted.
    Returns the EVM as a fraction (0.0066 = 0.66 %) and the constellation points."""
    # Filter both signals with the same RRC, then keep one sample per symbol, as a
    # receiver would. [start::step] = from index start, every step-th sample
    # (MATLAB: x(start+1:step:end)); [:N_SYMBOLS] = the first N_SYMBOLS of those.
    first = len(matched_filter) - 1
    measured_symbols = np.convolve(measured_signal, matched_filter)[first::SAMPLES_PER_SYMBOL][:N_SYMBOLS]
    reference_symbols = np.convolve(reference_signal, matched_filter)[first::SAMPLES_PER_SYMBOL][:N_SYMBOLS]
    # Skip 20 symbols at each end, where the filter is still filling up.
    measured_symbols = measured_symbols[20:N_SYMBOLS - 20]
    reference_symbols = reference_symbols[20:N_SYMBOLS - 20]
    # The complex gain (amplitude and rotation) that best maps the reference onto the
    # measured symbols, a least-squares fit, as a signal analyser normalises before EVM.
    # np.vdot(a, b) = sum(conj(a) * b).
    gain = np.vdot(reference_symbols, measured_symbols) / np.vdot(reference_symbols, reference_symbols)
    error_vectors = measured_symbols - gain * reference_symbols
    evm = np.sqrt(np.mean(np.abs(error_vectors)**2) / np.mean(np.abs(gain * reference_symbols)**2))
    constellation = measured_symbols / gain          # the dots you would plot, gain removed
    return evm, constellation


def measure_aclr(measured_signal):
    """ACLR in dBc (the worse of the two adjacent channels), plus the spectrum."""
    # Power spectral density by Welch's method (an average of many FFTs), both sides.
    freqs_Hz, psd = signal.welch(measured_signal, fs=SAMPLE_RATE_HZ, nperseg=4096,
                                 return_onesided=False, detrend=False)
    channel_bw_Hz = SYMBOL_RATE_HZ * (1 + RRC_ROLLOFF)            # occupied bandwidth
    # psd[condition] keeps only the values where the condition is True (MATLAB: same).
    main_channel_power = np.sum(psd[np.abs(freqs_Hz) <= channel_bw_Hz / 2])
    lower_channel_power = np.sum(psd[np.abs(freqs_Hz + channel_bw_Hz) <= channel_bw_Hz / 2])
    upper_channel_power = np.sum(psd[np.abs(freqs_Hz - channel_bw_Hz) <= channel_bw_Hz / 2])
    worse_adjacent = max(lower_channel_power, upper_channel_power)
    aclr_dBc = 10 * np.log10(worse_adjacent / main_channel_power)
    return aclr_dBc, freqs_Hz, psd


def main(show_plots=False):
    # show_plots: False when run_all.py calls main(); True when you run this file.

    # --- 1. The ideal signal ------------------------------------------------------
    random_generator = np.random.default_rng(7)     # seeded: the same symbols every run
    all_codes, amplitude_per_code, ampm_per_code, scpa_table = load_scpa_curves()
    rrc_taps = rrc_filter()
    symbols = qam64_symbols(N_SYMBOLS, random_generator)
    # Upsample: SAMPLES_PER_SYMBOL samples per symbol, the symbol in the first, zeros elsewhere ...
    impulses = np.zeros(N_SYMBOLS * SAMPLES_PER_SYMBOL, complex)
    impulses[::SAMPLES_PER_SYMBOL] = symbols          # MATLAB: impulses(1:32:end) = symbols
    # ... then the pulse-shaping filter turns the impulses into a smooth signal.
    ideal_signal = np.convolve(impulses, rrc_taps)
    papr_dB = 10 * np.log10(np.max(np.abs(ideal_signal)**2) / np.mean(np.abs(ideal_signal)**2))

    # --- 2. Every case: phase bits 6, 8, 10, each with skew 0, 1, 2, 5 ns ------------
    results_by_case = []      # a list, one entry per case; becomes the results table below
    spectra_by_case = {}      # a dictionary: case -> its constellation and spectrum, for plots
    for pm_bits in (6, 8, 10):
        for skew_ns in (0, 1, 2, 5):
            tx_output, code_per_sample = transmit(ideal_signal, all_codes, amplitude_per_code,
                                                  ampm_per_code, pm_bits, skew_ns * 1e-9)
            evm, constellation = measure_evm(tx_output, ideal_signal, rrc_taps)
            aclr_dBc, freqs_Hz, psd = measure_aclr(tx_output)
            # One entry: a dictionary, column name -> value.
            results_by_case.append(dict(pm_bits=pm_bits, skew_ns=skew_ns, evm_pct=100 * evm,
                                        evm_dB=20 * np.log10(evm), aclr_dBc=aclr_dBc))
            # Stored under the key (pm_bits, skew_ns), e.g. spectra_by_case[(6, 0)].
            spectra_by_case[(pm_bits, skew_ns)] = dict(constellation=constellation,
                                                       freqs_Hz=freqs_Hz, psd=psd)
    # The list of dictionaries becomes a table: 12 rows (cases), 5 named columns.
    results = pd.DataFrame(results_by_case)

    # --- 3. Average efficiency at this signal's back-off ---------------------------
    # The nominal case again (6-bit phase, no skew), kept by name for the plots below.
    tx_output_6bit, code_per_sample_6bit = transmit(ideal_signal, all_codes, amplitude_per_code,
                                                    ampm_per_code, 6)
    # The SCPA's output and supply power at each sample's code, then averaged.
    pout_per_sample_W = np.interp(code_per_sample_6bit, scpa_table.code, scpa_table.pout_W)
    psupply_per_sample_W = np.interp(code_per_sample_6bit, scpa_table.code, scpa_table.psupply_W)
    eff_avg = pout_per_sample_W.mean() / psupply_per_sample_W.mean()
    full_code = scpa_table.iloc[-1]                   # .iloc[-1] = the last row: code 32
    eff_peak = full_code.pout_W / full_code.psupply_W

    # --- 4. The same signal through the cascode class-AB PA, for comparison --------
    class_ab = class_ab_comparison(ideal_signal, rrc_taps)

    # --- 5. Save ---------------------------------------------------------------
    # float_format "%.18e": every digit kept, so the file holds exactly what was computed.
    results.to_csv(os.path.join(RESULTS_FOLDER, "polar_tx.csv"), index=False, float_format="%.18e")
    save_summary_figure(results, spectra_by_case, papr_dB)

    # --- 6. Your own plots: every variable above is available here --------------------
    # To add a plot: select the five lines below, press Ctrl+/ in VS Code to remove
    # the "# ", and put in real names, for example var_x -> results_8bit.skew_ns,
    # var_y -> results_8bit.aclr_dBc
    # with this line above them to pick the 8-bit rows:
    # results_8bit = results[results.pm_bits == 8]
    # plt.figure()
    # plt.plot(var_x, var_y, "o-")
    # plt.xlabel("x axis label")
    # plt.ylabel("y axis label")
    # plt.title("title")

    # --- 7. Show the figures, or close them -------------------------------------
    if show_plots:
        plt.show()            # opens the summary figure and yours; the script continues when you close them
    else:
        plt.close("all")      # run_all.py and GitHub: nothing to show, so free the figures

    return results, papr_dB, eff_avg, eff_peak, class_ab


def class_ab_comparison(ideal_signal, rrc_taps):
    """The same signal through the cascode class-AB PA's measured AM-AM and AM-PM."""
    path = os.path.join(RESULTS_FOLDER, "pa_sweep.csv")
    if not os.path.exists(path):
        return None                     # pa.py has not run yet
    pa_sweep = pd.read_csv(path).sort_values("amp_in")       # sorted by drive level
    small_signal_gain_dB = pa_sweep.gain_dB.iloc[0]          # .iloc[0] = first row
    # The drive at 1 dB compression: the first row whose gain has dropped 1 dB.
    compressed = pa_sweep[pa_sweep.gain_dB <= small_signal_gain_dB - 1]
    drive_at_p1db = float(compressed.amp_in.iloc[0])
    # The envelope as a drive amplitude, its peaks placed at P1dB.
    drive = np.abs(ideal_signal) / np.abs(ideal_signal).max() * drive_at_p1db
    # The PA's measured AM-AM and AM-PM, looked up at each sample's drive level.
    output_amplitude = np.interp(drive, pa_sweep.amp_in, pa_sweep.vout_pk, left=0)
    output_phase_shift = np.radians(np.interp(drive, pa_sweep.amp_in, pa_sweep.ampm_deg))
    pa_output = output_amplitude * np.exp(1j * (np.angle(ideal_signal) + output_phase_shift))
    evm, constellation = measure_evm(pa_output, ideal_signal, rrc_taps)
    aclr_dBc, freqs_Hz, psd = measure_aclr(pa_output)
    pout_per_sample_W = np.interp(drive, pa_sweep.amp_in, pa_sweep.pout_W, left=0)
    pdc_per_sample_W = np.interp(drive, pa_sweep.amp_in, pa_sweep.pdc_W)
    return dict(evm_pct=100 * evm, aclr_dBc=aclr_dBc,
                eff_avg=pout_per_sample_W.mean() / pdc_per_sample_W.mean())


def save_summary_figure(results, spectra_by_case, papr_dB):
    # The three-panel figure saved as results/polar_tx.png (the README shows it).
    # subplots(1, 3) makes one figure with three plots side by side; panel[0],
    # panel[1], panel[2] are the three (MATLAB: subplot(1,3,k)).
    fig, panel = plt.subplots(1, 3, figsize=(15, 4.4))

    nominal = spectra_by_case[(6, 0)]
    panel[0].plot(nominal["constellation"].real, nominal["constellation"].imag, ".", ms=2)
    panel[0].set(title="64-QAM after the polar TX (6-bit phase, 5-bit amplitude)",
                 xlabel="I", ylabel="Q", aspect="equal")

    for skew_ns in (0, 5):
        case = spectra_by_case[(6, skew_ns)]
        order = np.argsort(case["freqs_Hz"])      # sort by frequency so the line is drawn in order
        panel[1].plot(case["freqs_Hz"][order] / 1e6, 10 * np.log10(case["psd"][order] / case["psd"].max()),
                      lw=0.8, label=f"skew {skew_ns} ns")
    channel_bw_MHz = SYMBOL_RATE_HZ * (1 + RRC_ROLLOFF) / 1e6
    for edge in (-1.5, -0.5, 0.5, 1.5):
        panel[1].axvline(edge * channel_bw_MHz, color="0.6", lw=0.6)    # channel edges
    panel[1].set(xlim=(-20, 20), ylim=(-80, 5), xlabel="offset from carrier, MHz",
                 ylabel="PSD, dB", title="Spectrum: AM/PM skew regrows the skirts")
    panel[1].legend()

    for pm_bits in (6, 8, 10):
        cases = results[results.pm_bits == pm_bits]
        panel[2].plot(cases.skew_ns, cases.evm_dB, "o-", label=f"{pm_bits}-bit phase")
    panel[2].axhline(20 * np.log10(EVM_LIMIT), color="r", lw=0.8, label="8 % limit")
    panel[2].set(xlabel="AM-to-PM skew, ns", ylabel="EVM, dB", title=f"EVM vs skew (PAPR {papr_dB:.1f} dB)")
    panel[2].legend()

    for one_panel in panel:
        one_panel.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_FOLDER, "polar_tx.png"), dpi=130)
    # The figure stays open: main() shows it (show_plots=True) or closes it.


# These lines run only when you start this file yourself (python tx_system/polar_tx.py).
# When run_all.py imports the file, Python skips them and run_all calls main() itself.
if __name__ == "__main__":
    # main() returns five things; five names catch them (MATLAB: [a, b, ...] = main()).
    results, papr_dB, eff_avg, eff_peak, class_ab = main(show_plots=True)
    print(f"cascode class-AB PA, same signal: EVM {class_ab['evm_pct']:.1f} %, "
          f"ACLR {class_ab['aclr_dBc']:.1f} dBc, average efficiency {100 * class_ab['eff_avg']:.1f} %")
    print(f"PAPR {papr_dB:.1f} dB, efficiency peak {100 * eff_peak:.1f} %, "
          f"average at this back-off {100 * eff_avg:.1f} %")
    print(results.round(2).to_string(index=False))     # the table, 2 decimals, no row numbers
