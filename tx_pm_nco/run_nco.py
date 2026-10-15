"""Simulate the NCO with cocotb + Icarus Verilog, then synthesize it with Yosys.

Three steps, each one a CLI tool driven from Python:
  1. cocotb tests against the real RTL: must PASS.
  2. The same tests against the MUTANT build (pm ignored): must FAIL.
     A test bench that cannot fail proves nothing.
  3. Yosys generic synthesis: cell count and a gate-level netlist.
"""
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from cocotb_tools.runner import get_runner

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "results")


def run_tests(mutant):
    tag = "mutant" if mutant else "rtl"
    build = os.path.join(HERE, "sim_build", tag)
    runner = get_runner("icarus")
    runner.build(sources=[os.path.join(HERE, "rtl", "nco.v")], hdl_toplevel="nco",
                 defines={"MUTANT": 1} if mutant else {}, build_dir=build,
                 always=True, timescale=("1ns", "1ps"), waves=not mutant)
    xml = runner.test(hdl_toplevel="nco", test_module="test_nco", build_dir=build,
                      test_dir=HERE, results_xml=os.path.join(build, "results.xml"),
                      waves=not mutant)
    cases = ET.parse(xml).getroot().iter("testcase")
    results = {c.get("name"): c.find("failure") is None for c in cases}
    return results


def synth():
    yosys = shutil.which("yosys")
    if yosys is None:
        return None
    os.makedirs(OUT, exist_ok=True)
    net = os.path.join(OUT, "nco_synth.v").replace("\\", "/")
    script = (f"read_verilog {os.path.join(HERE, 'rtl', 'nco.v')}; "
              f"synth -top nco -flatten; abc -g AND,NAND,OR,NOR,XOR,XNOR,MUX; "
              f"opt_clean; stat; write_verilog -noattr {net}")
    log = subprocess.run([yosys, "-q", "-p", script, "-l", os.path.join(OUT, "nco_yosys.log")],
                         capture_output=True, text=True).returncode
    text = open(os.path.join(OUT, "nco_yosys.log")).read()
    cells = re.findall(r"Number of cells:\s+(\d+)", text)
    return int(cells[-1]) if cells and log == 0 else None


def main():
    good = run_tests(mutant=False)
    bad = run_tests(mutant=True)
    cells = synth()
    return good, bad, cells


if __name__ == "__main__":
    good, bad, cells = main()
    print("RTL tests:   ", good)
    print("MUTANT tests:", bad, "(phase_modulation must fail)")
    print("Yosys cells: ", cells)
