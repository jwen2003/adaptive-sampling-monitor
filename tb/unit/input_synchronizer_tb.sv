`timescale 1ns/1ps

module input_synchronizer_tb;

    logic clk_50m;
    logic rst_n;
    logic async_in;
    logic sync_out;

    int checks;
    int failures;

    input_synchronizer dut (
        .clk_50m    (clk_50m),
        .rst_n      (rst_n),
        .async_in   (async_in),
        .sync_out   (sync_out)
    );

    initial clk_50m = 1'b0;
    always #10 clk_50m = ~clk_50m;

    task automatic check_state(
        input logic expected_ff1,
        input logic expected_ff2,
        input logic expected_out,
        input string test_name
    );
        checks++;
        #1;
        if ((dut.sync_ff1 !== expected_ff1) ||
            (dut.sync_ff2 !== expected_ff2) ||
            (sync_out     !== expected_out)) begin
            failures++;
            $error("%s: expected ff1=%0b ff2=%0b out=%0b, got ff1=%0b ff2=%0b out=%0b",
                   test_name,
                   expected_ff1, expected_ff2, expected_out,
                   dut.sync_ff1, dut.sync_ff2, sync_out);
        end
    endtask

    initial begin

        $dumpfile("input_synchronizer_tb.vcd");
        $dumpvars(0, input_synchronizer_tb);

        checks   = 0;
        failures = 0;
        rst_n    = 1'b0;
        async_in = 1'b0;

        // Synchronous reset clears both synchronizer stages.
        @(posedge clk_50m);
        check_state(1'b0, 1'b0, 1'b0, "reset clears synchronizer");

        // Changing async_in during reset must not change synchronized state.
        @(negedge clk_50m);
        async_in = 1'b1;
        @(posedge clk_50m);
        check_state(1'b0, 1'b0, 1'b0, "reset blocks high input");

        // The first edge after reset release fills only the first stage.
        @(negedge clk_50m);
        rst_n = 1'b1;
        @(posedge clk_50m);
        check_state(1'b1, 1'b0, 1'b0, "first fill edge");

        // The second edge transfers the sampled high level to the output.
        @(posedge clk_50m);
        check_state(1'b1, 1'b1, 1'b1, "second fill edge");

        // A stable high input remains high at the synchronized output.
        repeat (2) begin
            @(posedge clk_50m);
            check_state(1'b1, 1'b1, 1'b1, "stable high input");
        end

        // A new low level reaches sync_out on the edge after stage 1 captures
        // it: two observed edges including the capture edge.
        @(negedge clk_50m);
        async_in = 1'b0;
        @(posedge clk_50m);
        check_state(1'b0, 1'b1, 1'b1, "low captured by first stage");
        @(posedge clk_50m);
        check_state(1'b0, 1'b0, 1'b0, "low reaches synchronized output");

        // This pulse lies wholly between rising edges, so it is not sampled.
        // The contract does not claim every narrow pulse must be missed;
        // capture depends on pulse phase relative to the sampling clock.
        @(negedge clk_50m);
        #2 async_in = 1'b1;
        #4 async_in = 1'b0;
        @(posedge clk_50m);
        check_state(1'b0, 1'b0, 1'b0, "between-edge pulse is not sampled");
        @(posedge clk_50m);
        check_state(1'b0, 1'b0, 1'b0, "no delayed pulse appears");

        // Synchronous reset takes effect on the next rising edge.
        @(negedge clk_50m);
        async_in = 1'b1;
        rst_n    = 1'b0;
        @(posedge clk_50m);
        check_state(1'b0, 1'b0, 1'b0, "second reset clears state");

        // The data path again requires two rising edges to reach the output.
        @(negedge clk_50m);
        rst_n = 1'b1;
        @(posedge clk_50m);
        check_state(1'b1, 1'b0, 1'b0, "refill first edge");
        @(posedge clk_50m);
        check_state(1'b1, 1'b1, 1'b1, "refill second edge");

        if (failures == 0)
            $display("PASS: input_synchronizer completed %0d checks", checks);
        else
            $fatal(1, "FAIL: input_synchronizer had %0d failures in %0d checks",
                   failures, checks);

        $finish;
    end

endmodule
