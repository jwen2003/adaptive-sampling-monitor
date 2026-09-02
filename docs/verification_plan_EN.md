# V.35 Phase-Measurement Subsystem — Verification Plan and v1.0 Results

Document revision: v1.2
RTL baseline: v1.0 (this documentation correction does not modify RTL)
Status: Core faithful-version tests completed; planned coverage identified separately
Date: 2026-08-20

## 1. Verification objective

Verify that the faithful RTL implements the frozen discrete measurement contract, including synchronization structure, event formation, CPU start protocol, latest-origin counting, deterministic same-cycle behavior, result mapping, restart invalidation, read-clear, and synchronous reset.

Digital simulation does not prove metastability probability, board-level margin, bit-error rate, or the suitability of candidate CPU thresholds for a real product.

## 2. Frozen verification contract

- An accepted `mem13[3]` write `1 -> 0` emits one start pulse.
- Writes while busy are rejected atomically.
- Every active RCLK rise replaces the phase origin.
- The first DATA transition after an origin completes the transaction.
- Adjacent observed cycles produce 1; same-cycle events produce 0.
- A new start invalidates an unread old result immediately.
- Read-clear clears valid state but preserves result bits.
- A new capture wins over abnormal same-cycle read-clear.
- Reset is synchronous.
- No faithful-version timeout or multi-sample averaging exists.

## 3. Verification layers

| Layer | Testbench | Purpose |
|---|---|---|
| Synchronizer | `tb/unit/input_synchronizer_tb.sv` | Two-stage propagation, reset, stable input, and unobservable narrow pulses. |
| Event detector | `tb/unit/event_detector_tb.sv` | Baseline establishment, rise/fall/toggle behavior, one-cycle events. |
| Phase core | `tb/unit/phase_measurement_tb.sv` | Exact event-cycle control, counting, origin replacement, same-cycle 0, restart, read-clear. |
| Register interface | `tb/unit/register_interface_tb.sv` | Arm/start protocol, busy rejection, and result mapping. |
| Integration | `tb/adaptive_sampling_monitor_tb.sv` | Asynchronous inputs through synchronization, measurement, and CPU-visible registers. |

## 4. Independent reference rule

The scoreboard rule is based on event indices rather than copying the DUT counter update code:

$$
C_{\mathrm{phase}} = n_d - n_r
$$

Same-cycle events return 0; adjacent cycles return 1; a new RCLK replaces `n_r`; DATA without a valid `n_r` produces no result.

## 5. Deterministic test catalog

### Phase and origin

| ID | Scenario | Expected |
|---|---|---|
| TC-PHASE-001 | DATA one cycle after origin | Result 1. |
| TC-PHASE-002 | DATA four cycles after origin | Result 4. |
| TC-PHASE-003 | DATA before any origin | No valid result. |
| TC-PHASE-004/005 | DATA rising/falling transition | Either polarity can complete measurement. |
| TC-CROSS-001 | One empty receive-clock period | Next RCLK replaces origin without error. |
| TC-CROSS-002 | Several empty periods then DATA | Result is relative to latest origin. |
| TC-CROSS-003/004 | Long missing DATA or RCLK | Wait without faithful-version timeout. |

### Same-cycle and priority

| ID | Scenario | Expected |
|---|---|---|
| TC-SAME-001 | RCLK and DATA together without prior origin | Capture 0. |
| TC-SAME-002 | RCLK and DATA together with an old origin | Current origin wins; capture 0. |
| TC-SAME-003 | Reset with normal event | Reset wins; no result. |
| TC-SAME-004 | Capture with read-clear | New capture wins and remains valid. |

### Interface and reset

| ID | Scenario | Expected |
|---|---|---|
| TC-IF-001 | Completed result not read | Value and valid state hold. |
| TC-IF-002 | CPU read-clear | Clear valid only. |
| TC-IF-003 | Result after prior read-clear | New result becomes valid. |
| TC-IF-004 | Restart with unread result | Invalidate immediately; preserve old bits temporarily; later overwrite. |
| TC-IF-005 | Input events without start | No published result. |
| TC-IF-006 | One-cycle start | Exactly one transaction. |
| TC-RST-001..003 | Reset in waiting/counting/valid states | Clear state and cancel transaction. |
| TC-RST-004/005 | Reset release with low/high inputs | Initialize before start; no CPU-visible filling result. |

