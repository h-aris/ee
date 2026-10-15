"""Run ngspice in batch mode from Python and read back its results.

Every simulation in this repo goes through run(): write a netlist, call
`ngspice -b`, then load the columns that the netlist's `wrdata` wrote.
No GUI and no PySpice, so the same flow works on Linux, WSL and Windows.
"""
import os
import shutil
import subprocess
import tempfile

import numpy as np


def ngspice_path():
    exe = shutil.which("ngspice") or shutil.which("ngspice_con")
    if exe is None:
        raise RuntimeError("ngspice not found on PATH; see README, Setup")
    return exe


DECKS = os.path.join(os.path.dirname(__file__), "..", "results", "decks")


def run(netlist, outputs, workdir=None, timeout=600, keep=None):
    """Simulate `netlist` (a string) and return {name: 2-D array}.

    `outputs` lists the file names the netlist writes with `wrdata`.
    The netlist may use the placeholder {dir} for the output folder.
    keep="name" saves the deck and its log in results/decks/name/, so it can be
    opened in interactive ngspice afterwards; otherwise a temporary folder is used.
    """
    if keep:
        workdir = os.path.join(DECKS, keep)
    workdir = os.path.abspath(workdir or tempfile.mkdtemp(prefix="spice_"))
    os.makedirs(workdir, exist_ok=True)
    deck = os.path.join(workdir, "deck.cir")
    with open(deck, "w") as f:
        f.write(netlist.replace("{dir}", workdir.replace("\\", "/")))
    proc = subprocess.run([ngspice_path(), "-b", deck], capture_output=True,
                          text=True, timeout=timeout, cwd=workdir)
    log = proc.stdout + proc.stderr
    with open(os.path.join(workdir, "ngspice.log"), "w") as f:
        f.write(log)
    if proc.returncode != 0:
        raise RuntimeError(f"ngspice failed, see {workdir}/ngspice.log")
    data = {}
    for name in outputs:
        path = os.path.join(workdir, name)
        if not os.path.exists(path):
            raise RuntimeError(f"ngspice wrote no {name}; see {workdir}/ngspice.log")
        data[name] = np.loadtxt(path)
    return data


def fourier(t, v, f0, n_harm=5, cycles=10):
    """Complex amplitudes of harmonics 1..n_harm over the last `cycles` periods.

    Resamples onto a uniform grid first, because ngspice's time step varies.
    Returns peak-amplitude phasors (size = peak volts, angle = phase in rad).
    """
    T = cycles / f0
    tu = np.linspace(t[-1] - T, t[-1], 64 * cycles * n_harm, endpoint=False)
    vu = np.interp(tu, t, v)
    k = np.arange(1, n_harm + 1)
    basis = np.exp(-2j * np.pi * np.outer(k, tu) * f0)
    return 2 * (basis @ vu) / len(tu)
