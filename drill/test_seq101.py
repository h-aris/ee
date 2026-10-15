import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ReadOnly


def model(bits):
    """What y should be after each clock: 1 when the last three bits were 1, 0, 1."""
    return [int(i >= 2 and bits[i - 2:i + 1] == [1, 0, 1]) for i in range(len(bits))]


@cocotb.test()
async def random_stream(dut):
    Clock(dut.clk, 1, unit="ns").start()
    dut.rst.value, dut.x.value = 1, 0
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    rng = random.Random(3)
    bits = [rng.randint(0, 1) for _ in range(300)]
    got = []
    for b in bits:
        dut.x.value = b                   # drive between edges
        await RisingEdge(dut.clk)         # the state updates here
        await ReadOnly()
        got.append(int(dut.y.value))
        await FallingEdge(dut.clk)
    assert got == model(bits), "detector disagrees with the model"