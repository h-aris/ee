"""Simulate the NCO with cocotb + Icarus Verilog, then synthesize it with Yosys.

Three steps, each one a CLI tool driven from Python:
  1. cocotb tests against the real RTL: must PASS.
  2. The same tests against the MUTANT build (pm ignored): must FAIL.
     A test bench that cannot fail proves nothing.
  3. Yosys generic synthesis: cell count and a gate-level netlist.
"""
# ---------------------------------------------------------------------------------
# The digital half of the testbench's flow: simulate the RTL (register-transfer
# level, the Verilog), check it, then synthesize it (turn it into logic gates and
# flip-flops) and count what it costs. Same idea as common/spice.py: Python starts
# command-line tools and reads back what they wrote.
# ---------------------------------------------------------------------------------
import os
import re          # regular expressions: find text patterns, here in Yosys's log
import shutil
import subprocess
import xml.etree.ElementTree as ET   # reads the XML file of test results

# cocotb's runner: builds the Verilog with a simulator and runs the Python tests.
from cocotb_tools.runner import get_runner

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_FOLDER = os.path.join(HERE, "..", "results")


def run_tests(mutant):
    tag = "mutant" if mutant else "rtl"
    build_folder = os.path.join(HERE, "sim_build", tag)    # separate build folders for the two
    runner = get_runner("icarus")                    # Icarus Verilog as the simulator
    # Compile nco.v. defines={"MUTANT": 1} is the same as `define MUTANT, which makes
    # the `ifdef in nco.v pick the broken line. waves=True also records waveforms
    # (open them with gtkwave) for the real build.
    runner.build(sources=[os.path.join(HERE, "rtl", "nco.v")], hdl_toplevel="nco",
                 defines={"MUTANT": 1} if mutant else {}, build_dir=build_folder,
                 always=True, timescale=("1ns", "1ps"), waves=not mutant)
    # Run every @cocotb.test() in test_nco.py against it; results go to an XML file.
    results_xml_path = runner.test(hdl_toplevel="nco", test_module="test_nco", build_dir=build_folder,
                      test_dir=HERE, results_xml=os.path.join(build_folder, "results.xml"),
                      waves=not mutant)
    # Each <testcase> in the XML has a <failure> child only if it failed.
    test_cases = ET.parse(results_xml_path).getroot().iter("testcase")
    # A dictionary, test name -> True if it passed.
    passed = {}
    for test_case in test_cases:
        passed[test_case.get("name")] = test_case.find("failure") is None
    return passed


def synth():
    yosys = shutil.which("yosys")
    if yosys is None:
        return None
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    netlist_path = os.path.join(RESULTS_FOLDER, "nco_synth.v").replace("\\", "/")
    # The Yosys script, commands separated by ";":
    #   read_verilog   load the RTL
    #   synth          generic synthesis: logic optimised, flip-flops inferred
    #   abc -g ...     map the logic onto this list of simple gate types
    #   opt_clean      remove unused wires and cells
    #   stat           print the cell count (what we read below)
    #   write_verilog  save the gate-level netlist
    script = (f"read_verilog {os.path.join(HERE, 'rtl', 'nco.v')}; "
              f"synth -top nco -flatten; abc -g AND,NAND,OR,NOR,XOR,XNOR,MUX; "
              f"opt_clean; stat; write_verilog -noattr {netlist_path}")
    # yosys -q (quiet) -p "script" -l logfile; we keep only its exit code here.
    log_path = os.path.join(RESULTS_FOLDER, "nco_yosys.log")
    exit_code = subprocess.run([yosys, "-q", "-p", script, "-l", log_path],
                         capture_output=True, text=True).returncode
    log_text = open(log_path).read()
    # Find every "Number of cells:   123" in the log; (\d+) captures the number.
    cell_counts = re.findall(r"Number of cells:\s+(\d+)", log_text)
    # The last match is the final design's count; None if Yosys failed.
    return int(cell_counts[-1]) if cell_counts and exit_code == 0 else None


def main():
    rtl_results = run_tests(mutant=False)      # every test must pass
    mutant_results = run_tests(mutant=True)    # phase_modulation must fail
    yosys_cells = synth()
    return rtl_results, mutant_results, yosys_cells


if __name__ == "__main__":
    rtl_results, mutant_results, yosys_cells = main()
    print("RTL tests:   ", rtl_results)
    print("MUTANT tests:", mutant_results, "(phase_modulation must fail)")
    print("Yosys cells: ", yosys_cells)
