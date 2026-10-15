// TX phase path: numerically controlled oscillator (NCO) with phase modulation.
//
// A W-bit phase accumulator advances by the frequency control word `fcw`
// every clock, so it wraps fcw / 2^W times per clock: the carrier offset.
// The top P bits are the coarse phase; the P-bit modulation word `pm` adds
// the symbol's phase. With P = 6 the output steps in 360/64 = 5.625 degrees,
// the 64-PSK grid. In a polar transmitter this word would set a digital-to-
// time converter or a DPLL's phase; here it is checked against a Python model.
//
// MUTANT: a deliberately broken variant that ignores `pm`. The test bench
// must fail on it, which proves the phase-modulation test can catch a bug.
module nco #(
    parameter W = 24,
    parameter P = 6
) (
    input  wire         clk,
    input  wire         rst,
    input  wire [W-1:0] fcw,
    input  wire [P-1:0] pm,
    output reg  [P-1:0] phase
);
    reg [W-1:0] acc;

    always @(posedge clk) begin
        if (rst) begin
            acc   <= {W{1'b0}};
            phase <= {P{1'b0}};
        end else begin
            acc <= acc + fcw;
`ifdef MUTANT
            phase <= acc[W-1 -: P];
`else
            phase <= acc[W-1 -: P] + pm;
`endif
        end
    end
endmodule
