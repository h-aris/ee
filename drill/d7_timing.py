"""Setup and hold slack for one flip-flop-to-flip-flop path, all times in ps."""
T = 1000          # clock period: 1 GHz
t_cq = 50         # clock-to-Q of the launching flip-flop
t_max = 700       # slowest logic path between the two flip-flops
t_min = 20        # fastest logic path
t_su, t_h = 60, 30
skew = 40         # the capturing flip-flop's clock arrives this much later


def slacks(T, t_cq, t_max, t_min, t_su, t_h, skew):
    setup = (T + skew) - (t_cq + t_max + t_su)    # data must arrive t_su before the next edge
    hold = (t_cq + t_min) - (t_h + skew)          # data must not change until t_h after this edge
    return setup, hold


s, h = slacks(T, t_cq, t_max, t_min, t_su, t_h, skew)
print(f"setup slack {s} ps, hold slack {h} ps")
fmax = 1e3 / (t_cq + t_max + t_su - skew)
print(f"fastest clock for this path: {fmax:.2f} GHz")