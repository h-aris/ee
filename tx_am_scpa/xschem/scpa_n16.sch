v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {SCPA at code 16 of 32: 16 units switching, 16 held at ground} 0 -120 0 0 0.5 0.5 {}
C {devices/vsource.sym} 0 0 0 0 {name=Vdd value=1.1}
C {devices/lab_pin.sym} 0 -30 0 0 {name=p1 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 0 30 0 0 {name=p2 sig_type=std_logic lab=0}
C {devices/vsource.sym} 200 0 0 0 {name=Vc value="PULSE(0 1 0 20p 20p 480p 1n)"}
C {devices/lab_pin.sym} 200 -30 0 0 {name=p3 sig_type=std_logic lab=ctl}
C {devices/lab_pin.sym} 200 30 0 0 {name=p4 sig_type=std_logic lab=0}
C {devices/vsource.sym} 400 0 0 0 {name=Vcb value="PULSE(1 0 0 20p 20p 480p 1n)"}
C {devices/lab_pin.sym} 400 -30 0 0 {name=p5 sig_type=std_logic lab=ctlb}
C {devices/lab_pin.sym} 400 30 0 0 {name=p6 sig_type=std_logic lab=0}
C {devices/switch_ngspice.sym} 600 0 0 0 {name=Sup model=swn}
C {devices/lab_pin.sym} 600 -30 0 0 {name=p7 sig_type=std_logic lab=asw}
C {devices/lab_pin.sym} 600 30 0 0 {name=p8 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 560 0 0 0 {name=p9 sig_type=std_logic lab=ctl}
C {devices/lab_pin.sym} 560 20 0 0 {name=p10 sig_type=std_logic lab=0}
C {devices/switch_ngspice.sym} 800 0 0 0 {name=Sdn model=swn}
C {devices/lab_pin.sym} 800 -30 0 0 {name=p11 sig_type=std_logic lab=asw}
C {devices/lab_pin.sym} 800 30 0 0 {name=p12 sig_type=std_logic lab=0}
C {devices/lab_pin.sym} 760 0 0 0 {name=p13 sig_type=std_logic lab=ctlb}
C {devices/lab_pin.sym} 760 20 0 0 {name=p14 sig_type=std_logic lab=0}
C {devices/capa.sym} 0 220 0 0 {name=Csw value=3.97887e-13 m=1}
C {devices/lab_pin.sym} 0 190 0 0 {name=p15 sig_type=std_logic lab=asw}
C {devices/lab_pin.sym} 0 250 0 0 {name=p16 sig_type=std_logic lab=top}
C {devices/res.sym} 200 220 0 0 {name=Rgnd value=1 m=1}
C {devices/lab_pin.sym} 200 190 0 0 {name=p17 sig_type=std_logic lab=0}
C {devices/lab_pin.sym} 200 250 0 0 {name=p18 sig_type=std_logic lab=agnd}
C {devices/capa.sym} 400 220 0 0 {name=Cgnd value=3.97887e-13 m=1}
C {devices/lab_pin.sym} 400 190 0 0 {name=p19 sig_type=std_logic lab=agnd}
C {devices/lab_pin.sym} 400 250 0 0 {name=p20 sig_type=std_logic lab=top}
C {devices/ind.sym} 600 220 0 0 {name=L1 value=3.1831e-08 m=1}
C {devices/lab_pin.sym} 600 190 0 0 {name=p21 sig_type=std_logic lab=top}
C {devices/lab_pin.sym} 600 250 0 0 {name=p22 sig_type=std_logic lab=out}
C {devices/res.sym} 800 220 0 0 {name=RL value=50 m=1}
C {devices/lab_pin.sym} 800 190 0 0 {name=p23 sig_type=std_logic lab=out}
C {devices/lab_pin.sym} 800 250 0 0 {name=p24 sig_type=std_logic lab=0}
C {devices/code_shown.sym} 0 480 0 0 {name=s1 only_toplevel=false value=".model swn sw(vt=0.5 vh=0 ron=1 roff=1e9)
.control
tran 1p 40n 0 1p
meas tran vpk MAX v(out) from=30n to=40n
meas tran vmin MIN v(out) from=30n to=40n
plot v(out) v(asw) xlimit 35n 40n
.endc"}
