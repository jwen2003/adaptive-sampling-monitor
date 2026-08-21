# 带置信门的 CPU 最终动作模拟

探索门限：集中度 ≥ `0.9`，圆周裕量/T ≥ `0.025`；`T=120`。

首次校准拒绝后请求重测；运行期拒绝后保持当前采样沿。

| 场景 | 门限结果 | 原因 | 最终动作序列 |
|---|---|---|---|
| initial_stable_near_rising | 接受 | accepted | set_falling |
| initial_stable_near_falling | 接受 | accepted | set_rising |
| initial_stable_near_period_end | 接受 | accepted | set_falling |
| initial_quarter_boundary_jitter | 拒绝 | low_decision_margin | recalibrate |
| initial_wraparound_cluster | 接受 | accepted | set_falling |
| initial_single_outlier | 拒绝 | low_concentration | recalibrate |
| periodic_explicit_keep_region | 接受 | accepted | keep_falling |
| periodic_undocumented_gap | 接受 | accepted | keep_falling |
| initial_wide_dispersion | 拒绝 | undefined_circular_mean | recalibrate |
| initial_opposite_bimodal | 拒绝 | low_concentration | recalibrate |
| initial_high_concentration_low_margin | 拒绝 | low_decision_margin | recalibrate |
| periodic_batches_near_threshold | 拒绝 -> 拒绝 -> 拒绝 -> 拒绝 -> 拒绝 | low_decision_margin -> low_decision_margin -> low_decision_margin -> low_decision_margin -> low_decision_margin | keep_falling -> keep_falling -> keep_falling -> keep_falling -> keep_falling |

## 解释限制

`recalibrate` 只表示首次校准不能发布新的采样沿；重试次数、默认安全沿和最终故障升级策略尚未定义。门限仍是探索参数。
