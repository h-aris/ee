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
# This file holds no functions, only constants. A block script does
#   from models import NMOS, PMOS, LMIN, VDD
# and pastes NMOS and PMOS into its netlist text, so every block simulates the same
# transistors. Change a value here and every block changes with it.

LMIN = 100e-9          # channel length used everywhere, m
VDD = 1.2              # core supply, V

# A SPICE ".model" line, built as one Python string. Python joins strings written
# side by side inside parentheses, so the three quoted pieces become one line.
# What the parameters mean (BSIM4 names):
#   level=54 version=4.8.2  BSIM4, the industry-standard MOSFET model family
#   toxe, toxp, toxm        gate-oxide thickness (2.0 nm): sets the gate capacitance
#                           per area, and so how hard the gate pulls the channel
#   vth0                    threshold voltage at zero body bias, V (+0.40 NMOS, -0.40 PMOS)
#   u0                      carrier mobility, m^2/(V s): electrons (0.035) about three
#                           times holes (0.012), which is why PMOS devices are drawn wider
#   vsat                    carrier saturation velocity, m/s: the speed limit that bends
#                           the square law (velocity saturation, L5 D3)
#   rdsw                    source/drain series resistance per width, ohm um
#   pclm                    channel-length modulation: sets the output resistance ro
#   cgso, cgdo, cgbo        gate overlap capacitance per width to source, drain, bulk
#                           (cgdo is the Cgd of the Miller effect)
NMOS = (".model nch nmos level=54 version=4.8.2 toxe=2.0n toxp=1.7n toxm=2.0n "
        "vth0=0.40 u0=0.035 vsat=1.0e5 rdsw=150 pclm=1.0 "
        "cgso=0.3n cgdo=0.3n cgbo=0")
PMOS = (".model pch pmos level=54 version=4.8.2 toxe=2.0n toxp=1.7n toxm=2.0n "
        "vth0=-0.40 u0=0.012 vsat=0.8e5 rdsw=300 pclm=1.0 "
        "cgso=0.3n cgdo=0.3n cgbo=0")
