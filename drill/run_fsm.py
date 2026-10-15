from cocotb_tools.runner import get_runner

r = get_runner("icarus")
r.build(sources=["seq101.v"], hdl_toplevel="seq101", build_dir="sim_build", waves=True,
        timescale=("1ns", "1ps"))
r.test(hdl_toplevel="seq101", test_module="test_seq101", build_dir="sim_build", waves=True)