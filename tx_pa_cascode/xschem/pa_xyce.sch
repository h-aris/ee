v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Cascode class-AB PA at full drive, simulated with Xyce (Simulation > Configure simulators and tools > Xyce batch)} 0 -120 0 0 0.5 0.5 {}
C {devices/vsource.sym} 0 0 0 0 {name=V_DD value=2.4}
C {devices/lab_pin.sym} 0 -30 0 0 {name=p1 sig_type=std_logic lab=VDD}
C {devices/lab_pin.sym} 0 30 0 0 {name=p2 sig_type=std_logic lab=VSS}
C {devices/vsource.sym} 200 0 0 0 {name=V_CAS value=1.6}
C {devices/lab_pin.sym} 200 -30 0 0 {name=p3 sig_type=std_logic lab=CAS}
C {devices/lab_pin.sym} 200 30 0 0 {name=p4 sig_type=std_logic lab=VSS}
C {devices/vsource.sym} 400 0 0 0 {name=V_IN value="SIN(0.5 0.9 1e9)"}
C {devices/lab_pin.sym} 400 -30 0 0 {name=p5 sig_type=std_logic lab=IN}
C {devices/lab_pin.sym} 400 30 0 0 {name=p6 sig_type=std_logic lab=VSS}
C {devices/nmos4.sym} 600 0 0 0 {name=M_IN model=nch w=1.2m l=100n extra=nf=120 m=1}
C {devices/lab_pin.sym} 620 -30 0 0 {name=p7 sig_type=std_logic lab=MID}
C {devices/lab_pin.sym} 580 0 0 0 {name=p8 sig_type=std_logic lab=IN}
C {devices/lab_pin.sym} 620 30 0 0 {name=p9 sig_type=std_logic lab=VSS}
C {devices/lab_pin.sym} 620 0 0 0 {name=p10 sig_type=std_logic lab=VSS}
C {devices/nmos4.sym} 800 0 0 0 {name=M_CAS model=nch w=1.2m l=100n extra=nf=120 m=1}
C {devices/lab_pin.sym} 820 -30 0 0 {name=p11 sig_type=std_logic lab=DRAIN}
C {devices/lab_pin.sym} 780 0 0 0 {name=p12 sig_type=std_logic lab=CAS}
C {devices/lab_pin.sym} 820 30 0 0 {name=p13 sig_type=std_logic lab=MID}
C {devices/lab_pin.sym} 820 0 0 0 {name=p14 sig_type=std_logic lab=VSS}
C {devices/ind.sym} 0 220 0 0 {name=L_D value=4n m=1}
C {devices/lab_pin.sym} 0 190 0 0 {name=p15 sig_type=std_logic lab=VDD}
C {devices/lab_pin.sym} 0 250 0 0 {name=p16 sig_type=std_logic lab=DRAIN}
C {devices/res.sym} 200 220 0 0 {name=R_LOSS value=502.655 m=1}
C {devices/lab_pin.sym} 200 190 0 0 {name=p17 sig_type=std_logic lab=VDD}
C {devices/lab_pin.sym} 200 250 0 0 {name=p18 sig_type=std_logic lab=DRAIN}
C {devices/capa.sym} 400 220 0 0 {name=C_TUNE value=5.25501p m=1}
C {devices/lab_pin.sym} 400 190 0 0 {name=p19 sig_type=std_logic lab=DRAIN}
C {devices/lab_pin.sym} 400 250 0 0 {name=p20 sig_type=std_logic lab=VSS}
C {devices/capa.sym} 600 220 0 0 {name=C_OUT value=100p m=1}
C {devices/lab_pin.sym} 600 190 0 0 {name=p21 sig_type=std_logic lab=DRAIN}
C {devices/lab_pin.sym} 600 250 0 0 {name=p22 sig_type=std_logic lab=OUT}
C {devices/res.sym} 800 220 0 0 {name=R_LOAD value=50 m=1}
C {devices/lab_pin.sym} 800 190 0 0 {name=p23 sig_type=std_logic lab=OUT}
C {devices/lab_pin.sym} 800 250 0 0 {name=p24 sig_type=std_logic lab=VSS}
C {devices/vsource.sym} 1000 0 0 0 {name=V_SS value=0}
C {devices/lab_pin.sym} 1000 -30 0 0 {name=p25 sig_type=std_logic lab=VSS}
C {devices/gnd.sym} 1000 30 0 0 {name=l1 lab=0}
C {devices/code_shown.sym} 0 480 0 0 {name=s1 only_toplevel=false value=".include /foss/designs/common/models.lib
.tran 1p 30n 0 1p
.print tran format=raw file=pa_xyce.raw V(OUT) V(DRAIN) V(MID) I(V_DD)
.measure tran VOUT_MAX MAX V(OUT) FROM=20n TO=30n
.measure tran IDD_AVG AVG I(V_DD) FROM=20n TO=30n
.measure tran VDS_CAS_MAX MAX V(DRAIN,MID) FROM=20n TO=30n
.measure tran VDS_IN_MAX MAX V(MID) FROM=20n TO=30n"}
