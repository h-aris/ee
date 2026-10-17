v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N -420 -10 -320 -10 {lab=VSS}
N -530 -100 -530 -10 {lab=VSS}
N -320 -100 -320 -10 {lab=VSS}
N -530 -200 -530 -160 {lab=CLK}
N -420 -150 -420 -90 {lab=VDD}
N -320 -200 -320 -160 {lab=CLK_B}
N 70 -250 70 -220 {lab=VDD}
N 70 -160 70 -140 {lab=BOT}
N 70 -160 160 -160 {lab=BOT}
N 70 -60 70 -50 {lab=VSS}
N 110 -210 140 -210 {lab=VSS}
N 10 -90 30 -90 {lab=VSS}
N 10 -90 10 -60 {lab=VSS}
N 10 -60 70 -60 {lab=VSS}
N 70 -80 70 -60 {lab=VSS}
N -420 -30 -420 -10 {lab=VSS}
N -530 -10 -420 -10 {lab=VSS}
N -420 -10 -420 10 {lab=VSS}
N -30 -110 30 -110 {lab=CLK_B}
N 110 -190 140 -190 {lab=CLK}
N 230 -160 260 -160 {lab=TOP}
N 230 -160 230 -120 {lab=TOP}
N 230 -60 230 -50 {lab=#net1}
N 230 10 230 30 {lab=VSS}
N 220 -160 230 -160 {lab=TOP}
N 320 -160 400 -160 {lab=OUT}
N 400 -160 400 -140 {lab=OUT}
N 400 -80 400 -50 {lab=VSS}
N -420 70 -420 110 {lab=0}
C {vsource.sym} -420 -60 0 0 {name=V_DD value=1.1 savecurrent=false}
C {vsource.sym} -530 -130 0 0 {name=V_CLK value="PULSE(0 1 0 20p 20p 480p 1n)" savecurrent=false}
C {vsource.sym} -320 -130 0 0 {name=V_CLK_B value="PULSE(1 0 0 20p 20p 480p 1n)" savecurrent=false}
C {gnd.sym} -420 110 0 0 {name=l1 lab=0}
C {switch_ngspice.sym} 70 -190 2 0 {name=S_UP model=swn
device_model=".MODEL SW1 SW 
+ VT=0.9 VH=0.01
+ RON=0.01 ROFF=10G "}
C {switch_ngspice.sym} 70 -110 0 0 {name=S_DN model=swn
device_model=".MODEL SW1 SW 
+ VT=0.9 VH=0.01
+ RON=0.01 ROFF=10G "}
C {lab_pin.sym} 70 -250 0 0 {name=p4 sig_type=std_logic lab=VDD}
C {lab_pin.sym} -420 -150 0 0 {name=p1 sig_type=std_logic lab=VDD}
C {lab_pin.sym} -530 -200 0 0 {name=p2 sig_type=std_logic lab=CLK}
C {lab_pin.sym} -320 -200 0 0 {name=p3 sig_type=std_logic lab=CLK_B}
C {lab_pin.sym} 70 -50 0 0 {name=p6 sig_type=std_logic lab=VSS}
C {lab_pin.sym} -30 -110 0 0 {name=p7 sig_type=std_logic lab=CLK_B}
C {lab_pin.sym} 140 -190 0 0 {name=p8 sig_type=std_logic lab=CLK}
C {lab_pin.sym} 140 -210 1 0 {name=p9 sig_type=std_logic lab=VSS}
C {lab_pin.sym} 160 -160 0 0 {name=p10 sig_type=std_logic lab=BOT}
C {capa.sym} 190 -160 3 0 {name=C_SW
m=1
value=0.397887p
footprint=1206
device="ceramic capacitor"}
C {lab_pin.sym} 250 -160 3 0 {name=p11 sig_type=std_logic lab=TOP}
C {capa.sym} 230 -90 2 0 {name=C_GND
m=1
value=0.397887p
footprint=1206
device="ceramic capacitor"}
C {res.sym} 230 -20 0 0 {name=R_GND
value=1
footprint=1206
device=resistor
m=1}
C {lab_pin.sym} 230 30 0 0 {name=p12 sig_type=std_logic lab=VSS}
C {ind.sym} 290 -160 1 0 {name=L_MATCH
m=1
value=31.831n
footprint=1206
device=inductor}
C {lab_pin.sym} 350 -160 3 0 {name=p13 sig_type=std_logic lab=OUT}
C {res.sym} 400 -110 0 0 {name=R_GND1
value=50
footprint=1206
device=resistor
m=1}
C {lab_pin.sym} 400 -50 0 0 {name=p14 sig_type=std_logic lab=VSS}
C {code_shown.sym} -460 -400 0 0 {name=s1 only_toplevel=false value="
.model swn sw(vt=0.5 vh=0 ron=1 roff=1e9)
.control
tran 1p 40n 0 1p
meas tran vpk MAX v(OUT) from=30n to=40n
meas tran vmin MIN v(OUT) from=30n to=40n
plot v(OUT) v(BOT) xlimit 35n 40n
.endc
"}
C {vsource.sym} -420 40 0 0 {name=V_SS value=0 savecurrent=false}
C {lab_pin.sym} -530 -10 0 0 {name=p5 sig_type=std_logic lab=VSS}
