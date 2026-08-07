`timescale 1ns/1ps

module event_detector_tb;

    logic clk_50m;
    logic rst_n;
    logic sync_in;
    logic toggle_evt;
    logic rise_evt;

    int checks;
    int failures;

    event_detector dut (
        .clk_50m    (clk_50m),
        .rst_n      (rst_n),
        .sync_in    (sync_in),
        .toggle_evt (toggle_evt),
        .rise_evt   (rise_evt)
    );

    initial clk_50m = 1'b0;
    always #10 clk_50m = ~clk_50m;

    task automatic check_outputs(
        input logic expected_toggle,
        input logic expected_rise,
        input logic expected_armed,
        input string test_name
    );
        checks++;
        #1;
        if ((toggle_evt !== expected_toggle) ||
            (rise_evt   !== expected_rise) ||
            (dut.detector_armed !== expected_armed)) begin
            failures++;
            $error("%s: expected toggle=%0b rise=%0b armed=%0b, got toggle=%0b rise=%0b armed=%0b",
                   test_name, expected_toggle, expected_rise, expected_armed,
                   toggle_evt, rise_evt, dut.detector_armed);
        end
    endtask

    task automatic drive_sample(
        input logic sample,
        input logic expected_toggle,
        input logic expected_rise,
        input logic expected_armed,
        input string test_name
    );
        @(negedge clk_50m);
        sync_in = sample;
        #1;
        check_outputs(expected_toggle, expected_rise, expected_armed, test_name);
        @(posedge clk_50m);
        #1;
    endtask

    initial begin
        checks     = 0;
        failures   = 0;
        rst_n      = 1'b0;
        sync_in    = 1'b0;

        $dumpfile("event_detector_tb.vcd");
        $dumpvars(0, event_detector_tb);

        // Synchronous reset clears history and masks event reporting.
        repeat (2) @(posedge clk_50m);
        @(negedge clk_50m);
        sync_in = 1'b1;
        check_outputs(1'b0, 1'b0, 1'b0, "reset masks events");

        // The first sample after reset establishes a baseline of one.
        @(negedge clk_50m);
        rst_n = 1'b1;
        check_outputs(1'b0, 1'b0, 1'b0, "startup remains disarmed");
        @(posedge clk_50m);
        #1;
        check_outputs(1'b0, 1'b0, 1'b1, "first sample is baseline");

        // Compare every subsequent sample with the preceding sample.
        drive_sample(1'b0, 1'b1, 1'b0, 1'b1, "falling transition");
        drive_sample(1'b0, 1'b0, 1'b0, 1'b1, "stable low");
        drive_sample(1'b1, 1'b1, 1'b1, 1'b1, "rising transition");
        drive_sample(1'b1, 1'b0, 1'b0, 1'b1, "stable high");
        drive_sample(1'b0, 1'b1, 1'b0, 1'b1, "second falling transition");
        drive_sample(1'b1, 1'b1, 1'b1, 1'b1, "second rising transition");
        drive_sample(1'b1, 1'b0, 1'b0, 1'b1, "event lasts one cycle only");

        // Reasserting reset immediately masks outputs; the next clock clears
        // history, and the first post-reset sample establishes a new baseline.
        @(negedge clk_50m);
        rst_n   = 1'b0;
        sync_in = 1'b0;
        check_outputs(1'b0, 1'b0, 1'b1, "reset immediately masks outputs");
        @(posedge clk_50m);
        #1;
        check_outputs(1'b0, 1'b0, 1'b0, "reset clears detector state");

        @(negedge clk_50m);
        rst_n   = 1'b1;
        sync_in = 1'b0;
        check_outputs(1'b0, 1'b0, 1'b0, "rearm starts without an event");
        @(posedge clk_50m);
        #1;
        check_outputs(1'b0, 1'b0, 1'b1, "post-reset sample is new baseline");
        drive_sample(1'b1, 1'b1, 1'b1, 1'b1, "detection resumes after rearming");

        if (failures == 0)
            $display("PASS: event_detector completed %0d checks", checks);
        else
            $fatal(1, "FAIL: event_detector had %0d failures in %0d checks",
                   failures, checks);

        $finish;
    end

endmodule
