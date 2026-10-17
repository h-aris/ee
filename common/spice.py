"""Run ngspice in batch mode from Python and read back its results.

Every simulation in this repo goes through run(): write a netlist, call
`ngspice -b`, then load the columns that the netlist's `wrdata` wrote.
No GUI and no PySpice, so the same flow works on Linux, WSL and Windows.
"""
# ---------------------------------------------------------------------------------
# How to read this file (for a MATLAB user)
#
# A Python file is a "module": other files load it with `import` and then call its
# functions as spice.run(...), spice.fourier(...), the way MATLAB calls a function
# file. Nothing runs when it is imported except the lines at the left margin
# (imports, the DECKS constant, and the `def` lines that define functions).
#
# The whole idea of the repo's simulation flow is in run():
#   1. a block script (scpa.py, lna.py, ...) builds a netlist as a text string,
#   2. run() writes that string to a file deck.cir,
#   3. run() starts ngspice in batch mode (-b: no prompt, run the deck, exit),
#   4. the deck's .control block writes columns of numbers with `wrdata`,
#   5. run() reads those text files into NumPy arrays and returns them.
# So ngspice is used exactly like a command you would type in the terminal, and
# Python only writes text and reads numbers. That is the "programmatic EDA / CLI"
# skill in one function.
# ---------------------------------------------------------------------------------

# Standard-library modules (they come with Python, no install needed):
import os          # paths and folders: os.path.join glues folder names with "/"
import shutil      # shutil.which("x") finds program x on the PATH, like `which x`
import subprocess  # starts other programs (here ngspice) and collects their output
import tempfile    # makes a fresh, uniquely named temporary folder

# Installed with pip (requirements.txt): numerical arrays, MATLAB's matrices.
# "as np" is a nickname, so np.loadtxt means numpy.loadtxt.
import numpy as np


def ngspice_path():
    # Find the ngspice program. `or` returns the first answer that is not None,
    # so on Windows the console build "ngspice_con" is tried when "ngspice" is missing.
    program = shutil.which("ngspice") or shutil.which("ngspice_con")
    if program is None:
        # raise stops the program with this message, like MATLAB's error().
        raise RuntimeError("ngspice not found on PATH; see README, Setup")
    return program


# Folder where decks are kept when a block asks to keep one (keep="name" below).
# __file__ is this file's own path; ".." goes one folder up, from common/ to the repo.
DECKS = os.path.join(os.path.dirname(__file__), "..", "results", "decks")


# A function definition. Arguments with "=" have default values, so a call may
# leave them out: run(net, ["out.txt"]) uses workdir=None, timeout=600, keep=None.
# Callers can also name them in any order: run(net, files, keep="scpa").
def run(netlist, outputs, workdir=None, timeout=600, keep=None):
    """Simulate `netlist` (a string) and return {name: 2-D array}.

    `outputs` lists the file names the netlist writes with `wrdata`.
    The netlist may use the placeholder {dir} for the output folder.
    keep="name" saves the deck and its log in results/decks/name/, so it can be
    opened in interactive ngspice afterwards; otherwise a temporary folder is used.
    """
    # Choose the folder ngspice works in: a named, kept folder, or a throwaway one.
    if keep:
        workdir = os.path.join(DECKS, keep)
    # `workdir or tempfile.mkdtemp(...)`: use workdir if given, else make a temp folder.
    workdir = os.path.abspath(workdir or tempfile.mkdtemp(prefix="spice_"))
    os.makedirs(workdir, exist_ok=True)   # create it; no error if it already exists
    deck_path = os.path.join(workdir, "deck.cir")
    # `with open(...) as deck_file:` opens a file and closes it automatically at the
    # end of the indented block. "w" = write (overwrite).
    with open(deck_path, "w") as deck_file:
        # The netlist text contains the placeholder {dir} where wrdata should write;
        # replace it with the real folder. Backslashes become "/" for Windows paths.
        deck_file.write(netlist.replace("{dir}", workdir.replace("\\", "/")))
    # Start ngspice: the list is the command line, word by word: ngspice -b deck.cir.
    # capture_output=True keeps what ngspice prints instead of showing it;
    # text=True gives it as text; timeout stops a run that hangs; cwd = run inside workdir.
    finished = subprocess.run([ngspice_path(), "-b", deck_path], capture_output=True,
                          text=True, timeout=timeout, cwd=workdir)
    # Save everything ngspice printed (normal output + errors) next to the deck.
    printed = finished.stdout + finished.stderr
    with open(os.path.join(workdir, "ngspice.log"), "w") as log_file:
        log_file.write(printed)
    # A program that fails returns a non-zero exit code; stop with a pointer to the log.
    if finished.returncode != 0:
        # f"...{workdir}..." is an f-string: the braces are replaced by the value.
        raise RuntimeError(f"ngspice failed, see {workdir}/ngspice.log")
    # Read each output file into a NumPy array and collect them in a dictionary:
    # tables["out.txt"] -> the table of numbers (rows = time or frequency points,
    # columns = what wrdata wrote: x, y, x, y, ...).
    tables = {}
    for name in outputs:
        path = os.path.join(workdir, name)
        if not os.path.exists(path):
            raise RuntimeError(f"ngspice wrote no {name}; see {workdir}/ngspice.log")
        tables[name] = np.loadtxt(path)   # like MATLAB's load() of a text table
    return tables


def fourier(time_s, values, f0, n_harm=5, cycles=10):
    """Complex amplitudes of harmonics 1..n_harm over the last `cycles` periods.

    Resamples onto a uniform grid first, because ngspice's time step varies.
    Returns peak-amplitude phasors (size = peak volts, angle = phase in rad).
    """
    # Why: the PA scripts need the size and phase of the 1st, 2nd, 3rd ... harmonic
    # of a waveform (output power, HD2, HD3, AM-PM). That is one Fourier-series
    # coefficient per harmonic, computed over whole periods at the end of the run,
    # after the start-up transient has died away.
    span_s = cycles / f0                  # length of the analysed stretch, s
    # ngspice takes small steps where the signal changes fast and big ones elsewhere,
    # so first resample onto evenly spaced times (64 points per period per harmonic).
    even_time_s = np.linspace(time_s[-1] - span_s, time_s[-1], 64 * cycles * n_harm, endpoint=False)
    even_values = np.interp(even_time_s, time_s, values)   # linear interpolation, MATLAB's interp1
    harmonic_numbers = np.arange(1, n_harm + 1)            # 1, 2, ..., n_harm
    # basis[k, n] = exp(-j 2 pi k f0 t_n): one row per harmonic (np.outer makes the
    # harmonic-by-time grid of k*t). Multiplying it by the samples (@ is matrix product)
    # sums v(t) e^{-j k w0 t} over time: the Fourier integral as a sum.
    basis = np.exp(-2j * np.pi * np.outer(harmonic_numbers, even_time_s) * f0)
    # Divide by the number of samples for the average, times 2 for a peak amplitude
    # (a cosine of peak A has coefficient A/2 at +f0 and A/2 at -f0).
    return 2 * (basis @ even_values) / len(even_time_s)
