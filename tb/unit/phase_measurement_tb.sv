`timescale 1ns/1ps

module phase_measurement_tb;

    logic       clk_50m;
    logic       rst_n;
    logic       start;
    logic       rclk_rise_evt;
    logic       data_toggle_evt;
    logic       cpu_read_clear;
    logic [9:0] phase_result;
    logic       result_valid;
    logic       busy;

    int checks;
    int failures;

    phase_measurement dut (
        .clk_50m         (clk_50m),
        .rst_n           (rst_n),
        .start           (start),
        .rclk_rise_evt   (rclk_rise_evt),
        .data_toggle_evt (data_toggle_evt),
        .cpu_read_clear  (cpu_read_clear),
        .phase_result    (phase_result),
        .result_valid    (result_valid),
        .busy            (busy)
    );

    initial clk_50m = 1'b0;
    always #10 clk_50m = ~clk_50m;

    task automatic drive_cycle(
        input logic drive_start,
        input logic drive_rclk,
        input logic drive_data,
        input logic drive_clear
    );
        @(negedge clk_50m);
        start           = drive_start;
        rclk_rise_evt   = drive_rclk;
        data_toggle_evt = drive_data;
        cpu_read_clear  = drive_clear;
        @(posedge clk_50m);
        #1;
    endtask

    task automatic check_state(
        input logic       expected_busy,
        input logic       expected_valid,
        input logic [9:0] expected_result,
        input string      test_name
    );
        checks++;
        if ((busy         !== expected_busy)  ||
            (result_valid !== expected_valid) ||
            (phase_result !== expected_result)) begin
            failures++;
            $error("%s: expected busy=%0b valid=%0b result=%0d, got busy=%0b valid=%0b result=%0d",
                   test_name, expected_busy, expected_valid, expected_result,
                   busy, result_valid, phase_result);
        end
    endtask

    initial begin
        $dumpfile("phase_measurement_tb.vcd");
        $dumpvars(0, phase_measurement_tb);

        checks          = 0;
        failures        = 0;
        rst_n           = 1'b0;
        start           = 1'b0;
        rclk_rise_evt   = 1'b0;
        data_toggle_evt = 1'b0;
        cpu_read_clear  = 1'b0;

        // Synchronous reset clears all CPU-visible state.
        drive_cycle(1'b0, 1'b0, 1'b0, 1'b0);
        check_state(1'b0, 1'b0, 10'd0, "reset clears the module");

        rst_n = 1'b1;

        // Events before start must not publish a result.
        drive_cycle(1'b0, 1'b1, 1'b1, 1'b0);
        check_state(1'b0, 1'b0, 10'd0, "events before start are ignored");

        // Data before the first receive-clock origin is ignored.
        drive_cycle(1'b1, 1'b0, 1'b0, 1'b0);
        check_state(1'b1, 1'b0, 10'd0, "start opens a measurement window");
        drive_cycle(1'b0, 1'b0, 1'b1, 1'b0);
        check_state(1'b1, 1'b0, 10'd0, "data before origin is ignored");

        // Adjacent receive-clock and data event cycles produce one.
        drive_cycle(1'b0, 1'b1, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b0, 1'b1, 1'b0);
        check_state(1'b0, 1'b1, 10'd1, "adjacent event cycles produce one");

        // A valid result remains stable until read or a later capture.
        drive_cycle(1'b0, 1'b0, 1'b0, 1'b0);
        check_state(1'b0, 1'b1, 10'd1, "unread result remains stable");
        drive_cycle(1'b0, 1'b0, 1'b0, 1'b1);
        check_state(1'b0, 1'b0, 10'd1, "CPU read clears only the valid flag");

        // A multi-cycle phase measurement uses the documented n_d - n_r rule.
        drive_cycle(1'b1, 1'b0, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b1, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b0, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b0, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b0, 1'b1, 1'b0);
        check_state(1'b0, 1'b1, 10'd3, "three-cycle phase is measured correctly");

        // Restarting with an unread result immediately clears the old valid
        // flag, while the stored result value remains unchanged until capture.
        drive_cycle(1'b1, 1'b0, 1'b0, 1'b0);
        check_state(1'b1, 1'b0, 10'd3, "restart invalidates unread old result");
        drive_cycle(1'b0, 1'b1, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b0, 1'b0, 1'b0);

        // A newer receive-clock event replaces the previous origin.
        drive_cycle(1'b0, 1'b1, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b0, 1'b1, 1'b0);
        check_state(1'b0, 1'b1, 10'd1, "new origin replaces old origin and result");

        // Simultaneous clock and data events explicitly produce zero.
        drive_cycle(1'b1, 1'b0, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b1, 1'b1, 1'b0);
        check_state(1'b0, 1'b1, 10'd0, "same-cycle events produce zero");

        // Capture wins over an abnormal simultaneous read-clear request.
        drive_cycle(1'b1, 1'b0, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b1, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b0, 1'b1, 1'b1);
        check_state(1'b0, 1'b1, 10'd1, "new capture wins over read clear");

        // A new start restarts an in-flight transaction and waits for a new
        // receive-clock origin rather than using the old one.
        drive_cycle(1'b1, 1'b0, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b1, 1'b0, 1'b0);
        drive_cycle(1'b1, 1'b0, 1'b0, 1'b0);
        drive_cycle(1'b0, 1'b0, 1'b1, 1'b0);
        check_state(1'b1, 1'b0, 10'd1, "restart discards the in-flight origin");
        drive_cycle(1'b0, 1'b1, 1'b1, 1'b0);
        check_state(1'b0, 1'b1, 10'd0, "restarted transaction completes from new origin");

        // Reset has priority while a result is valid.
        @(negedge clk_50m);
        rst_n = 1'b0;
        start = 1'b1;
        rclk_rise_evt = 1'b1;
        data_toggle_evt = 1'b1;
        cpu_read_clear = 1'b1;
        @(posedge clk_50m);
        #1;
        check_state(1'b0, 1'b0, 10'd0, "reset has highest priority");

        if (failures == 0)
            $display("PASS: phase_measurement completed %0d checks", checks);
        else
            $fatal(1, "FAIL: phase_measurement had %0d failures in %0d checks",
                   failures, checks);

        $finish;
    end

endmodule
