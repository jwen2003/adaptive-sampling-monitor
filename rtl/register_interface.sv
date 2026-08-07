`timescale 1ns/1ps

// Adapts the legacy mem13 control-bit protocol to the phase measurement
// core's one-cycle start pulse. Only mem13[3] is writable; the remaining
// fields are read-only views of the measurement result.
//
// Control protocol:
// - An accepted write of mem13[3] = 1 arms one future measurement.
// - The first accepted write of mem13[3] = 0 while armed emits start for one
//   clk_50m cycle and consumes the armed state.
// - Further zero writes do not retrigger until another one write is accepted.
// - All control writes are rejected while measurement_busy is high. They do
//   not update either the CPU-visible control bit or the internal armed state.
// - rst_n is an active-low synchronous reset.

module register_interface (
    input  logic       clk_50m,
    input  logic       rst_n,

    input  logic       mem13_write,
    input  logic [7:0] mem13_wdata,

    input  logic       measurement_busy,
    input  logic       result_valid,
    input  logic [9:0] phase_result,

    output logic       measurement_start,
    output logic [7:0] mem13_rdata,
    output logic [7:0] mem14_rdata
);

    logic mem13_control;
    logic start_armed;

    // These outputs continuously mirror the current stored state. Bus timing
    // and read handshaking belong to a future outer bus adapter.
    assign mem13_rdata = {
        4'b0000,
        mem13_control,
        result_valid,
        phase_result[9:8]
    };

    assign mem14_rdata = phase_result[7:0];

    always_ff @(posedge clk_50m) begin
        if (!rst_n) begin
            mem13_control   <= 1'b0;
            start_armed     <= 1'b0;
            measurement_start <= 1'b0;
        end else begin
            // Default deassertion makes every accepted start exactly one
            // reference-clock cycle wide.
            measurement_start <= 1'b0;

            if (mem13_write && !measurement_busy) begin
                mem13_control <= mem13_wdata[3];

                if (mem13_wdata[3]) begin
                    start_armed <= 1'b1;
                end else if (start_armed) begin
                    start_armed       <= 1'b0;
                    measurement_start <= 1'b1;
                end
            end
        end
    end

endmodule
