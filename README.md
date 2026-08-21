# Adaptive V.35 Sampling Monitor

[中文](README_zh-CN.md)

A SystemVerilog reconstruction of a legacy CPLD subsystem that measures the discrete phase between V.35 receive-clock edges and receive-data transitions. A CPU can use the result to select a safer sampling edge for a TDMoP device that has no built-in receive-edge adaptation.

## Current milestone

**Faithful version v1.0 is implemented and has passed the current unit and end-to-end simulations.**

“Faithful” means faithful to the engineering behavior recovered from the historical material and subsequently clarified with the original engineer. It does not mean mechanically reproducing every ambiguity in the old VHDL or Word document. In particular, the current RTL implements CPU-controlled single-measurement transactions; the historical CPU-side 10-sample and 3-sample averaging algorithms are not implemented in hardware.

The CPU reference-model exploration is complete and frozen. Executable models now cover the historical 10/3-sample algorithm, a circular-statistics candidate, confidence gating, threshold sweeps, and dynamic tracking, without changing CPLD v1.0. Hardware timeout, counter saturation, boundary classification, multiple-toggle diagnostics, and broader RTL regression remain future work.

## Why this exists

The original product used a TDMoP device that sampled V.35 receive data on a software-selected edge. At some operating frequencies, the DATA transition moved close to the default RCLK rising edge and caused bit errors. The legacy solution divided the work among three components:

| Component | Role |
|---|---|
| CPLD | Observe asynchronous RCLK and DATA, then report their discrete phase. |
| CPU | Repeatedly start single measurements, form the 10-sample initial mean or 3-sample periodic mean, and select or retain an edge relative to the current V.35 period. |
| TDMoP | Sample the actual traffic on the configured edge. |

This repository currently implements the CPLD measurement path and its CPU-facing register abstraction.

## Architecture

```mermaid
flowchart TD
    A["Asynchronous V.35 RCLK and DATA"] --> B["Matched two-stage synchronizers"]
    B --> C["RCLK-rise and DATA-toggle detectors"]
    C --> D["Single-transaction phase measurement"]
    E["mem13 write 1 then 0"] --> F["One-cycle measurement_start"]
    F --> D
    D --> G["mem13 and mem14 result mapping"]
    H["External bus adapter"] --> I["cpu_read_clear"]
    I --> D
```

The measured quantity is a reference-clock sample-index difference:

$$
C_{phase}=n_d-n_r
$$

$$
t=C_{phase}\times20\text{ ns}
$$

where `n_r` is the most recent observable RCLK rising-event cycle and `n_d` is the first observable DATA-transition cycle that completes the transaction.

Key semantics:

- A CPU starts one measurement by writing `1` and then `0` to `mem13[3]` while the subsystem is idle.
- `register_interface` converts the accepted sequence into a single-cycle `measurement_start` pulse.
- Every RCLK rising event during the active window replaces the previous origin and clears the phase count.
- The first DATA transition after a valid origin captures the result.
- Events on adjacent 50 MHz cycles produce `phase_result=1`, equivalent to 20 ns.
- RCLK and DATA events observed on the same cycle produce `phase_result=0`.
- A newly accepted start immediately clears `result_valid`; the old numerical result may remain temporarily but is invalid.
- Writes while busy are rejected atomically.
- `cpu_read_clear` clears `result_valid` without erasing the stored result.
- The top level exposes `cpu_read_clear` because the real legacy CPU-bus read handshake is not yet known.

## Register mapping

| Field | Meaning |
|---|---|
| `mem13_rdata[3]` | CPU-visible control state |
| `mem13_rdata[2]` | Result valid/completion flag |
| `mem13_rdata[1:0]` | `phase_result[9:8]` |
| `mem14_rdata[7:0]` | `phase_result[7:0]` |

## Reset and initialization

Reset is synchronous to `clk_50m`. The faithful design has no `sync_valid` port. Each event detector uses its first post-reset sample to establish its comparison baseline.

If an asynchronous input is already high during reset, synchronizer filling can still appear as an internal event. The measurement core ignores events while idle, so this cannot publish a CPU-visible result. The first transaction must nevertheless start only after an initialization interval; the integrated testbench waits four 50 MHz cycles.

## Repository layout

```text
adaptive-sampling-monitor/
├── README.md
├── README_zh-CN.md
├── docs/                 # Historical record and Chinese/English design documents
├── model/                # CPU decision reference model and directed tests
├── rtl/                  # Four submodules and the integrated top level
└── tb/
    ├── adaptive_sampling_monitor_tb.sv
    ├── testcases/        # Reserved for future data-driven test vectors
    └── unit/             # Four self-checking unit testbenches
```

`tb/testcases/` is reserved for future data-driven regression vectors. The current tests generate stimuli directly in SystemVerilog, so the folder is intentionally empty.

## Documentation

