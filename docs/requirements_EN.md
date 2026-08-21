# V.35 Phase-Measurement Subsystem — Requirements

Document revision: v1.2
RTL baseline: v1.0 (this documentation correction does not modify RTL)
Status: Faithful-version requirements frozen and RTL-verified
Date: 2026-08-20

## 1. Requirement classes

- **Baseline**: required and verified for the faithful version.
- **Implementation decision**: the legacy system permits more than one behavior, but implementation must choose one deterministic rule.
- **Candidate enhancement**: extended version only; must not alter faithful-version compatibility.
- **Open**: requires legacy source, target-device information, or engineer confirmation.

## 2. Environment and synchronization

| ID | Class | Requirement |
|---|---|---|
| REQ-ENV-001 | Baseline | All internal functional logic is clocked only by the 50 MHz reference clock. |
| REQ-ENV-002 | Baseline | Support V.35 receive-clock frequencies from 64 kHz to 2.048 MHz. |
| REQ-ENV-003 | Baseline | `v35_rclk` and `v35_data` use independent, identical two-stage synchronizers. |
| REQ-ENV-004 | Baseline | Synchronizer stage 1 may feed only stage 2. |
| REQ-ENV-005 | Baseline | Event detection compares stage-2 output with a history sample. |
| REQ-ENV-006 | Baseline | RCLK reports rising edges only; DATA reports either-polarity transitions. |
| REQ-ENV-007 | Baseline | Only discrete observable events are guaranteed; transitions folded between sample points need not be recovered. |
| REQ-ENV-008 | Open | Minimum input high/low times and minimum observable transition spacing. |
| REQ-ENV-009 | Baseline | No `sync_valid` port; each detector uses `detector_armed` to make its first post-reset sample a history baseline. |

## 3. CPU-controlled phase measurement

| ID | Class | Requirement |
|---|---|---|
| REQ-FUNC-001 | Baseline | While idle, accepted writes `1 -> 0` to `mem13[3]` produce one-cycle `measurement_start`; no start means no new published result. |
| REQ-FUNC-002 | Baseline | Every active-window `rclk_rise_evt` establishes a new origin and clears the phase count. |
| REQ-FUNC-003 | Baseline | With no DATA transition over multiple periods, every later RCLK rise replaces the old origin. |
| REQ-FUNC-004 | Baseline | A DATA event before any valid origin cannot produce a result. |
| REQ-FUNC-005 | Baseline | The first DATA transition after a valid origin captures the phase and completes the transaction. |
| REQ-FUNC-006 | Baseline | A completed result remains stable until read-clear or a new accepted start. |
| REQ-FUNC-007 | Baseline | An accepted new start clears `result_valid` immediately; the old numerical result may remain temporarily and be overwritten by completion. |
| REQ-FUNC-008 | Baseline | Control writes while busy are rejected atomically and cannot alter control or armed state. |

## 4. Counting and priority

| ID | Class | Requirement |
|---|---|---|
| REQ-COUNT-001 | Baseline | `phase_result = n_d - n_r` in 50 MHz cycles. |
| REQ-COUNT-002 | Baseline | Adjacent observed events return 1, corresponding to 20 ns. |
| REQ-COUNT-003 | Baseline | Same-cycle RCLK and DATA events return 0 using the current RCLK as origin. |
| REQ-COUNT-004 | Baseline | A new RCLK event has origin-update priority over normal count increment. |
| REQ-COUNT-005 | Baseline | A new-result capture has priority over an abnormal same-cycle read-clear. |
| REQ-COUNT-006 | Candidate enhancement | Detect or report saturation instead of relying on natural 10-bit wrap. |

## 5. Register interface

| ID | Class | Requirement |
|---|---|---|
| REQ-IF-001 | Baseline | `mem13_rdata[3]` exposes control state. |
| REQ-IF-002 | Baseline | `mem13_rdata[2]` exposes `result_valid`. |
| REQ-IF-003 | Baseline | `mem13_rdata[1:0]` exposes `phase_result[9:8]`. |
| REQ-IF-004 | Baseline | `mem14_rdata[7:0]` exposes `phase_result[7:0]`. |
| REQ-IF-005 | Baseline | `cpu_read_clear` clears valid state without erasing the stored numerical result. |
| REQ-IF-006 | Baseline | The top level exposes `cpu_read_clear`; it does not assume an unknown CPU bus handshake. |
| REQ-IF-007 | Open | Exact legacy addresses and bus timing. |

## 6. Reset and initialization

| ID | Class | Requirement |
|---|---|---|
| REQ-RST-001 | Baseline | Reset is synchronous to `clk_50m`. |
| REQ-RST-002 | Baseline | Reset clears synchronization state, detector history, measurement state, count, result, valid state, and register-control state. |
| REQ-RST-003 | Baseline | Reset has priority over normal events and cannot publish a result. |
| REQ-RST-004 | Baseline | Software must wait for synchronizers and detector histories to initialize before the first start; the current system test uses four cycles. |
| REQ-RST-005 | Baseline | Synchronizer-filling activity while idle must not create a CPU-visible result. |

