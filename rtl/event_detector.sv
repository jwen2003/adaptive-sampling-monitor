`timescale 1ns/1ps

// Event detector for one synchronized level input.
//
// Contract:
// - sync_in must already be synchronized to clk_50m.
// - The first sample after reset is released establishes the history baseline
//   and produces no event.
// - Once armed, toggle_evt reports differing adjacent samples and rise_evt
//   reports the 0-to-1 subset. Both are combinational one-cycle indications.
// - Transitions before arming, or transitions not visible in the synchronized
//   sample sequence, are intentionally not reported.
// - rst_n is an active-low synchronous reset.

module event_detector (
    input  logic clk_50m,
    input  logic rst_n,
    input  logic sync_in,
    output logic toggle_evt,
    output logic rise_evt
);

    logic sync_in_d;
    logic detector_armed;

    always_ff @(posedge clk_50m) begin
        if (!rst_n) begin
            sync_in_d      <= 1'b0;
            detector_armed <= 1'b0;
        end else if (!detector_armed) begin
            // Use the first post-reset sample only as the comparison baseline.
            sync_in_d      <= sync_in;
            detector_armed <= 1'b1;
        end else begin
            // Retain the current sample for comparison during the next cycle.
            sync_in_d <= sync_in;
        end
    end

    always_comb begin
        // Reset and startup arming both suppress event reporting.
        toggle_evt = rst_n & detector_armed & (sync_in ^ sync_in_d);
        rise_evt   = rst_n & detector_armed &  sync_in & ~sync_in_d;
    end

endmodule
