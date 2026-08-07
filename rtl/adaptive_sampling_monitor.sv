`timescale 1ns/1ps

// Top-level integration for the faithful V.35 phase-measurement version.
//
// The external V.35 receive clock and data inputs are synchronized into the
// 50 MHz domain through identical two-stage paths. A shared validity pipeline
// prevents the synchronizer fill sequence after reset from being interpreted
// as a real input event.
//
// cpu_read_clear is intentionally supplied by an outer CPU/bus adapter. This
// module does not invent read timing or handshaking that is absent from the
// available legacy interface definition.

module adaptive_sampling_monitor (
    input  logic       clk_50m,
    input  logic       rst_n,

    input  logic       rclk_async,
    input  logic       data_async,

    input  logic       mem13_write,
    input  logic [7:0] mem13_wdata,
    input  logic       cpu_read_clear,

    output logic [7:0] mem13_rdata,
    output logic [7:0] mem14_rdata
);

    logic       rclk_sync;
    logic       data_sync;

    logic       rclk_rise_evt;
    logic       data_toggle_evt;

    logic       measurement_start;
    logic       measurement_busy;
    logic       result_valid;
    logic [9:0] phase_result;

    // Both synchronizers have identical structure and reset behavior so the
    // top level does not deliberately skew the measured clock/data relation.
    input_synchronizer u_rclk_synchronizer (
        .clk_50m (clk_50m),
        .rst_n   (rst_n),
        .async_in(rclk_async),
        .sync_out(rclk_sync)
    );

    input_synchronizer u_data_synchronizer (
        .clk_50m (clk_50m),
        .rst_n   (rst_n),
        .async_in(data_async),
        .sync_out(data_sync)
    );

    // Wait for both stages of both identical synchronizers to be filled.
    // The event detectors then use their own first valid sample as a baseline.
    event_detector u_rclk_event_detector (
        .clk_50m   (clk_50m),
        .rst_n     (rst_n),
        .sync_in   (rclk_sync),
        .toggle_evt(),
        .rise_evt  (rclk_rise_evt)
    );

    event_detector u_data_event_detector (
        .clk_50m   (clk_50m),
        .rst_n     (rst_n),
        .sync_in   (data_sync),
        .toggle_evt(data_toggle_evt),
        .rise_evt  ()
    );

    phase_measurement u_phase_measurement (
        .clk_50m        (clk_50m),
        .rst_n          (rst_n),
        .start          (measurement_start),
        .rclk_rise_evt  (rclk_rise_evt),
        .data_toggle_evt(data_toggle_evt),
        .cpu_read_clear (cpu_read_clear),
        .phase_result   (phase_result),
        .result_valid   (result_valid),
        .busy           (measurement_busy)
    );

    register_interface u_register_interface (
        .clk_50m          (clk_50m),
        .rst_n            (rst_n),
        .mem13_write      (mem13_write),
        .mem13_wdata      (mem13_wdata),
        .measurement_busy (measurement_busy),
        .result_valid     (result_valid),
        .phase_result     (phase_result),
        .measurement_start(measurement_start),
        .mem13_rdata      (mem13_rdata),
        .mem14_rdata      (mem14_rdata)
    );

endmodule
