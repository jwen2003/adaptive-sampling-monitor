# V.35 Phase-Measurement Subsystem — Timing Behavior

Version: v1.0
Status: Faithful-version cycle semantics frozen and tested
Date: 2026-08-07

## 1. Timing model

All functional decisions occur on rising edges of `clk_50m`; one cycle is 20 ns. `rclk_async` and `data_async` are observations, never functional clocks. Each passes through an identical two-stage synchronizer and then an event detector with a history register.

The measured value is:

$$
C_{phase}=n_d-n_r,\qquad t=C_{phase}\times20\text{ ns}
$$

`n_r` is the cycle of the most recent observable RCLK rising event in the active window; `n_d` is the cycle of the first subsequent observable DATA transition.

## 2. Reset release

Reset is synchronous and active low in the current RTL. While `rst_n=0`, all state is cleared on each 50 MHz rising edge. After release:

1. synchronizer stages fill;
2. each detector uses its first sample to establish history;
3. software waits an initialization interval;
4. the first measurement may start.

The integrated testbench waits four cycles. There is no `sync_valid` signal. A filling transition may exist internally when an input was high during reset, but the idle measurement core ignores it.

## 3. Start sequence

| Cycle action | Interface behavior |
|---|---|
| Accepted write with `mem13_wdata[3]=1` while idle | Set `start_armed`; do not start yet. |
| First later accepted write with bit 3 = 0 | Clear `start_armed`; pulse `measurement_start` for one cycle. |
| Additional write of 0 | No retrigger. |
| Any control write while busy | Reject atomically. |

On the cycle in which `start` is accepted by `phase_measurement`, the core becomes busy, clears `result_valid`, and waits for an origin. The stored `phase_result` need not be erased.

## 4. Origin and count updates

The cycle-level priority is:

1. synchronous reset;
2. accepted start;
3. active-window event processing;
4. read-clear of an already published result;
5. hold state.

Within active event processing:

| `rclk_rise_evt` | `data_toggle_evt` | Behavior |
|---:|---:|---|
| 0 | 0 | If an origin exists, increment the count. |
| 1 | 0 | Establish/replace origin and set count to 0. |
| 0 | 1 | Capture current count only if an origin exists. |
| 1 | 1 | Establish the current origin and capture 0. |

A DATA event before the first RCLK origin is ignored. Every later RCLK event replaces the origin, so a DATA transition after several empty receive-clock periods is measured from the latest period, not the first.

## 5. Examples

### Adjacent cycles

```text
cycle n:     rclk_rise_evt=1, count becomes 0
cycle n+1:   data_toggle_evt=1, result becomes 1
```

### Same cycle

```text
cycle n:     rclk_rise_evt=1 and data_toggle_evt=1
result:      0
```

### Origin replacement

```text
cycle n:     RCLK origin A
cycle n+k:   RCLK origin B replaces A
cycle n+k+m: DATA captures m, not k+m
```

## 6. Completion and read-clear

Capturing a result clears busy and sets `result_valid`. The mapped result remains visible until either:

- `cpu_read_clear` clears only `result_valid`; or
- a new accepted start clears `result_valid` and begins another measurement.

If result capture and read-clear occur abnormally in one cycle, capture wins and the new result remains valid. Normal software avoids this ambiguity by waiting for valid, reading, and then clearing.

## 7. Discrete-observation limitations

The RTL cannot state which of two analog edges occurred first when both map to the same reference-clock sample. Metastability can move an observation by a cycle, and transitions occurring an even number of times between sample points can disappear. Therefore a result of 0 means “same observable 50 MHz cycle,” not “zero physical phase.”

## 8. Counter boundary

The faithful result width is 10 bits. Natural wrap is possible if a count were allowed to run long enough, but active RCLK events normally reset it each receive-clock period. v1.0 provides no saturation or wrap indication. Directed near-wrap testing and explicit saturation status belong to future work.

## 9. Verified timing cases

Current simulations cover first-sample detector arming, one-cycle event pulses, phase results 1 and 3 at unit level, same-cycle phase 0, replacement by the latest origin, restart invalidation, read-clear, busy-write rejection, and synchronous reset. The integrated path covers phase 1 and phase 0 after four initialization cycles.

Full nominal-frequency regression, long waits, physical implementation timing, and analog margin remain outside the completed v1.0 evidence.
