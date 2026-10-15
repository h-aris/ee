| Block | Check | Result | Spec | |
|---|---|---|---|---|
| TX AM | Pout at full code | 4.81 mW | >= 4.5 | PASS |
| TX AM | efficiency vs SCPA theory, worst gap | 1.1 pts | <= 3 | PASS |
| TX AM | efficiency vs theory at code 16/32 | 1.04 pts | <= 2 | PASS |
| TX AM | HD3 at 1/3 duty | -126.0 dBc | <= -40 | PASS |
| TX AM | HD2 at 1/2 duty | -237.9 dBc | <= -40 | PASS |
| TX PM | cocotb tests on RTL | 3/3  | all pass | PASS |
| TX PM | mutant RTL caught by phase test | True  | True | PASS |
| TX PM | Yosys synthesis, generic gates | 176 cells | > 0 | PASS |
| TX PA | saturated output power | 19.5 dBm | >= 17 | PASS |
| TX PA | peak drain efficiency | 68.1 % | >= 50 | PASS |
| TX PA | drain efficiency at 6 dB back-off | 43.0 % | report | PASS |
| TX PA | AM-PM at saturation | -7.0 deg | report | PASS |
| TX PA | worst device Vds peak (1.2 V devices) | 4.19 V | <= 2.4 | OPEN |
| TX system | EVM, 64-QAM, 6-bit phase | 0.66 % | <= 8 | PASS |
| TX system | ACLR, 64-QAM, 6-bit phase | -39.5 dBc | <= -30 | PASS |
| TX system | 5 ns AM/PM skew degrades EVM | +11.0 dB | > 0 | PASS |
| TX system | SCPA average efficiency, 6.5 dB PAPR | 83.3 % | report | PASS |
| TX system | class-AB PA average efficiency, same | 59.0 % | report | PASS |
| TX system | class-AB PA EVM at P1dB peaks, no DPD | 10.7 % | <= 8 | OPEN |
| RX LNA | S11 at 1 GHz | -46.0 dB | <= -10 | PASS |
| RX LNA | S21 at 1 GHz | 25.4 dB | >= 15 | PASS |
| RX LNA | noise figure at 1 GHz (Lg Q = 30) | 0.70 dB | <= 2 | PASS |
| RX LNA | cascode removed: match breaks (Miller) | -2.0 dB | > -10 | PASS |
