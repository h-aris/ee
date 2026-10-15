# %% [markdown]
# Scratch space for exploring results, MATLAB style.
#
# In VS Code (with the Python extension) every "# %%" line starts a cell: put
# the cursor in a cell and press Shift+Enter to run just that cell, and the
# variables stay alive in the Interactive window, like MATLAB's workspace.
# Run `python3 run_all.py` once first so results/ is filled.

# %% Load: pandas reads a CSV into a table with named columns (a DataFrame)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

pa = pd.read_csv("results/pa_sweep.csv")
scpa = pd.read_csv("results/scpa_codes.csv").query("code > 0")   # code 0 sends no power
lna = pd.read_csv("results/lna.csv")
print(pa.columns.tolist())
pa.head()

# %% Ask questions of a table: rows where the PA is within 3 dB of its peak
near_peak = pa[pa.backoff_dB > -3]
near_peak[["pout_dBm", "eff", "ampm_deg", "vds2_max"]]

# %% Efficiency against back-off: the two PAs and the two textbook curves
bo = np.linspace(-15, 0, 200)
scpa_bo = 10 * np.log10(scpa.pout_W / scpa.pout_W.max())
fig, ax = plt.subplots()
ax.plot(pa.backoff_dB, 100 * pa.eff, "o-", label="cascode class AB (ngspice)")
ax.plot(scpa_bo, 100 * scpa.eff_sim, "s-", label="SCPA, ideal switches (ngspice)")
ax.plot(bo, 100 * np.pi / 4 * 10**(bo / 20), "--", label="ideal class B")
ax.set(xlim=(-15, 0.5), xlabel="back-off, dB", ylabel="efficiency, %")
ax.grid(alpha=0.3)
ax.legend()

# %% The LNA's match band, read off the table instead of a plot
band = lna[lna.s11 < -10]
print(f"S11 < -10 dB from {band.f.min() / 1e9:.3f} to {band.f.max() / 1e9:.3f} GHz")
