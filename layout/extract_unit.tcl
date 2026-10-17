# extract_unit.tcl: turn the layout back into netlists.
#   scpa_unit_lvs.spice : devices and connections only, for LVS against ref.spice
#   scpa_unit_pex.spice : the same plus every parasitic capacitance Magic finds
#                         (PEX, parasitic extraction), for post-layout simulation
# Run like build_unit.tcl, after it.

gds readonly true
gds read /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/gds/sg13g2_stdcell.gds
load scpa_unit

# extract all: Magic recognises devices from layer overlaps (Poly over Activ = transistor,
# Metal5 under the MIM layer = capacitor) and traces which shapes touch (the nets).
# It also computes the capacitance between overlapping and neighbouring shapes.
extract all

# lvs: names and format that Netgen expects. No parasitics.
ext2spice lvs
ext2spice -o scpa_unit_lvs.spice

# cthresh 0: keep every parasitic capacitor, however small (the default drops tiny ones).
ext2spice lvs
ext2spice cthresh 0
ext2spice -o scpa_unit_pex.spice
quit -noprompt