## 7. CPU decision behavior

| ID | Class | Requirement |
|---|---|---|
| REQ-CPU-001 | Baseline | The CPU converts one result using `t = phase_result x 20 ns`. |
| REQ-CPU-002 | Baseline | The CPU interprets `t` relative to the current V.35 period `T`. |
| REQ-CPU-003 | Baseline | After power-up or a frequency change, the CPU collects 10 valid results and computes the mean phase. |
| REQ-CPU-004 | Baseline | Initial calibration selects falling for `0<t<T/4` or `3T/4<t<T`, and rising for `T/4<t<3T/4`. |
| REQ-CPU-005 | Baseline | During operation, the CPU obtains one result at 1 s intervals and uses the mean of three results for periodic calibration. |
| REQ-CPU-006 | Implementation decision | Periodic samples use non-overlapping batches; after every three results, software decides and starts a new batch. |
| REQ-CPU-007 | Baseline | The periodic table may select rising, select falling, or retain the current edge; retain regions cause no switch. |
| REQ-CPU-008 | Implementation decision | The undocumented intervals `4T/12<=t<=5T/12`, `7T/12<=t<=8T/12`, and all exact thresholds retain the current setting. |
| REQ-CPU-009 | Baseline | Multi-sample scheduling, statistics, and TDMoP configuration remain outside the CPLD RTL. |
| REQ-CPU-010 | Open | How frequency changes are detected and when the first periodic sample is taken. |

## 8. Error and enhancement boundary

| ID | Class | Requirement |
|---|---|---|
| REQ-ERR-001 | Baseline | Missing RCLK may wait indefinitely; no faithful-version timeout is reported. |
| REQ-ERR-002 | Baseline | With RCLK but no DATA transition, origins continue to update; no faithful-version timeout is reported. |
| REQ-ERR-003 | Candidate enhancement | Add missing-clock and missing-data timeout status. |
| REQ-ERR-004 | Candidate enhancement | Add `boundary_flag`, `multiple_toggle`, and explicit error status only in the extended version. |

## 9. Acceptance evidence

The following self-checking simulations have run successfully:

| Testbench | Result | Confirmed scope |
|---|---|---|
| `input_synchronizer_tb.sv` | `PASS`, exit 0 | Synchronous reset, two-stage propagation, stable input, narrow pulse between sample points. |
| `event_detector_tb.sv` | `PASS`, 15 checks | First-sample baseline, rising/falling/toggle detection, one-cycle outputs, no `sync_valid`. |
| `phase_measurement_tb.sv` | `PASS`, 12 checks | Start, origin waiting, phases 1 and 3, origin replacement, same-cycle 0, read-clear, restart, reset. |
| `register_interface_tb.sv` | `PASS`, 16 checks | Arm/start sequence, busy rejection, mapping, reset. |
| `adaptive_sampling_monitor_tb.sv` | `PASS`, 29 checks, exit 0 | End-to-end asynchronous input path, phase 1, phase 0, busy rejection, read-clear, final reset. |

`PASS` means the DUT met the expectations encoded in a testbench. Exit code 0 means the simulation process reported success. Neither proves the specification itself complete or every possible input covered.

## 10. Planned but not completed coverage

- Regression at 64 kHz, 2.048 MHz, and all nominal `N = 1..32` frequencies.
- Directed testing near 10-bit wrap.
- Long-duration missing-clock and missing-data stress.
- Validation of the implemented CPU reference model against continuous phase logs from real hardware.
- Target-device implementation, synchronizer attributes, board timing margin, and BER testing.
- Extended-version timeout, saturation, boundary, and multiple-toggle behavior.

## 11. CPU candidate-enhancement requirements

| ID | Class | Requirement |
|---|---|---|
| REQ-CPU-011 | Candidate enhancement | Treat phase as a circular quantity to prevent the `0/T` wrap from corrupting the representative phase. |
| REQ-CPU-012 | Candidate enhancement | Before publishing a circular decision, independently check circular concentration and normalized circular decision margin. |
| REQ-CPU-013 | Candidate enhancement | If initial-calibration confidence is insufficient, publish no new edge and enter retry or failure handling. |
| REQ-CPU-014 | Candidate enhancement | If periodic-calibration confidence is insufficient, retain the current edge. |
| REQ-CPU-015 | Open | Concentration threshold, margin threshold, maximum retries, and maximum acceptable switching delay require real measurements and product requirements. |
| REQ-CPU-016 | Boundary | The candidate CPU enhancement must not change the CPLD v1.0 single-result interface or value semantics. |
