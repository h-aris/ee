// Moore FSM: y goes high for one clock after the input stream ends in 1, 0, 1.
module seq101 (input wire clk, input wire rst, input wire x, output wire y);
    localparam S0 = 2'd0,   // nothing useful seen yet
               S1 = 2'd1,   // last bit was 1
               S2 = 2'd2,   // last bits were 1, 0
               S3 = 2'd3;   // last bits were 1, 0, 1: detected
    reg [1:0] state, next;

    always @(posedge clk)                 // the state register: flip-flops
        state <= rst ? S0 : next;

    always @(*) begin                     // next-state logic: plain gates
        case (state)
            S0: next = x ? S1 : S0;
            S1: next = x ? S1 : S2;
            S2: next = x ? S3 : S0;
            S3: next = x ? S1 : S2;       // overlapping: the final 1 can start a new 101
            default: next = S0;
        endcase
    end

    assign y = (state == S3);             // Moore: output from the state alone
endmodule