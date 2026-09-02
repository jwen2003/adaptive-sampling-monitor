# V.35 CPU Sampling-Edge Algorithm — Exploration Conclusions

Document revision: v1.0
RTL baseline: v1.0 (unchanged)
Status: reference-model exploration frozen pending real measurements
Date: 2026-08-20

## 1. Purpose and boundary

This document records the reconstructed historical CPU decision algorithm, its executable reference model, reproduced failure modes, and a candidate enhancement. It does not claim that the candidate existed in the original product, and it does not promote exploratory thresholds to product requirements.

## 2. Established facts

1. Each CPLD transaction produces one `phase_count`; multi-sample statistics belong to CPU software.
2. After power-up or a frequency change, the historical CPU collects 10 valid results and computes an ordinary arithmetic mean.
3. During operation, approximately one result is obtained every second. The current reconstruction forms a non-overlapping batch of three results and makes one decision approximately every 3 s.
4. Initial and periodic decisions use the interval tables in the historical material; the periodic table contains retain regions.
5. The current CPLD RTL v1.0 does not need to change for this algorithm exploration.

## 3. Where the historical algorithm is adequate

When the samples form a stable, unimodal distribution that does not cross the $0/T$ wrap, the arithmetic and circular means produce the same decision. The historical algorithm is therefore not universally wrong. Its main limitations arise from the circular nature of phase and from abnormal distributions.

## 4. Reproduced failure modes

### 4.1 Phase wrap

When samples cluster on both sides of the period boundary, the arithmetic mean moves the apparent location toward the middle of the period. In the directed case, the arithmetic mean is `48.20`, while the circular mean is approximately `0.20`; they select rising and falling respectively. Circular concentration is `0.997`, showing that the wrapped distribution is stable rather than random noise.

### 4.2 Dispersion and bimodality

- A distribution spread around the full period has circular concentration 0 and no defined circular mean.
- Two peaks separated by half a period can still produce a numerical mean, but concentration is close to 0 and the mean is not representative.

### 4.3 One distant sample

A single distant sample can push the arithmetic mean across a decision boundary. A circular mean is not a universal outlier filter; such a case is better handled by rejecting the decision or collecting more evidence when concentration is insufficient.

### 4.4 Stable but close to a boundary

High concentration says that the measurements are stable, not that the edge decision is well separated. If the circular mean lies close to an effective decision boundary, the decision still has little margin. Statistical stability and decision margin must therefore be evaluated independently.

## 5. Two confidence metrics

- **Circular concentration** describes how tightly phase samples cluster on the circle and ranges from 0 to 1.
- **Normalized circular decision margin** is the circular distance from the circular mean to the nearest effective boundary at which the final sampling edge would change, divided by the period $T$.

$0/T$ is a numerical wrap point, not an initial-calibration decision boundary. Because periodic calibration contains retain regions, its effective boundaries depend on the current sampling edge.

## 6. Candidate guarded policy

The reference enhancement processes a batch in this order:

1. compute the circular mean and concentration;
2. reject the batch if the circular mean is undefined or concentration is insufficient;
3. compute normalized circular decision margin;
4. reject the batch if margin is insufficient;
5. after both gates pass, apply the historical interval table to the circular mean;
6. after an initial-calibration rejection, publish no new edge and request another calibration attempt;
7. after a periodic rejection, retain the current edge.

The current program demonstrates behavior using concentration at least `0.9` and circular margin divided by `T` at least `0.025`. This pair is an observation point for directed scenarios, not a frozen threshold.

## 7. Dynamic-response results

Assuming one valid result per second and three results per batch:

| Scenario | Historical algorithm | Candidate enhancement |
|---|---|---|
| Slow boundary crossing | Switches at batch 4 | Switches at batch 6; about 6 s additional delay |
| Fast unambiguous jump | Switches at batch 2 | Switches at batch 2; no additional delay |
| Noisy crossing | Switches at batch 3 | Switches at batch 7; about 12 s additional delay |
| Transient crossing followed by retreat | Switches and does not automatically recover because of the retain region | Does not switch |

The confidence gate reduces low-evidence switching at the cost of a slower response to genuine gradual drift. Without a product limit on switching delay and a cost model for false switching, the final thresholds cannot be selected.

## 8. Interim decisions

[Established]

- The historical arithmetic mean cannot correctly represent a distribution crossing the $0/T$ wrap.
- Concentration and decision margin describe statistical credibility and decision separation respectively; neither replaces the other.
- Periodic retain regions suppress repeated switching, but can also preserve a switch caused by a transient excursion.
- The candidate enhancement requires no change to CPLD RTL v1.0.

[Candidate]

- Use a circular mean, a concentration gate, and a normalized decision-margin gate in CPU software.
- Retry after an initial rejection and retain the current edge after a periodic rejection.

[Not established]

- Whether real-device phase distributions cross the wrap, become bimodal, or contain distant samples.
- Product thresholds for concentration and margin.
- Maximum initial retries, the default edge after failure, and fault reporting.
- Maximum acceptable periodic switching delay.
- The frequency-change detector and recalibration entry path.
- The real CPU-to-TDMoP control path.

## 9. Freeze and resume conditions

Algorithm exploration is frozen and will not accumulate further statistical complexity. Resume it only after at least one of the following becomes available:

1. continuous `phase_count` logs from real hardware;
2. product requirements for false-switch rate, maximum response time, or calibration failure;
3. the original CPU source or a more complete software requirement;
4. board testing that shows the current decision still causes errors at a specific frequency.

## 10. Executable artifacts

The reference model, static scenarios, threshold sweep, guarded-action simulation, and dynamic tracking are under `model/`. The complete Python unit-test suite contains 33 tests, all passing. This result proves consistency with the current reconstruction and exploratory rules only; it does not prove that the candidate thresholds are suitable for the real product.