| Topic | Chinese | English |
|---|---|---|
| Historical problem record | [original_v35_problem.md](docs/original_v35_problem.md) | [original_v35_problem_EN.md](docs/original_v35_problem_EN.md) |
| Design intent | [design_intent_zh-CN.md](docs/design_intent_zh-CN.md) | [design_intent_EN.md](docs/design_intent_EN.md) |
| Requirements | [requirements_zh-CN.md](docs/requirements_zh-CN.md) | [requirements_EN.md](docs/requirements_EN.md) |
| Architecture | [architecture_zh-CN.md](docs/architecture_zh-CN.md) | [architecture_EN.md](docs/architecture_EN.md) |
| Timing behavior | [timing_behavior_zh-CN.md](docs/timing_behavior_zh-CN.md) | [timing_behavior_EN.md](docs/timing_behavior_EN.md) |
| Verification plan and results | [verification_plan_zh-CN.md](docs/verification_plan_zh-CN.md) | [verification_plan_EN.md](docs/verification_plan_EN.md) |
| CPU algorithm exploration | [cpu_algorithm_exploration_zh-CN.md](docs/cpu_algorithm_exploration_zh-CN.md) | [cpu_algorithm_exploration_EN.md](docs/cpu_algorithm_exploration_EN.md) |

## Build and run

Requirements:

- Verilator with SystemVerilog and `--timing` support
- GTKWave for interactive VCD inspection
- A C++ compiler and `make` available to Verilator

### End-to-end test

From the repository root:

```bash
verilator --binary \
  --timing \
  --trace \
  --top-module adaptive_sampling_monitor_tb \
  rtl/input_synchronizer.sv \
  rtl/event_detector.sv \
  rtl/phase_measurement.sv \
  rtl/register_interface.sv \
  rtl/adaptive_sampling_monitor.sv \
  tb/adaptive_sampling_monitor_tb.sv \
  --Mdir build/adaptive_sampling_monitor

./build/adaptive_sampling_monitor/Vadaptive_sampling_monitor_tb
echo $?
gtkwave adaptive_sampling_monitor_tb.vcd
```

The testbench prints a `PASS` summary and the shell prints exit code `0` when the run succeeds.

Expected terminal output:

```text
PASS: adaptive_sampling_monitor completed 29 checks
0
```

`PASS` means every expectation encoded in that testbench was satisfied. Exit code `0` means the simulation process reported success to the operating system. Neither result alone proves that the specification is complete; waveform review and coverage analysis remain separate evidence.

### Unit-test pattern

Example for `phase_measurement`:

```bash
verilator --binary \
  --timing \
  --trace \
  --top-module phase_measurement_tb \
  rtl/phase_measurement.sv \
  tb/unit/phase_measurement_tb.sv \
  --Mdir build/phase_measurement

./build/phase_measurement/Vphase_measurement_tb
echo $?
gtkwave phase_measurement.vcd
```

Use the corresponding RTL and testbench files for the other unit tests.

## Verified results

| Testbench | Recorded result | Covered behavior |
|---|---|---|
| `input_synchronizer_tb.sv` | `PASS`, exit 0 | Reset, two-stage propagation, stable input, narrow inter-sample pulse |
| `event_detector_tb.sv` | `PASS` | Baseline establishment, rise/fall/toggle detection, one-cycle pulses |
| `phase_measurement_tb.sv` | `PASS` | Start, phases 1 and 3, origin replacement, same-cycle 0, read-clear, restart, reset |
| `register_interface_tb.sv` | `PASS` | Arm/start sequence, busy rejection, mapping, reset |
| `adaptive_sampling_monitor_tb.sv` | `PASS`, exit 0 | End-to-end phase 1 and phase 0 paths, busy rejection, read-clear, final reset |

Key waveforms have also been manually inspected.

## Known limits

[Established limits]

- The result is a discrete digital observation, not an exact analog phase measurement.
- Two-stage synchronization reduces metastability propagation risk but cannot eliminate metastability.
- Sub-cycle ordering is not preserved; same-sample events are deliberately reported as 0.
- Transitions folded between 50 MHz sample points may be missed.
- The faithful version has no timeout, saturation indication, or independent error register.
- No target-device synthesis, place-and-route, timing closure, board validation, or BER test has been completed in this repository.

[Not yet verified]

- Full regression at 64 kHz, 2.048 MHz, and all nominal `N=1..32` frequencies.
- Directed behavior near 10-bit counter wrap.
- Long missing-clock and missing-data cases.

[CPU reference model verified]

- No initial decision is published before 10 valid samples have been collected.
- All three defined initial-calibration regions are covered.
- Every three periodic samples form one non-overlapping batch.
- Periodic switch regions, retain regions, undocumented gaps, and exact thresholds are covered.
- Invalid results do not enter statistical batches; a frequency change clears history and restarts initial calibration.
- A wrap-crossing distribution demonstrates how an arithmetic mean can be pulled incorrectly toward the middle of the period.
- Circular mean, concentration, both legacy and circular decision margins, threshold sweeps, guarded final actions, and dynamic phase tracking are implemented.
- The Python reference model currently passes 33 tests.
- Exploration conclusions are frozen; candidate thresholds await real board data and product response requirements.

## Extended-version roadmap

Candidate work, not current functionality:

1. Explicit missing-clock and missing-data timeouts.
2. Counter saturation and status reporting.
3. Boundary and multiple-toggle diagnostics.
4. Data-driven regression vectors under `tb/testcases/`.
5. Full nominal-frequency regression and an independent scoreboard.
6. Target-Lattice synthesis constraints, CDC attributes, and timing review.
7. The historical CPU algorithm has an executable reconstruction; the circular-statistics candidate awaits real measurements and will not accumulate further statistical complexity meanwhile.

The extended version should be developed as a separate, clearly labeled layer so that improvements do not silently change the frozen faithful-version contract.
