`timescale 1ns/1ps

module register_interface_tb;

    logic       clk_50m;
    logic       rst_n;
    logic       mem13_write;
    logic [7:0] mem13_wdata;
    logic       measurement_busy;
    logic       result_valid;
    logic [9:0] phase_result;
    logic       measurement_start;
    logic [7:0] mem13_rdata;
    logic [7:0] mem14_rdata;

    int checks;
    int failures;

    register_interface dut (
        .clk_50m           (clk_50m),
        .rst_n             (rst_n),
        .mem13_write       (mem13_write),
        .mem13_wdata       (mem13_wdata),
        .measurement_busy  (measurement_busy),
        .result_valid      (result_valid),
        .phase_result      (phase_result),
        .measurement_start (measurement_start),
        .mem13_rdata       (mem13_rdata),
        .mem14_rdata       (mem14_rdata)
    );

    initial clk_50m = 1'b0;
    always #10 clk_50m = ~clk_50m;

    task automatic drive_cycle(
        input logic       drive_write,
        input logic [7:0] drive_wdata,
        input logic       drive_busy
    );
        @(negedge clk_50m);
        mem13_write      = drive_write;
        mem13_wdata      = drive_wdata;
        measurement_busy = drive_busy;
        @(posedge clk_50m);
        #1;
    endtask

    task automatic check_outputs(
        input logic       expected_start,
        input logic [7:0] expected_mem13,
        input logic [7:0] expected_mem14,
        input string      test_name
    );
        checks++;
        if ((measurement_start !== expected_start) ||
            (mem13_rdata       !== expected_mem13) ||
            (mem14_rdata       !== expected_mem14)) begin
            failures++;
            $error("%s: expected start=%0b mem13=0x%02h mem14=0x%02h, got start=%0b mem13=0x%02h mem14=0x%02h",
                   test_name, expected_start, expected_mem13, expected_mem14,
                   measurement_start, mem13_rdata, mem14_rdata);
        end
    endtask

    initial begin
        $dumpfile("register_interface_tb.vcd");
        $dumpvars(0, register_interface_tb);

        checks            = 0;
        failures          = 0;
        rst_n             = 1'b0;
        mem13_write       = 1'b0;
        mem13_wdata       = 8'h00;
        measurement_busy  = 1'b0;
        result_valid      = 1'b0;
        phase_result      = 10'h000;

        // Reset starts unarmed, clears the visible control bit, and emits no
        // start. A direct zero write after reset must therefore do nothing.
        drive_cycle(1'b0, 8'h00, 1'b0);
        check_outputs(1'b0, 8'h00, 8'h00, "reset clears interface state");
        rst_n = 1'b1;
        drive_cycle(1'b1, 8'h00, 1'b0);
        check_outputs(1'b0, 8'h00, 8'h00, "zero write while unarmed is ignored");

        // Only bit 3 is writable. Other write-data bits cannot modify the
        // read-only result fields, and repeated one writes merely remain armed.
        phase_result = 10'b10_1010_0101;
        result_valid = 1'b1;
        #1;
        check_outputs(1'b0, 8'b0000_0110, 8'hA5,
                      "read mapping exposes valid result before control write");
        drive_cycle(1'b1, 8'hFF, 1'b0);
        check_outputs(1'b0, 8'b0000_1110, 8'hA5,
                      "one write arms and only updates control bit");
        drive_cycle(1'b1, 8'h08, 1'b0);
        check_outputs(1'b0, 8'b0000_1110, 8'hA5,
                      "repeated one write does not start measurement");

        // The first armed zero produces one full-cycle pulse and consumes the
        // arm. The old result bits remain visible; validity is owned upstream.
        drive_cycle(1'b1, 8'h00, 1'b0);
        check_outputs(1'b1, 8'b0000_0110, 8'hA5,
                      "armed zero emits one start pulse");
        result_valid = 1'b0;
        #1;
        check_outputs(1'b1, 8'b0000_0010, 8'hA5,
                      "invalid state retains old result bits");
        drive_cycle(1'b0, 8'h00, 1'b1);
        check_outputs(1'b0, 8'b0000_0010, 8'hA5,
                      "start pulse deasserts after one cycle");
        drive_cycle(1'b1, 8'h00, 1'b0);
        check_outputs(1'b0, 8'b0000_0010, 8'hA5,
                      "continued zero does not retrigger");

        // Busy rejects an entire write atomically: neither the visible bit nor
        // the armed state changes. First verify a rejected one cannot arm.
        drive_cycle(1'b1, 8'h08, 1'b1);
        check_outputs(1'b0, 8'b0000_0010, 8'hA5,
                      "busy rejects one write and visible update");
        drive_cycle(1'b1, 8'h00, 1'b0);
        check_outputs(1'b0, 8'b0000_0010, 8'hA5,
                      "rejected one did not leave interface armed");

        // An arm accepted before busy remains intact across rejected writes.
        drive_cycle(1'b1, 8'h08, 1'b0);
        check_outputs(1'b0, 8'b0000_1010, 8'hA5,
                      "idle one write arms next measurement");
        drive_cycle(1'b1, 8'h00, 1'b1);
        check_outputs(1'b0, 8'b0000_1010, 8'hA5,
                      "busy rejects zero and preserves prior arm");
        drive_cycle(1'b1, 8'h00, 1'b0);
        check_outputs(1'b1, 8'b0000_0010, 8'hA5,
                      "zero succeeds after busy clears");

        // A write sampled on a completion edge still sees the old busy=1 and
        // is rejected. It is not accepted retroactively when busy falls.
        drive_cycle(1'b0, 8'h00, 1'b0);
        drive_cycle(1'b1, 8'h08, 1'b1);
        measurement_busy = 1'b0;
        #1;
        check_outputs(1'b0, 8'b0000_0010, 8'hA5,
                      "completion-edge write is rejected using old busy");
        drive_cycle(1'b1, 8'h00, 1'b0);
        check_outputs(1'b0, 8'b0000_0010, 8'hA5,
                      "completion-edge rejection does not arm later zero");

        // Synchronous reset has priority over writes and busy state.
        @(negedge clk_50m);
        rst_n            = 1'b0;
        mem13_write      = 1'b1;
        mem13_wdata      = 8'h08;
        measurement_busy = 1'b1;
        @(posedge clk_50m);
        #1;
        check_outputs(1'b0, 8'b0000_0010, 8'hA5,
                      "reset clears control state but preserves upstream result");

        if (failures == 0)
            $display("PASS: register_interface completed %0d checks", checks);
        else
            $fatal(1, "FAIL: register_interface had %0d failures in %0d checks",
                   failures, checks);

        $finish;
    end

endmodule
