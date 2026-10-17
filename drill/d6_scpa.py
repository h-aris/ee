import sys
sys.path.insert(0, "../tx_am_scpa")
sys.path.insert(0, "..")
import scpa

# A different SCPA: 64 units, Q = 5, 1.2 V switches
scpa.N, scpa.Q, scpa.VDD = 64, 5.0, 1.2
scpa.CTOT = 1 / (scpa.W0 * scpa.RL * scpa.Q)
scpa.LSER = 1 / (scpa.W0**2 * scpa.CTOT)
for n in (64, 16):
    h, pout, psup = scpa.simulate(n)
    print(f"n = {n}: Pout = {pout*1e3:.3f} mW, efficiency = {100*pout/psup:.1f} %, "
          f"theory {100*scpa.theory_efficiency(n):.1f} %")