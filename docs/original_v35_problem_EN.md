# V.35 Interface Adaptive Function — Original Problem Record

Status: Frozen historical requirements baseline
Original source: `RC1201-2FEV35设备V35接口自适应功能实现.doc`
Original source date: 2010-04-08
Reconstruction date: 2026-08-06

> This document is an English translation of the reconstructed historical problem record. The Chinese version, [`original_v35_problem.md`](original_v35_problem.md), remains the authoritative historical baseline. If the two versions differ in meaning, refer to the Chinese version.

## 1. Purpose of This Document

This document reconstructs the original V.35 interface adaptation problem provided by the engineer. It preserves the product context, observed failure, diagnostic conclusion, proposed solution, hardware/software responsibilities, key behavior of the original VHDL, and measured results.

It answers only two historical questions: what problem the original project encountered, and how the original solution addressed it. It is not the requirements specification for the current SystemVerilog reconstruction and does not incorporate the later module decomposition, cycle-by-cycle arbitration rules, verification strategy, or enhancements. Refer to the other design documents for the current design.

Unless a transcription error is discovered, this document is frozen and will not evolve with the RTL.

## 2. Original Device and Interface Context

The original device was the `RC1201-2FEV35`, a V.35-to-Ethernet TDMoP device whose basic function was to convert between V.35 data and Ethernet data.

The device provided:

- one V.35 interface;
- two Fast Ethernet electrical ports;
- one 1000/100M SFP optical port;
- dedicated SNMP and console interfaces.

The source described V.35 as a general-purpose terminal interface specification for synchronous data transmission. The device supported the following system-clock frequencies:

$$
f_{\mathrm{V35}}=N\times64\ \mathrm{kHz},\qquad N=1,2,\ldots,32
$$

The original test therefore covered 32 frequency points from 64 kHz to 2.048 MHz.

## 3. Original Test Environment

The original test system consisted of two devices and one V.35 tester:

- Device 1 operated in DCE mode and supplied the system clock;
- Device 2 operated in DCE mode, used a recovered clock, and internally looped back the V.35 interface data;
- the V.35 tester operated in DTE mode and used the external clock supplied by Device 1;
- data formed a test loop between the devices and the tester.

Figures 1 through 11 in the source included the device exterior, V.35 interface, test connections, waveforms at different frequencies, hardware block diagram, phase illustration, and a 10×64K example. They are not redrawn here; the original figures remain in the source Word document.

## 4. Observed Failure

While sweeping all 32 system-clock points at $N\times64$ kHz, the test found that:

- the tester reported bit errors near $20\times64$ kHz, or approximately 1.28 MHz;
- the other frequencies operated normally.

This was the central problem addressed by the original project.

## 5. Original Diagnostic Process and Conclusion

The original project successively inspected:

1. the hardware schematic;
2. PCB routing;
3. software register configuration.

No problem was found in those areas, so the investigation shifted to the timing relationship between the V.35 receive data and receive clock.

The engineer used an oscilloscope to measure the V.35 receive-data and receive-clock pin waveforms of Device 1 at different frequencies. The comparison showed that:

- the phase relationship between receive data and receive clock changed with the system-clock frequency;
- because the tester used Device 1's system clock as its external clock, the phase of the data transmitted by the tester relative to that clock also changed with frequency;
- the TDMoP device sampled receive data on the rising edge by default;
- near $20\times64$ kHz, a data transition occurred close to the receive-clock rising edge, making a 0 liable to be sampled as 1 or a 1 as 0;
- at the other frequency points, data transitions remained farther from the hazardous sampling position, so no bit errors appeared.

The original project therefore identified the cause as follows:

> The TDMoP device always sampled on the rising edge, while the phase between V.35 receive data and receive clock varied with frequency. At certain frequency points, a data transition approached the rising edge and caused sampling errors.

## 6. Original Solution

The original project established that some V.35 protocol-conversion devices contained a receive-side adaptive function that could select a better sampling time. The Maxim TDMoP device used in this product did not provide that function; software could only configure whether receive data was sampled on the rising or falling edge.

The final solution divided the work among the CPLD, CPU, and TDMoP device:

1. the CPLD measured the position of a V.35 receive-data transition relative to the V.35 receive clock;
2. the CPU read the CPLD result and calculated the preferable sampling edge;
3. the CPU configured the TDMoP device to sample on the rising or falling edge.

The CPLD did not directly choose or switch the TDMoP sampling edge.

## 7. Original CPLD Measurement Method

The original device used the 50 MHz CPLD system clock to sample:

- `V35_RCLK_I`: V.35 receive clock;
- `V35_RX_I`: V.35 receive data.

The period of the 50 MHz reference clock was:

$$
T_{50\mathrm{M}}=20\ \mathrm{ns}
$$

The original VHDL detected the rising edge of `V35_RCLK_I` in the 50 MHz clock domain. On a detected rising edge, it cleared the 10-bit counter `i_counter_for_v35_rclk_edge_calibration`; on other cycles, it incremented the counter. When any transition of the synchronized `V35_RX_I` was detected and the current measurement had not ended, the design latched the counter value and asserted the completion flag.

The source interpreted the data-transition position relative to the clock as:

$$
t=i_{\mathrm{counter}}\times20\ \mathrm{ns}
$$

At the minimum frequency of 64 kHz, the period is approximately 15.625 μs, corresponding to about 781 intervals of 20 ns. The original code therefore used a 10-bit counter.

### 7.1 Behavior Directly Observable in the Original Code

The original VHDL fragment exhibited the following behavior:

