`timescale 1ns/1ps

// Measures the number of 50 MHz clock intervals from the most recent
// synchronized V.35 receive-clock rising edge to the first synchronized data
// transition. The CPU starts one measurement transaction at a time.
//
// Faithful-version behavior:
// - A start pulse opens or restarts a measurement window.
// - Data transitions are ignored until a receive-clock origin is observed.
// - Every later receive-clock rising edge replaces the previous origin.
// - A data transition completes the transaction and latches one result.
// - Simultaneous clock and data events produce a result of zero.
// - A new start clears result_valid immediately; the previous result value
//   remains stored but is no longer valid.
// - A later completed measurement overwrites the previous result value.
// - A CPU read clears result_valid but leaves phase_result unchanged.
// - If result capture and cpu_read_clear coincide, capture has priority.
// - No timeout, saturation report, or boundary flag is implemented here.
// - rst_n is an active-low synchronous reset.

module phase_measurement (
    input  logic       clk_50m,
    input  logic       rst_n,
    input  logic       start,
    input  logic       rclk_rise_evt,
    input  logic       data_toggle_evt,
    input  logic       cpu_read_clear,
    output logic [9:0] phase_result,
    output logic       result_valid,
    output logic       busy
);

    typedef enum logic [1:0] {
        IDLE,
        WAIT_RCLK,
        WAIT_DATA
    } state_t;

    state_t state;
    logic [9:0] phase_count;
    logic       capture_result;
    logic [9:0] captured_value;

    // Capture intent is derived explicitly so that a newly captured result
    // can take priority over a simultaneous CPU read-clear request.
    always_comb begin
        capture_result = 1'b0;
        captured_value = 10'd0;

        if (!start) begin
            case (state)
                WAIT_RCLK: begin
                    if (rclk_rise_evt && data_toggle_evt) begin
                        capture_result = 1'b1;
                        captured_value = 10'd0;
                    end
                end

                WAIT_DATA: begin
                    if (rclk_rise_evt && data_toggle_evt) begin
                        capture_result = 1'b1;
                        captured_value = 10'd0;
                    end else if (data_toggle_evt) begin
                        // phase_count stores completed intervals before this
                        // edge. Including the current interval makes adjacent
                        // clock/data event cycles produce a result of one.
                        capture_result = 1'b1;
                        captured_value = phase_count + 10'd1;
                    end
                end

                default: begin
                    capture_result = 1'b0;
                    captured_value = 10'd0;
                end
            endcase
        end
    end

    assign busy = (state != IDLE);

    always_ff @(posedge clk_50m) begin
        if (!rst_n) begin
            state        <= IDLE;
            phase_count  <= 10'd0;
            phase_result <= 10'd0;
            result_valid <= 1'b0;
        end else begin
            // Read-clear applies unless this same edge captures a new result.
            if (cpu_read_clear && !capture_result)
                result_valid <= 1'b0;

            // A new start has priority over in-flight measurement events and
            // immediately invalidates any previous result. The stored result
            // value itself remains unchanged until the new capture completes.
            if (start) begin
                state        <= WAIT_RCLK;
                phase_count  <= 10'd0;
                result_valid <= 1'b0;
            end else begin
                case (state)
                    IDLE: begin
                        phase_count <= 10'd0;
                    end

                    WAIT_RCLK: begin
                        if (capture_result) begin
                            phase_result <= captured_value;
                            result_valid <= 1'b1;
                            phase_count  <= 10'd0;
                            state        <= IDLE;
                        end else if (rclk_rise_evt) begin
                            phase_count <= 10'd0;
                            state       <= WAIT_DATA;
                        end
                    end

                    WAIT_DATA: begin
                        if (capture_result) begin
                            phase_result <= captured_value;
                            result_valid <= 1'b1;
                            phase_count  <= 10'd0;
                            state        <= IDLE;
                        end else if (rclk_rise_evt) begin
                            // Replace the old origin when a new V.35 receive
                            // clock period begins without a data transition.
                            phase_count <= 10'd0;
                        end else begin
                            // Natural 10-bit wraparound matches the faithful
                            // version, which has no saturation diagnostics.
                            phase_count <= phase_count + 10'd1;
                        end
                    end

                    default: begin
                        state       <= IDLE;
                        phase_count <= 10'd0;
                    end
                endcase
            end
        end
    end

endmodule
