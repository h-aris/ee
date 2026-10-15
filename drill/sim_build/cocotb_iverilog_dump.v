module cocotb_iverilog_dump();
initial begin
    string dumpfile_path;    if ($value$plusargs("dumpfile_path=%s", dumpfile_path)) begin
        $dumpfile(dumpfile_path);
    end else begin
        $dumpfile("/home/haris/ee/drill/sim_build/seq101.fst");
    end
    $dumpvars(0, seq101);
end
endmodule
