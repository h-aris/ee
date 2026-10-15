import numpy as np
from tools import op

# Hand: KCL at nodes 1 and 2, in volts, kilohms and milliamperes: G @ v = i
G = np.array([[2.0, -1.0],
              [-1.0, 2.0]])
i = np.array([2.0, 3.0])
v = np.linalg.solve(G, i)
print("numpy:  v1 = %.4f V, v2 = %.4f V" % tuple(v))

net = """* D2
I1 0 n1 2m
R1 n1 0 1k
R2 n1 n2 1k
R3 n2 0 2k
R4 n2 n3 2k
V3 n3 0 6"""
s = op(net)
print("ngspice: v1 = %.4f V, v2 = %.4f V" % (s["v(n1)"], s["v(n2)"]))