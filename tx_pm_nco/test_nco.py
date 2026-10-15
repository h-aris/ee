"""cocotb tests for rtl/nco.v, checked cycle by cycle against a Python model."""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge

W, P = 24, 6


def start_clock(dut):
    Clock(dut.clk, 1, unit="ns").start()


async def reset(dut, fcw, pm=0):
    await FallingEdge(dut.clk)   # leave any read-only phase before driving inputs
    dut.rst.value = 1
    dut.fcw.value = fcw
    dut.pm.value = pm
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.rst.value = 0


async def collect(dut, cycles):
    out = []
    for _ in range(cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        out.append(int(dut.phase.value))
    return out


def model(fcw, pm, cycles):
    """Expected phase words after reset is released, one per clock."""
    acc, phase, out = 0, 0, []
    for _ in range(cycles):
        acc, phase = (acc + fcw) % 2**W, ((acc >> (W - P)) + pm) % 2**P
        out.append(phase)
    return out


@cocotb.test()
async def sawtooth(dut):
    """fcw = 2^W / 64 steps the phase by one LSB (5.625 deg) per clock."""
    fcw = 2**W // 64
    start_clock(dut)
    await reset(dut, fcw)
    got = await collect(dut, 200)
    assert got == model(fcw, 0, 200), "phase does not ramp one LSB per clock"


@cocotb.test()
async def random_frequency(dut):
    """Random frequency words match the model for 500 clocks each."""
    rng = random.Random(1)
    start_clock(dut)
    for _ in range(5):
        fcw = rng.randrange(1, 2**W)
        await reset(dut, fcw)
        got = await collect(dut, 500)
        assert got == model(fcw, 0, 500), f"mismatch for fcw={fcw}"


@cocotb.test()
async def phase_modulation(dut):
    """pm = 16 rotates the output by 90 degrees against pm = 0."""
    fcw = 123457
    start_clock(dut)
    await reset(dut, fcw, pm=0)
    base = await collect(dut, 100)
    await reset(dut, fcw, pm=16)
    rot = await collect(dut, 100)
    assert all((r - b) % 64 == 16 for r, b in zip(rot, base)), "pm does not rotate phase"
