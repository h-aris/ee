# gds_unit.tcl: write the cell as GDS, the file format foundries and KLayout read.
# GDS stores polygons per layer number; the IHP standard cells are written in with it.
gds readonly true
gds read /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/gds/sg13g2_stdcell.gds
load scpa_unit
gds write scpa_unit.gds
quit -noprompt
