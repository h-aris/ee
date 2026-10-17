# build_unit.tcl: draw the SCPA unit cell in Magic, check it (DRC) and save it.
#
# What the cell is: one unit of a switched-capacitor PA (SCPA). An inverter switches
# the bottom plate of a MIM capacitor between 0 V and VDD; many such units in parallel,
# their top plates tied together, make the PA's output. The digital code says how many
# units switch, and that count sets the output amplitude (L7 7.4).
#   inverter : IHP standard cell sg13g2_inv_4 (4 gate fingers, 2.88 x 3.78 um), taken
#              ready-made from the IHP library, the way a real SCPA reuses digital cells.
#   capacitor: cap_cmim, IHP's metal-insulator-metal cap between Metal5 (bottom plate)
#              and TopMetal1 (top plate), 5 um x 5 um, about 37 fF (estimated).
#
# Run (inside the IIC-OSIC-TOOLS image, or through run_flow.sh from Ubuntu):
#   magic -dnull -noconsole -rcfile $PDK_ROOT/$PDK/libs.tech/magic/ihp-sg13g2.magicrc build_unit.tcl
#   -dnull: no graphics window;  -noconsole: no Tcl prompt;  -rcfile: load the IHP technology.
# Units: "um" after a number means micrometres; without it Magic uses its own grid.

# --- 1. The inverter, read from IHP's standard-cell GDS file -------------------------
# readonly: Magic keeps the cell exactly as IHP drew it and never rewrites it.
gds readonly true
gds read /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/gds/sg13g2_stdcell.gds

# Open (create) our own top cell. Everything we paint from here on goes into it.
load scpa_unit

# getcell places a copy (an instance) of a cell where the box is; identify names it.
box 0um 0um 0um 0um
getcell sg13g2_inv_4
identify XINV

# --- 2. The MIM capacitor, made by IHP's device generator ----------------------------
# gencell draws a device from parameters (w, l), the same as the Devices menu in the GUI.
# It is placed at the box: lower-left corner at x = 6 um, clear of the inverter.
box 6um 0um 6um 0um
magic::gencell sg13g2::cap_cmim C1 w 5.0 l 5.0

# --- 3. Wire the inverter output Y to the cap's bottom plate -------------------------
# Y is a Metal1 strip at the inverter's right edge (x 2.245 to 2.54 um, from IHP's LEF).
# The bottom plate is Metal5, four metal layers higher. So: Metal1 out to the right,
# then a via stack Metal1 -> Metal5, then Metal5 across into the cap.
box 2.3um 1.4um 3.6um 1.9um; paint metal1

# Every metal must cover each via by a margin (the enclosure rule; DRC flagged 0.045 um
# when only the via area was painted). So paint all five metals a little larger first...
box 2.95um 1.2um 4.05um 2.1um; paint metal1; paint metal2; paint metal3; paint metal4; paint metal5
# ...then the vias. In Magic a via is painted as an area; the cut squares the foundry
# needs are generated from it when the GDS is written.
box 3.0um 1.25um 4.0um 2.05um
paint via1; paint via2; paint via3; paint via4

# Metal5 from the top of the via stack into the cap's bottom plate (which starts at x = 6 um).
box 3.0um 1.25um 7.0um 2.05um; paint metal5

# --- 4. Ports: the cell's pins, for LVS and for anyone who uses the cell -------------
# A label sticks only to paint in its own cell, and the inverter's metal lives in the
# inverter cell, so each label gets a small patch of metal painted under it here.
# 'port make N' turns the label into pin number N.
box 1.1um 1.6um 1.3um 1.8um;    paint metal1; label A   c metal1; port make 1
box 1.3um 3.7um 1.6um 3.9um;    paint metal1; label VDD c metal1; port make 2
box 1.3um -0.1um 1.6um 0.1um;   paint metal1; label VSS c metal1; port make 3
# metal6 is Magic's name for IHP's TopMetal1, the cap's top plate.
box 8.9um 2.9um 9.3um 3.3um;    paint metal6; label top c metal6; port make 4
# An internal net name (not a pin), so netlists say "out" instead of a generated name.
box 5.0um 1.65um 5.0um 1.65um;  label out c metal5

# --- 5. DRC: the design rules, checked in Magic --------------------------------------
drc check; drc catchup
puts "DRC_COUNT [drc list count total]"
puts "DRC_WHY [drc listall why]"

# --- 6. Save only our two cells; the inverter stays in IHP's GDS ---------------------
save scpa_unit
foreach c [cellname list children scpa_unit] { if {[string match cap_cmim* $c]} { load $c; save } }
quit -noprompt