- the receive data and receive clock were each sampled through two 50 MHz registers;
- a receive-clock rising edge was recognized when the synchronized clock and its delayed value were `1` and `0`, respectively;
- each receive-clock rising edge cleared the phase counter;
- a data transition was recognized when the synchronized data differed from its delayed value;
- after the first data transition was captured, the completion flag was set to 1 and subsequent transitions no longer updated the result;
- the upper two bits of the 10-bit result were mapped to `mem13(1:0)`, and the lower eight bits to `mem14(7:0)`;
- `mem13(2)` was mapped to the measurement-completion flag.

These items only record the original code. They do not require the current reconstruction to reproduce every encoding choice or boundary behavior.

## 8. Original CPU Interaction Flow

The source described the following CPU sequence:

1. the CPU used the data/address bus to write `mem13(3)` from 1 to 0, starting a CPLD adaptive measurement;
2. after capturing a data transition, the CPLD set `mem13(2)` to 1 and stored the 10-bit phase count;
3. the CPU repeatedly read `mem13(2)`;
4. after observing `mem13(2)=1`, the CPU read the phase count;
5. the CPU calculated the preferable sampling edge;
6. the CPU configured the TDMoP register through the bus.

The original register map was:

| Address | Register | Original purpose |
|---|---|---|
| `0x0500000D` | `mem13` | bit 3: start control; bit 2: completion flag; bits 1:0: upper two result bits |
| `0x0500000E` | `mem14` | lower eight result bits |

The phase-result concatenation was:

```text
i_counter_for_v35_rclk_edge_calibration
    = mem13(1) & mem13(0) & mem14(7:0)
```

## 9. Original CPU Sampling-Edge Algorithm

### 9.1 Initial Decision After Power-Up or a Frequency Change

The CPU first took 10 samples and calculated the mean phase $t$:

| Mean phase interval | TDMoP sampling setting |
|---|---|
| $0<t<T/4$ | Falling-edge sampling |
| $T/4<t<3T/4$ | Rising-edge sampling |
| $3T/4<t<T$ | Falling-edge sampling |

### 9.2 Periodic Remeasurement During Operation

After the initial decision, the CPU sampled once per second and calculated the mean $t$ from three results. Under the ordinary reading of that sentence, this project reconstructs the schedule as a 1 s sample interval with non-overlapping three-sample batches. The source itself did not explicitly distinguish among non-overlapping batches, a three-point sliding window, or three rapid samples per round. The intervals given near the end of the source were:

| Mean phase interval | TDMoP sampling setting |
|---|---|
| $0<t<T/12$ | Falling-edge sampling |
| $T/12<t<4T/12$ | Keep the current setting |
| $5T/12<t<7T/12$ | Rising-edge sampling |
| $8T/12<t<11T/12$ | Keep the current setting |
| $11T/12<t<T$ | Falling-edge sampling |

The source did not specify how to handle:

$$
4T/12\le t\le5T/12
$$

$$
7T/12\le t\le8T/12
$$

It also did not assign equality at the thresholds.

## 10. Measured 10×64K Example

The source provided an example at $10\times64$ kHz, or 640 kHz.

Repeated CPLD measurements produced phase counts primarily of:

```text
0x038, 0x039, 0x03A
```

The original project considered this variation acceptable and used the mean:

$$
0x039=57
$$

Therefore:

$$
t=57\times20\ \mathrm{ns}=1140\ \mathrm{ns}=1.14\ \mu\mathrm{s}
$$

The period of a 640 kHz clock is:

$$
T=\frac{1}{640\ \mathrm{kHz}}\approx1562\ \mathrm{ns}
$$

The result satisfies:

$$
T/4<t<3T/4
$$

The oscilloscope cursor measured approximately 1.16 μs, differing from the CPLD result by 20 ns. The original project treated this one-cycle difference as normal, and the CPU consequently configured the TDMoP device for rising-edge sampling.

## 11. Original Project Conclusion

The source concluded that this solution used a CPLD to measure the phase between V.35 receive data and receive clock, with the CPU performing the calculation. It was applicable to V.35 interface devices that lacked receive-side adaptive capability.

The original program had been tested and could stably report phase values.

## 12. Ambiguities and Transcription Notes in the Source

The following items were incomplete or internally inconsistent in the source. This document records them without resolving them:

1. The continuous-calibration algorithm first appeared in the body as `5/12T < t < 712T`, but was repeated near the end as `5/12T < t < 7/12T`. The latter is dimensionally and contextually reasonable and is used in the table, while the apparent typo is still recorded here.
2. The continuous-calibration algorithm omitted the intervals from $4T/12$ to $5T/12$ and from $7T/12$ to $8T/12$, and did not define equality at any threshold.
3. The source stated that writing `mem13(3)` from 1 to 0 started a measurement, while the original VHDL sampled `mem13(3)` into an internal enable signal upon detecting a receive-clock rising edge. Their exact cycle-by-cycle relationship cannot be fully determined from the prose alone.
4. The original code had no explicit reset port; some signals depended on declaration-time initial values or subsequent control behavior.
5. The original code did not define timeout, counter saturation, counter-wrap reporting, or abnormal status.
6. The source did not define priority among multiple events occurring in the same cycle or formally define the count assigned to adjacent 50 MHz sampling cycles.
7. The source stated that the solution had passed stable testing, but presented detailed numerical data only for one 10×64K example and did not provide the raw results for all 32 frequency points.

These ambiguities are part of the historical record. Behaviors closed by engineer confirmation or design decisions in the current project belong in the current documents such as `requirements.md` and `timing_behavior.md`; they must not be back-propagated into this historical record.
