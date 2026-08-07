`timescale 1ns/1ps

// Two-stage synchronizer for a single-bit asynchronous level input.
//
// Contract:
// - async_in is asynchronous to clk_50m.
// - sync_out is the second-stage sample in the clk_50m domain.
// - sync_ff1 is intentionally not exposed to downstream logic.
// - Narrow pulses and multiple transitions between samples may be missed.
// - rst_n is an active-low synchronous reset in this first implementation.
//
// This module does not perform edge detection or detector arming. Those
// responsibilities belong to the downstream event detector.

module input_synchronizer (
    input  logic clk_50m,
    input  logic rst_n,
    input  logic async_in,
    output logic sync_out
);

    logic sync_ff1;  // First stage; reduces metastability propagation risk
    logic sync_ff2;  // Second stage; provides the synchronized output level

    always_ff @(posedge clk_50m) begin
        if (!rst_n) begin
            sync_ff1 <= 1'b0;
            sync_ff2 <= 1'b0;
        end else begin
            sync_ff1 <= async_in;
            sync_ff2 <= sync_ff1;
        end
    end

    assign sync_out = sync_ff2;
endmodule
