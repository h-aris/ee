v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N -90 -60 -90 -40 {lab=#net1}
N -90 -60 -20 -60 {lab=#net1}
N 90 -60 90 -40 {lab=out}
N 40 -60 90 -60 {lab=out}
N 90 -60 190 -60 {lab=out}
N 190 -60 190 -40 {lab=out}
N 190 -80 190 -60 {lab=out}
N 180 -80 190 -80 {lab=out}
C {vsource.sym} -90 -10 0 0 {name=V1 value=12 savecurrent=false}
C {res.sym} 10 -60 1 0 {name=R1
value=4k
footprint=1206
device=resistor
m=1}
C {res.sym} 90 -10 2 0 {name=R2
value=12k
footprint=1206
device=resistor
m=1}
C {res.sym} 190 -10 2 0 {name=R3
value=6k
footprint=1206
device=resistor
m=1}
C {gnd.sym} -90 20 0 0 {name=l1 lab=0}
C {gnd.sym} 90 20 0 0 {name=l2 lab=0}
C {gnd.sym} 190 20 0 0 {name=l3 lab=0}
C {lab_pin.sym} 180 -80 0 0 {name=p1 sig_type=std_logic lab=out}
C {code_shown.sym} 270 -130 0 0 {name=s1 only_toplevel=false value="
.control
op
print all
.endc
"}
