"""cocotb tests for rtl/nco.v, checked cycle by cycle against a Python model."""
# ---------------------------------------------------------------------------------
# cocotb: write the testbench in Python, run the design in a Verilog simulator
# (Icarus here). Python drives the design's input pins and reads its output pins
# while the simulation runs. The verification vocabulary of L7 7.14, all in here:
#   DUT        "dut" below: the nco module, its pins as dut.clk, dut.fcw, dut.phase
#   stimulus   directed (sawtooth, phase_modulation) and random (random_frequency)
#   golden model   model(): the same NCO in four lines of Python
#   scoreboard + assertion   "assert got == model(...)": every clock compared
#   mutation   run_nco.py runs these tests on a broken build, which must fail
#
# "async def" and "await": a test is a coroutine, a function that can pause.
# "await RisingEdge(dut.clk)" pauses this test until the simulator reaches the
# next rising clock edge, then continues. Simulated time only moves while a test
# is waiting, so the test and the hardware take turns.
# ---------------------------------------------------------------------------------
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge

W = 24      # accumulator width, bits: must match the Verilog parameter
P = 6       # output phase width, bits: must match too


def start_clock(dut):
    # A 1 ns period clock on the clk pin (1 GHz), running in the background.
    Clock(dut.clk, 1, unit="ns").start()


async def reset(dut, fcw, pm=0):
    # Drive inputs only after a falling edge: there is half a period before the next
    # rising edge, so the flip-flops see stable inputs (L6's setup and hold, in a
    # testbench). Writing during the read-only phase was one of the five agent errors.
    await FallingEdge(dut.clk)   # leave any read-only phase before driving inputs
    dut.rst.value = 1            # .value is how cocotb writes and reads a pin
    dut.fcw.value = fcw
    dut.pm.value = pm
    for edge in range(2):        # hold reset for two rising edges
        await RisingEdge(dut.clk)
    dut.rst.value = 0


async def collect(dut, cycles):
    # Read the output once per clock, for `cycles` clocks, into a list.
    phase_words = []
    for clock in range(cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()             # wait until every signal has settled for this edge
        phase_words.append(int(dut.phase.value))
    return phase_words


def model(fcw, pm, cycles):
    """Expected phase words after reset is released, one per clock."""
    # The golden model: what the hardware should do, written as plainly as possible.
    accumulator = 0
    phase = 0
    expected = []
    for clock in range(cycles):
        # Both new values computed from the OLD ones in one line, as the flip-flops do
        # (two separate lines would let the second see the new accumulator):
        # % 2**W wraps the accumulator (MATLAB: mod); >> (W - P) keeps the top P bits.
        accumulator, phase = (accumulator + fcw) % 2**W, ((accumulator >> (W - P)) + pm) % 2**P
        expected.append(phase)
    return expected


# @cocotb.test() marks a function as a test; the runner finds and runs each one.
@cocotb.test()
async def sawtooth(dut):
    """fcw = 2^W / 64 steps the phase by one LSB (5.625 deg) per clock."""
    # Directed test: a step of exactly one phase LSB per clock gives a staircase
    # 0, 1, 2, ..., 63, 0, ... that anyone can check by eye.
    fcw = 2**W // 64             # // is integer division
    start_clock(dut)
    await reset(dut, fcw)
    measured = await collect(dut, 200)
    assert measured == model(fcw, 0, 200), "phase does not ramp one LSB per clock"


@cocotb.test()
async def random_frequency(dut):
    """Random frequency words match the model for 500 clocks each."""
    # Random stimulus with a fixed seed (1): random, but the same every run, so a
    # failure can be reproduced.
    random_generator = random.Random(1)
    start_clock(dut)
    for trial in range(5):
        fcw = random_generator.randrange(1, 2**W)
        await reset(dut, fcw)
        measured = await collect(dut, 500)
        assert measured == model(fcw, 0, 500), f"mismatch for fcw={fcw}"


@cocotb.test()
async def phase_modulation(dut):
    """pm = 16 rotates the output by 90 degrees against pm = 0."""
    # The test that catches the mutant: with pm = 16 (16 x 5.625 = 90 degrees) every
    # output must be 16 steps ahead of the pm = 0 run. The mutant ignores pm, so
    # its two runs are identical and this assertion fails.
    fcw = 123457
    start_clock(dut)
    await reset(dut, fcw, pm=0)
    without_pm = await collect(dut, 100)
    await reset(dut, fcw, pm=16)
    with_pm = await collect(dut, 100)
    # zip pairs the two lists element by element; all() is True only if every pair passes.
    assert all((rotated - plain) % 64 == 16 for rotated, plain in zip(with_pm, without_pm)), "pm does not rotate phase"
