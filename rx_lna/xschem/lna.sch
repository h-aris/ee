v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Cascode LNA at 1 GHz, the design lna.py tuned: match, gain, noise figure} 0 -120 0 0 0.5 0.5 {}
C {devices/vsource.sym} 0 0 0 0 {name=Vdd value=1.2}
C {devices/lab_pin.sym} 0 -30 0 0 {name=p1 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 0 30 0 0 {name=p2 sig_type=std_logic lab=0}
C {devices/vsource.sym} 200 0 0 0 {name=Vs value="DC 0 AC 1"}
C {devices/lab_pin.sym} 200 -30 0 0 {name=p3 sig_type=std_logic lab=src}
C {devices/lab_pin.sym} 200 30 0 0 {name=p4 sig_type=std_logic lab=0}
C {devices/res.sym} 400 0 0 0 {name=Rs value=50 m=1}
C {devices/lab_pin.sym} 400 -30 0 0 {name=p5 sig_type=std_logic lab=src}
C {devices/lab_pin.sym} 400 30 0 0 {name=p6 sig_type=std_logic lab=rfin}
C {devices/capa.sym} 600 0 0 0 {name=Cin value=100p m=1}
C {devices/lab_pin.sym} 600 -30 0 0 {name=p7 sig_type=std_logic lab=rfin}
C {devices/lab_pin.sym} 600 30 0 0 {name=p8 sig_type=std_logic lab=g1}
C {devices/ind.sym} 800 0 0 0 {name=Lg value=37.198n m=1}
C {devices/lab_pin.sym} 800 -30 0 0 {name=p9 sig_type=std_logic lab=g1}
C {devices/lab_pin.sym} 800 30 0 0 {name=p10 sig_type=std_logic lab=g2}
C {devices/res.sym} 0 220 0 0 {name=Rlg value=7.79173 m=1}
C {devices/lab_pin.sym} 0 190 0 0 {name=p11 sig_type=std_logic lab=g2}
C {devices/lab_pin.sym} 0 250 0 0 {name=p12 sig_type=std_logic lab=g}
C {devices/vsource.sym} 200 220 0 0 {name=Vb value=0.574994}
C {devices/lab_pin.sym} 200 190 0 0 {name=p13 sig_type=std_logic lab=bias}
C {devices/lab_pin.sym} 200 250 0 0 {name=p14 sig_type=std_logic lab=0}
C {devices/ind.sym} 400 220 0 0 {name=Lbias value=10u m=1}
C {devices/lab_pin.sym} 400 190 0 0 {name=p15 sig_type=std_logic lab=bias}
C {devices/lab_pin.sym} 400 250 0 0 {name=p16 sig_type=std_logic lab=g}
C {devices/ind.sym} 600 220 0 0 {name=Ls value=0.390602n m=1}
C {devices/lab_pin.sym} 600 190 0 0 {name=p17 sig_type=std_logic lab=s}
C {devices/lab_pin.sym} 600 250 0 0 {name=p18 sig_type=std_logic lab=0}
C {devices/nmos4.sym} 800 220 0 0 {name=M1 model=nch w=300u l=100n extra=nf=30 m=1}
C {devices/lab_pin.sym} 820 190 0 0 {name=p19 sig_type=std_logic lab=x}
C {devices/lab_pin.sym} 780 220 0 0 {name=p20 sig_type=std_logic lab=g}
C {devices/lab_pin.sym} 820 250 0 0 {name=p21 sig_type=std_logic lab=s}
C {devices/lab_pin.sym} 820 220 0 0 {name=p22 sig_type=std_logic lab=0}
C {devices/vsource.sym} 0 440 0 0 {name=Vcas value=1.2}
C {devices/lab_pin.sym} 0 410 0 0 {name=p23 sig_type=std_logic lab=cg}
C {devices/lab_pin.sym} 0 470 0 0 {name=p24 sig_type=std_logic lab=0}
C {devices/nmos4.sym} 200 440 0 0 {name=M2 model=nch w=300u l=100n extra=nf=30 m=1}
C {devices/lab_pin.sym} 220 410 0 0 {name=p25 sig_type=std_logic lab=d}
C {devices/lab_pin.sym} 180 440 0 0 {name=p26 sig_type=std_logic lab=cg}
C {devices/lab_pin.sym} 220 470 0 0 {name=p27 sig_type=std_logic lab=x}
C {devices/lab_pin.sym} 220 440 0 0 {name=p28 sig_type=std_logic lab=0}
C {devices/ind.sym} 400 440 0 0 {name=Ld value=8n m=1}
C {devices/lab_pin.sym} 400 410 0 0 {name=p29 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 400 470 0 0 {name=p30 sig_type=std_logic lab=d}
C {devices/res.sym} 600 440 0 0 {name=Rp value=502.655 m=1}
C {devices/lab_pin.sym} 600 410 0 0 {name=p31 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 600 470 0 0 {name=p32 sig_type=std_logic lab=d}
C {devices/capa.sym} 800 440 0 0 {name=Cd value=1.74p m=1}
C {devices/lab_pin.sym} 800 410 0 0 {name=p33 sig_type=std_logic lab=d}
C {devices/lab_pin.sym} 800 470 0 0 {name=p34 sig_type=std_logic lab=0}
C {devices/capa.sym} 0 660 0 0 {name=Cout value=100p m=1}
C {devices/lab_pin.sym} 0 630 0 0 {name=p35 sig_type=std_logic lab=d}
C {devices/lab_pin.sym} 0 690 0 0 {name=p36 sig_type=std_logic lab=out}
C {devices/res.sym} 200 660 0 0 {name=RL value=50 m=1}
C {devices/lab_pin.sym} 200 630 0 0 {name=p37 sig_type=std_logic lab=out}
C {devices/lab_pin.sym} 200 690 0 0 {name=p38 sig_type=std_logic lab=0}
C {devices/code_shown.sym} 0 920 0 0 {name=s1 only_toplevel=false value=".include /foss/designs/common/models.lib
.control
ac dec 200 100meg 10g
let zin = v(rfin) / (-i(vs))
let s11 = db((zin - 50) / (zin + 50))
let s21 = db(2 * v(out))
meas ac s11_1g FIND s11 AT=1e9
meas ac s21_1g FIND s21 AT=1e9
plot s11 s21 xlog
noise v(out) vs dec 200 100meg 10g
setplot noise1
let nf = 10 * log10(inoise_spectrum^2 / (4 * 1.380649e-23 * 300.15 * 50))
print frequency[200] nf[200]
plot nf xlog ylimit 0 8
.endc"}
