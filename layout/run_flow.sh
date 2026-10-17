#!/usr/bin/env bash
# run_flow.sh: the whole layout-to-silicon check of the SCPA unit cell, from Ubuntu.
#   1 build   Magic draws the cell and runs its own DRC          -> scpa_unit.mag
#   2 extract Magic writes the LVS and PEX netlists              -> scpa_unit_*.spice
#   3 LVS     Netgen compares the layout netlist with ref.spice  -> lvs_report.txt
#   4 GDS     Magic writes the foundry file                      -> scpa_unit.gds
#   5 DRC     IHP's official KLayout rule deck (signoff)         -> drc_signoff/
#   6 sim     ngspice, schematic against layout with parasitics  -> energy and delay
#
# Each tool runs inside the IIC-OSIC-TOOLS Docker image: "docker run" starts a fresh
# container, mounts this folder as /foss/designs, runs one command and removes the
# container (--rm). So nothing is installed in Ubuntu, and every run starts clean.
#
# Run from this folder:  bash run_flow.sh
set -euo pipefail                         # stop at the first error or unset variable
cd "$(dirname "$0")"                      # work in this script's folder

IMG=hpretl/iic-osic-tools:latest
# PDK_ROOT and PDK tell Magic and the IHP model files where the IHP kit lives.
RUN="docker run --rm --entrypoint bash -e PDK_ROOT=/foss/pdks -e PDK=ihp-sg13g2 -v $PWD:/foss/designs -w /foss/designs $IMG -c"
MAGIC="/foss/tools/magic/bin/magic -dnull -noconsole -rcfile /foss/pdks/ihp-sg13g2/libs.tech/magic/ihp-sg13g2.magicrc"

echo "== 1 build and Magic DRC"
$RUN "$MAGIC build_unit.tcl" 2>&1 | grep DRC_COUNT

echo "== 2 extract"
$RUN "$MAGIC extract_unit.tcl" > /dev/null 2>&1
grep -c '^C' scpa_unit_pex.spice | sed 's/^/parasitic capacitors found: /'

echo "== 3 LVS"
$RUN "/foss/tools/netgen/bin/netgen -batch lvs 'scpa_unit_lvs.spice scpa_unit' 'ref.spice scpa_unit' /foss/pdks/ihp-sg13g2/libs.tech/netgen/ihp-sg13g2_setup.tcl lvs_report.txt" 2>&1 | grep -A1 'Final result' | tail -1

echo "== 4 GDS"
$RUN "$MAGIC gds_unit.tcl" > /dev/null 2>&1
ls -l scpa_unit.gds | awk '{print "scpa_unit.gds", $5, "bytes"}'

echo "== 5 signoff DRC (KLayout, IHP deck; density rules off, they apply to a whole chip)"
$RUN "PATH=/foss/tools/klayout:\$PATH python3 /foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py --path=scpa_unit.gds --topcell=scpa_unit --run_dir=drc_signoff --no_density" 2>&1 | grep -E 'Passed|violation' | sed 's/.*| INFO    | //'

echo "== 6 simulate: schematic, then layout with parasitics"
# The two netlists list the pins in different orders, so each deck gets its own order.
sed 's#NETLIST#ref.spice#;           s#PINS#a 0 vdd 0#' sim_unit.cir.in > sim_ref.cir
sed 's#NETLIST#scpa_unit_pex.spice#; s#PINS#a vdd 0 0#' sim_unit.cir.in > sim_pex.cir
for d in sim_ref sim_pex; do
  echo "-- $d"
  # .spiceinit loads IHP's compiled transistor model (PSP 103) into ngspice
  $RUN "cp /foss/pdks/ihp-sg13g2/libs.tech/ngspice/.spiceinit . && /foss/tools/ngspice/bin/ngspice -b $d.cir" 2>&1 | grep -E '^e_fj|^tpd' | awk '{print $1, $3}'
done
