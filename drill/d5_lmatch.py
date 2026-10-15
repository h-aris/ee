import numpy as np
from tools import ac

f0, rs, rl = 1e9, 50.0, 200.0
q = np.sqrt(rl / rs - 1)                 # the L-match's Q is fixed by the ratio
L = q * rs / (2 * np.pi * f0)            # series reactance Q * Rlow
C = q / rl / (2 * np.pi * f0)            # shunt susceptance Q / Rhigh
print(f"Q = {q:.3f}, L = {L*1e9:.2f} nH, C = {C*1e12:.3f} pF")

f, (va,) = ac(f"""* D5
V1 src 0 DC 0 AC 1
Rs src a {rs}
L1 a b {L}
C1 b 0 {C}
RL b 0 {rl}""", 1e8, 1e10, 400, "a")
zin = va / ((1 - va) / rs)               # current through Rs is (1 - v(a)) / Rs
s11 = 20 * np.log10(abs((zin - rs) / (zin + rs)))
k = np.argmin(abs(f - f0))
band = f[s11 < -10]
print(f"Zin(1 GHz) = {zin[k].real:.2f} {zin[k].imag:+.2f}j ohm, S11 = {s11[k]:.1f} dB")
print(f"S11 < -10 dB from {band.min()/1e9:.3f} to {band.max()/1e9:.3f} GHz")