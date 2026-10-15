import numpy as np
from tools import ac

f, (vout,) = ac("* D4\nV1 in 0 DC 0 AC 1\nR1 in out 50\nC1 out 0 3.18p", 1e8, 1e10, 50, "out")
k = np.argmin(abs(f - 1e9))
print(f"at {f[k]/1e9:.3f} GHz: |H| = {abs(vout[k]):.3f}, angle = {np.degrees(np.angle(vout[k])):.1f} deg")