"""Transistor models shared by every CMOS block.

A generic BSIM4 card, not a foundry model: oxide, threshold, mobility and
overlap capacitance are set to typical values for a 1.2 V, 100 nm-class
process and everything else is left at the BSIM4 defaults. It gives the right
kind of behaviour (square law bending into velocity saturation, gate and
overlap capacitance, channel thermal noise) with roughly right numbers: at
L = 100 nm the NMOS reaches fT of about 60 GHz near 20 uA/um.

This is the "generic real" rung of the ladder in the README. The next rung
swaps these lines for a foundry PDK (IHP SG13G2 through IIC-OSIC-TOOLS).
"""

LMIN = 100e-9          # channel length used everywhere, m
VDD = 1.2              # core supply, V

NMOS = (".model nch nmos level=54 version=4.8.2 toxe=2.0n toxp=1.7n toxm=2.0n "
        "vth0=0.40 u0=0.035 vsat=1.0e5 rdsw=150 pclm=1.0 "
        "cgso=0.3n cgdo=0.3n cgbo=0")
PMOS = (".model pch pmos level=54 version=4.8.2 toxe=2.0n toxp=1.7n toxm=2.0n "
        "vth0=-0.40 u0=0.012 vsat=0.8e5 rdsw=300 pclm=1.0 "
        "cgso=0.3n cgdo=0.3n cgbo=0")
