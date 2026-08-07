`timescale 1ns/1ps

module adaptive_sampling_monitor_tb;

    logic       clk_50m;
    logic       rst_n;
    logic       rclk_async;
    logic       data_async;
    logic       mem13_write;
    logic [7:0] mem13_wdata;
    logic       cpu_read_clear;
    logic [7:0] mem13_rdata;
    logic [7:0] mem14_rdata;

    int checks;
    int failures;

    adaptive_sampling_monitor dut (
        .clk_50m      (clk_50m),
        .rst_n        (rst_n),
        .rclk_async   (rclk_async),
        .data_async   (data_async),
        .mem13_write  (mem13_write),
        .mem13_wdata  (mem13_wdata),
        .cpu_read_clear(cpu_read_clear),
        .mem13_rdata  (mem13_rdata),
        .mem14_rdata  (mem14_rdata)
    );

    initial clk_50m = 1'b0;
    always #10 clk_50m = ~clk_50m;

    task automatic check_bit(
        input logic  actual,
        input logic  expected,
        input string test_name
    );
        checks++;
        if (actual !== expected) begin
            failures++;
            $error("%s: expected %0b, got %0b", test_name, expected, actual);
        end
    endtask

    task automatic check_byte(
        input logic [7:0] actual,
        input logic [7:0] expected,
        input string      test_name
    );
        checks++;
        if (actual !== expected) begin
            failures++;
            $error("%s: expected 0x%02h, got 0x%02h",
                   test_name, expected, actual);
        end
    endtask

    task automatic write_mem13(input logic control_value);
        @(negedge clk_50m);
        mem13_wdata = {4'b0000, control_value, 3'b000};
        mem13_write = 1'b1;
        @(posedge clk_50m);
        #1;
        @(negedge clk_50m);
        mem13_write = 1'b0;
        mem13_wdata = 8'h00;
    endtask

    task automatic start_measurement;
        write_mem13(1'b1);
        #1;
        check_bit(mem13_rdata[3], 1'b1, "write one sets control bit");

        write_mem13(1'b0);
        #1;
        check_bit(dut.measurement_start, 1'b1,
                  "accepted one-to-zero sequence emits start");

        @(posedge clk_50m);
        #1;
        check_bit(dut.measurement_start, 1'b0,
                  "measurement_start lasts one cycle");
        check_bit(dut.measurement_busy, 1'b1,
                  "measurement core enters busy state");
    endtask

    task automatic wait_for_result(input int max_cycles);
        int cycle;
        cycle = 0;
        while (!dut.result_valid && cycle < max_cycles) begin
            @(posedge clk_50m);
            #1;
            cycle++;
        end
        checks++;
        if (!dut.result_valid) begin
            failures++;
            $error("result_valid did not assert within %0d cycles", max_cycles);
        end
    endtask

    initial begin
        checks         = 0;
        failures       = 0;
        rst_n          = 1'b0;
        rclk_async     = 1'b0;
        data_async     = 1'b0;
        mem13_write    = 1'b0;
        mem13_wdata    = 8'h00;
        cpu_read_clear = 1'b0;

        $dumpfile("adaptive_sampling_monitor_tb.vcd");
        $dumpvars(0, adaptive_sampling_monitor_tb);

        // Synchronous reset clears every stored state in the integrated path.
        repeat (2) @(posedge clk_50m);
        #1;
        check_byte(mem13_rdata, 8'h00, "reset clears mem13 readback");
        check_byte(mem14_rdata, 8'h00, "reset clears mem14 readback");
        check_bit(dut.measurement_busy, 1'b0, "reset leaves measurement idle");

        // Release reset and allow both synchronizers and both event detectors
        // to establish their common low baseline.
        @(negedge clk_50m);
        rst_n = 1'b1;
        repeat (4) @(posedge clk_50m);
        #1;
        check_bit(dut.u_rclk_event_detector.detector_armed, 1'b1,
                  "RCLK detector establishes baseline");
        check_bit(dut.u_data_event_detector.detector_armed, 1'b1,
                  "DATA detector establishes baseline");

        // Transaction 1: make the synchronized DATA event follow the RCLK
        // event by one clk_50m cycle. The faithful counter must report one.
        start_measurement();

        // A control write attempted while busy is rejected atomically.
        write_mem13(1'b1);
        #1;
        check_byte(mem13_rdata, 8'h00, "busy write leaves control and result zero");
        check_bit(dut.u_register_interface.start_armed, 1'b0,
                  "busy write does not arm another start");

        @(negedge clk_50m);
        rclk_async = 1'b1;
        @(negedge clk_50m);
        data_async = 1'b1;

        wait_for_result(10);
        check_bit(dut.measurement_busy, 1'b0,
                  "first capture returns measurement to idle");
        check_byte(mem13_rdata, 8'h04,
                   "phase one sets valid with zero result high bits");
        check_byte(mem14_rdata, 8'h01, "adjacent events produce phase one");

        // CPU read-clear removes only validity; the stored result remains.
        @(negedge clk_50m);
        cpu_read_clear = 1'b1;
        @(posedge clk_50m);
        #1;
        cpu_read_clear = 1'b0;
        check_byte(mem13_rdata, 8'h00, "read-clear removes result_valid");
        check_byte(mem14_rdata, 8'h01, "read-clear preserves stored result");

        // Return both asynchronous inputs low and wait until the complete
        // synchronization/detection path has adopted that idle baseline.
        @(negedge clk_50m);
        rclk_async = 1'b0;
        data_async = 1'b0;
        repeat (4) @(posedge clk_50m);

        // Transaction 2: simultaneous synchronized RCLK and DATA events while
        // waiting for the first RCLK must capture a phase value of zero.
        start_measurement();
        check_byte(mem14_rdata, 8'h01,
                   "new start invalidates but preserves old result value");
        check_bit(mem13_rdata[2], 1'b0,
                  "new start keeps previous result invalid");

        @(negedge clk_50m);
        rclk_async = 1'b1;
        data_async = 1'b1;

        wait_for_result(10);
        check_byte(mem13_rdata, 8'h04,
                   "simultaneous capture sets valid for zero result");
        check_byte(mem14_rdata, 8'h00,
                   "simultaneous RCLK and DATA events produce phase zero");

        // A full reset at the end proves that integrated state can be cleared
        // after completed traffic, not only at time zero.
        @(negedge clk_50m);
        rst_n = 1'b0;
        @(posedge clk_50m);
        #1;
        check_byte(mem13_rdata, 8'h00, "final reset clears mem13 state");
        check_byte(mem14_rdata, 8'h00, "final reset clears phase result");
        check_bit(dut.measurement_busy, 1'b0, "final reset clears busy");

        if (failures == 0)
            $display("PASS: adaptive_sampling_monitor completed %0d checks",
                     checks);
        else
            $fatal(1,
                   "FAIL: adaptive_sampling_monitor had %0d failures in %0d checks",
                   failures, checks);

        $finish;
    end

endmodule
