# CPU 候选算法门限扫描结果

场景周期为 `T=120` 个相位计数单位。接受条件为：圆周均值有效、集中度不低于门限、圆周裕量/T 不低于门限。

表中数字为通过门限的场景数，场景总数为 12。

| 最小集中度 \ 最小圆周裕量/T | 0 | 0.005 | 0.01 | 0.025 | 0.05 | 0.1 |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 11 | 8 | 7 | 6 | 5 | 5 |
| 0.5 | 10 | 8 | 7 | 6 | 5 | 5 |
| 0.8 | 10 | 8 | 7 | 6 | 5 | 5 |
| 0.9 | 9 | 7 | 6 | 6 | 5 | 5 |
| 0.95 | 9 | 7 | 6 | 6 | 5 | 5 |
| 0.99 | 9 | 7 | 6 | 6 | 5 | 5 |

## 代表性门限组合

### 仅排除无定义均值

门限：集中度 ≥ `0`，圆周裕量/T ≥ `0`。

接受：`initial_stable_near_rising`, `initial_stable_near_falling`, `initial_stable_near_period_end`, `initial_quarter_boundary_jitter`, `initial_wraparound_cluster`, `initial_single_outlier`, `periodic_explicit_keep_region`, `periodic_undocumented_gap`, `initial_opposite_bimodal`, `initial_high_concentration_low_margin`, `periodic_batches_near_threshold`

拒绝：`initial_wide_dispersion`

### 宽松观察

门限：集中度 ≥ `0.8`，圆周裕量/T ≥ `0.01`。

接受：`initial_stable_near_rising`, `initial_stable_near_falling`, `initial_stable_near_period_end`, `initial_wraparound_cluster`, `initial_single_outlier`, `periodic_explicit_keep_region`, `periodic_undocumented_gap`

拒绝：`initial_quarter_boundary_jitter`, `initial_wide_dispersion`, `initial_opposite_bimodal`, `initial_high_concentration_low_margin`, `periodic_batches_near_threshold`

### 中等观察

门限：集中度 ≥ `0.9`，圆周裕量/T ≥ `0.025`。

接受：`initial_stable_near_rising`, `initial_stable_near_falling`, `initial_stable_near_period_end`, `initial_wraparound_cluster`, `periodic_explicit_keep_region`, `periodic_undocumented_gap`

拒绝：`initial_quarter_boundary_jitter`, `initial_single_outlier`, `initial_wide_dispersion`, `initial_opposite_bimodal`, `initial_high_concentration_low_margin`, `periodic_batches_near_threshold`

### 严格观察

门限：集中度 ≥ `0.99`，圆周裕量/T ≥ `0.05`。

接受：`initial_stable_near_rising`, `initial_stable_near_falling`, `initial_stable_near_period_end`, `initial_wraparound_cluster`, `periodic_explicit_keep_region`

拒绝：`initial_quarter_boundary_jitter`, `initial_single_outlier`, `periodic_undocumented_gap`, `initial_wide_dispersion`, `initial_opposite_bimodal`, `initial_high_concentration_low_margin`, `periodic_batches_near_threshold`

## 解释限制

这些门限名称只是方便比较，不代表产品推荐值。场景是定向构造样本，不是现场概率分布；扫描结果只能显示参数敏感性，不能据此估计误码率或误拒绝率。
