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
//
// How to read Verilog (for someone who knows the circuits): this file describes
// hardware, not a program that runs line by line. A "module" is a block with pins.
// "reg" is a value held by flip-flops; "wire" is a connection. Everything inside
// "always @(posedge clk)" happens at each rising clock edge, all at once: these
// are the flip-flops of L6, with the logic in front of them. "<=" (non-blocking
// assignment) means "take this value at the edge", so every right-hand side is
// read before any flip-flop changes, exactly as real flip-flops sample together.
module nco #(
    // Parameters: sizes fixed when the block is built, like constants.
    parameter W = 24,     // accumulator width, bits: frequency resolution f_clk / 2^24
    parameter P = 6       // output phase width, bits: 64 phase steps per turn
) (
    input  wire         clk,     // the clock: everything below updates on its rising edge
    input  wire         rst,     // synchronous reset: clears the state at a clock edge
    input  wire [W-1:0] fcw,     // frequency control word: the step added each clock
    input  wire [P-1:0] pm,      // phase modulation word: the symbol's phase, added on top
    output reg  [P-1:0] phase    // output phase word, held in P flip-flops
);
    // The accumulator: W flip-flops holding the running phase, a fraction of a turn.
    reg [W-1:0] acc;

    always @(posedge clk) begin
        if (rst) begin
            // {W{1'b0}} = W copies of the bit 0: all zeros, whatever W is.
            acc   <= {W{1'b0}};
            phase <= {P{1'b0}};
        end else begin
            // Add the step. The sum keeps only W bits, so it wraps around past
            // 2^W - 1 back to 0: one full turn of phase, no extra logic needed.
            acc <= acc + fcw;
// `ifdef is a compile-time switch: the MUTANT define (set by run_nco.py) builds
// the broken line instead of the real one. Only one of the two is ever hardware.
`ifdef MUTANT
            phase <= acc[W-1 -: P];
`else
            // acc[W-1 -: P] = the top P bits of the accumulator (from bit W-1 down,
            // P bits wide): the coarse phase. Adding pm rotates it by the symbol's
            // phase; P-bit addition wraps around a full turn on its own.
            phase <= acc[W-1 -: P] + pm;
`endif
        end
    end
endmodule
