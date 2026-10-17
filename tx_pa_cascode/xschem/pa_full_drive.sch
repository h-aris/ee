v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Cascode class-AB PA at full drive (0.9 V peak input): look at what each transistor stands} 0 -120 0 0 0.5 0.5 {}
C {devices/vsource.sym} 0 0 0 0 {name=Vdd value=2.4}
C {devices/lab_pin.sym} 0 -30 0 0 {name=p1 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 0 30 0 0 {name=p2 sig_type=std_logic lab=0}
C {devices/vsource.sym} 200 0 0 0 {name=Vcas value=1.6}
C {devices/lab_pin.sym} 200 -30 0 0 {name=p3 sig_type=std_logic lab=cg}
C {devices/lab_pin.sym} 200 30 0 0 {name=p4 sig_type=std_logic lab=0}
C {devices/vsource.sym} 400 0 0 0 {name=Vin value="DC 0.5 AC 1 SIN(0.5 0.9 1e9)"}
C {devices/lab_pin.sym} 400 -30 0 0 {name=p5 sig_type=std_logic lab=g}
C {devices/lab_pin.sym} 400 30 0 0 {name=p6 sig_type=std_logic lab=0}
C {devices/nmos4.sym} 600 0 0 0 {name=M1 model=nch w=1.2m l=100n extra=nf=120 m=1}
C {devices/lab_pin.sym} 620 -30 0 0 {name=p7 sig_type=std_logic lab=x}
C {devices/lab_pin.sym} 580 0 0 0 {name=p8 sig_type=std_logic lab=g}
C {devices/lab_pin.sym} 620 30 0 0 {name=p9 sig_type=std_logic lab=0}
C {devices/lab_pin.sym} 620 0 0 0 {name=p10 sig_type=std_logic lab=0}
C {devices/nmos4.sym} 800 0 0 0 {name=M2 model=nch w=1.2m l=100n extra=nf=120 m=1}
C {devices/lab_pin.sym} 820 -30 0 0 {name=p11 sig_type=std_logic lab=d}
C {devices/lab_pin.sym} 780 0 0 0 {name=p12 sig_type=std_logic lab=cg}
C {devices/lab_pin.sym} 820 30 0 0 {name=p13 sig_type=std_logic lab=x}
C {devices/lab_pin.sym} 820 0 0 0 {name=p14 sig_type=std_logic lab=0}
C {devices/ind.sym} 0 220 0 0 {name=Ld value=4n m=1}
C {devices/lab_pin.sym} 0 190 0 0 {name=p15 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 0 250 0 0 {name=p16 sig_type=std_logic lab=d}
C {devices/res.sym} 200 220 0 0 {name=Rp value=502.655 m=1}
C {devices/lab_pin.sym} 200 190 0 0 {name=p17 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 200 250 0 0 {name=p18 sig_type=std_logic lab=d}
C {devices/capa.sym} 400 220 0 0 {name=Cd value=5.25501p m=1}
C {devices/lab_pin.sym} 400 190 0 0 {name=p19 sig_type=std_logic lab=d}
C {devices/lab_pin.sym} 400 250 0 0 {name=p20 sig_type=std_logic lab=0}
C {devices/capa.sym} 600 220 0 0 {name=Cout value=100p m=1}
C {devices/lab_pin.sym} 600 190 0 0 {name=p21 sig_type=std_logic lab=d}
C {devices/lab_pin.sym} 600 250 0 0 {name=p22 sig_type=std_logic lab=out}
C {devices/res.sym} 800 220 0 0 {name=RL value=50 m=1}
C {devices/lab_pin.sym} 800 190 0 0 {name=p23 sig_type=std_logic lab=out}
C {devices/lab_pin.sym} 800 250 0 0 {name=p24 sig_type=std_logic lab=0}
C {devices/code_shown.sym} 0 480 0 0 {name=s1 only_toplevel=false value=".include /foss/designs/common/models.lib
.control
tran 1p 30n 0 1p
meas tran vout_pk MAX v(out) from=20n to=30n
meas tran vds1_max MAX v(x) from=20n to=30n
let vds2 = v(d) - v(x)
meas tran vds2_max MAX vds2 from=20n to=30n
plot v(d) v(x) v(out) xlimit 25n 30n
.endc"}