### Synchronization and frequency

The plan includes stable-input behavior, RCLK rise-only detection, DATA either-polarity detection, one-cycle pulses, and allowance for a one-cycle observation shift near a sampling boundary. Frequency regression is planned at 64 kHz, 2.048 MHz, and nominal $N = 1,\ldots,32$ points.

## 6. Assertion intent

- Reset implies `result_valid=0`.
- Event outputs never remain high for more than one cycle.
- Only an RCLK event establishes or replaces an origin.
- Same-cycle events produce 0.
- DATA requires a valid origin.
- Result holds without read-clear or restart.
- Read-clear invalidates unless a new capture occurs in the same cycle.
- Accepted start invalidates the old result until the next capture.
- Waiting without timeout never enters an implicit error state.

These are verification intentions; not every item is currently encoded as a standalone SystemVerilog Assertion.

## 7. v1.0 results

| Testbench | Actual result | Confirmed scope |
|---|---|---|
| `input_synchronizer_tb.sv` | `PASS`, exit 0 | Reset, two-stage propagation, stable input, narrow inter-sample pulse. |
| `event_detector_tb.sv` | `PASS`, 15 checks | Initial baseline, rises/falls/toggles, one-cycle output, final interface without `sync_valid`. |
| `phase_measurement_tb.sv` | `PASS`, 12 checks | Start, origin wait, results 1 and 3, latest origin, same-cycle 0, read-clear, restart, reset. |
| `register_interface_tb.sv` | `PASS`, 16 checks | Arm/start, busy rejection, mapping, reset. |
| `adaptive_sampling_monitor_tb.sv` | `PASS`, 29 checks, exit 0 | End-to-end phase 1 and 0, busy rejection, mapping, read-clear, final reset. |

Key waveforms were manually inspected. `PASS` establishes agreement with encoded expectations; exit 0 establishes successful process completion. Neither alone proves complete correctness.

## 8. Coverage not yet completed

- All 32 nominal V.35 frequencies and endpoint regression.
- Directed near-wrap test for the 10-bit count.
- Long missing-clock and missing-data stress.
- Validation of the implemented CPU reference model using continuous phase logs from real hardware.
- Target-device synthesis, place-and-route, synchronizer attributes, and timing analysis.
- Board measurement and BER validation.
- Extended-version timeout, saturation, `boundary_flag`, and `multiple_toggle` behavior.

These items must remain labeled as plans rather than v1.0 results.

## 9. Faithful-version exit interpretation

The current milestone is accepted as: implemented RTL plus self-checking unit/integration simulations that pass the frozen core scenarios, with deterministic same-cycle semantics, latest-origin behavior, restart invalidation, read-clear, and reset confirmed.

It is not accepted as proof of analog correctness, exhaustive frequency coverage, or production readiness.

## 10. CPU decision reference tests

The executable CPU model verifies that:

1. initial calibration publishes no decision before 10 valid results;
2. the 10-sample statistic follows the $T/4$ and $3T/4$ initial regions;
3. periodic sampling uses 1 s intervals and non-overlapping batches of exactly three results;
4. periodic decisions select rising, select falling, or retain the current edge according to the historical table;
5. undocumented gaps and exact thresholds retain the current setting;
6. a completed three-sample batch is cleared rather than becoming a sliding window;
7. invalid results do not enter a batch, and a frequency change discards partial history;
8. directed $0/T$ distributions expose the physical error of an ordinary arithmetic mean.

The first historical-algorithm test set contains 11 tests, all passing. The complete Python suite now contains 33 passing tests and additionally covers circular mean, concentration, ordinary and circular decision margins, threshold sweeps, guarded final actions, and dynamic tracking.

## 11. CPU algorithm scenario status

Covered scenarios include stable phase, $0/T$ wrap, one distant sample, wide dispersion, opposite bimodality, high concentration with low margin, repeated threshold motion, slow crossing, fast jump, noisy crossing, and a transient crossing followed by retreat.

The exploratory gate uses concentration at least `0.9` and normalized circular margin at least `0.025`. Passing these tests proves consistency with the reconstructed and exploratory rules only. It does not establish that these thresholds improve real-hardware BER or satisfy product response-time requirements.
