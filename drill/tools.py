"""Two helpers for the drill: run ngspice on a netlist string, read results back."""
import os
import subprocess
import tempfile

import numpy as np


def ngspice(netlist):
    """Run a netlist in batch mode in a fresh folder; return that folder's path."""
    d = tempfile.mkdtemp(prefix="drill_")
    with open(os.path.join(d, "deck.cir"), "w") as f:
        f.write(netlist.replace("{dir}", d))
    p = subprocess.run(["ngspice", "-b", "deck.cir"], cwd=d, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stdout + p.stderr)
    return d


def op(netlist):
    """Operating point: every node voltage and source current, as a dict."""
    deck = netlist + "\n.control\nop\nprint all > {dir}/op.txt\n.endc\n.end\n"
    d = ngspice(deck)
    out = {}
    for line in open(os.path.join(d, "op.txt")):
        if "=" in line:
            k, v = (x.strip() for x in line.split("="))
            # ngspice prints node "out" and source current "v1#branch"
            key = f"i({k[:-7]})" if k.endswith("#branch") else f"v({k})"
            out[key] = float(v)
    return out


def ac(netlist, start, stop, points, *nodes):
    """AC sweep; returns frequency and one complex array per node voltage."""
    vecs = " ".join(f"v({n})" for n in nodes)
    sweep = f"lin 1 {start} {start}" if start == stop else f"dec {points} {start} {stop}"
    deck = (netlist + f"\n.control\nac {sweep}\n"
            f"wrdata {{dir}}/ac.txt {vecs}\n.endc\n.end\n")
    d = ngspice(deck)
    a = np.loadtxt(os.path.join(d, "ac.txt"), ndmin=2)
    f = a[:, 0]
    return f, [a[:, 3 * i + 1] + 1j * a[:, 3 * i + 2] for i in range(len(nodes))]