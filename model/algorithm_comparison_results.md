# CPU 判决算法场景对照结果

接收时钟周期：$T = 120$ 个相位计数单位。圆周集中度越接近 1，样本在圆周上越集中。

| 场景 | 普通平均 | 圆周平均 | 集中度 | 普通裕量 | 圆周裕量 | 普通裕量 / $T$ | 圆周裕量 / $T$ | 原算法 | 圆周候选 | 是否不同 |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| initial_stable_near_rising | 5.00 | 5.00 | 0.999 | 25.00 | 25.00 | 0.208 | 0.208 | set_falling | set_falling | 否 |
| initial_stable_near_falling | 60.00 | 60.00 | 0.998 | 30.00 | 30.00 | 0.250 | 0.250 | set_rising | set_rising | 否 |
| initial_stable_near_period_end | 114.70 | 114.70 | 0.999 | 24.70 | 24.70 | 0.206 | 0.206 | set_falling | set_falling | 否 |
| initial_quarter_boundary_jitter | 30.00 | 30.00 | 0.999 | 0.00 | 0.00 | 0.000 | 0.000 | unresolved_initial_boundary | unresolved_initial_boundary | 否 |
| initial_wraparound_cluster | 48.20 | 0.20 | 0.997 | 18.20 | 29.80 | 0.152 | 0.248 | set_rising | set_falling | 是 |
| initial_single_outlier | 33.60 | 27.00 | 0.801 | 3.60 | 3.00 | 0.030 | 0.025 | set_rising | set_falling | 是 |
| periodic_explicit_keep_region | 20.00 | 20.00 | 0.999 | 30.00 | 30.00 | 0.250 | 0.250 | keep_falling | keep_falling | 否 |
| periodic_undocumented_gap | 45.00 | 45.00 | 0.999 | 5.00 | 5.00 | 0.042 | 0.042 | keep_falling | keep_falling | 否 |
| initial_wide_dispersion | 59.00 | undefined | 0.000 | 29.00 | undefined | 0.242 | undefined | set_rising | undefined_circular_mean | 是 |
| initial_opposite_bimodal | 30.50 | 30.50 | 0.016 | 0.50 | 0.50 | 0.004 | 0.004 | set_rising | set_rising | 否 |
| initial_high_concentration_low_margin | 30.40 | 30.40 | 1.000 | 0.40 | 0.40 | 0.003 | 0.003 | set_rising | set_rising | 否 |
| periodic_batches_near_threshold | sequence | undefined | 1.000 | 0.67 | 0.67 | 0.006 | 0.006 | falling -> rising -> rising -> rising -> rising | falling -> rising -> rising -> rising -> rising | 否 |

## 场景说明

- `initial_stable_near_rising`：稳定聚集在上升沿附近，预期选择下降沿
- `initial_stable_near_falling`：稳定聚集在半周期附近，预期选择上升沿
- `initial_stable_near_period_end`：稳定聚集在周期末端，预期选择下降沿
- `initial_quarter_boundary_jitter`：围绕 $T/4$ 抖动，普通平均恰好命中未定义边界
- `initial_wraparound_cluster`：样本物理上聚集在 $0/T$ 两侧，用于暴露普通平均回绕错误
- `initial_single_outlier`：九个样本靠近 $T/4$ 下方，一个远端异常值把普通平均推过边界
- `periodic_explicit_keep_region`：运行期样本位于原表明确保持区
- `periodic_undocumented_gap`：运行期样本位于 $4T/12$ 到 $5T/12$ 的原文空窗
- `initial_wide_dispersion`：样本近似覆盖整个周期，用于验证低集中度和圆周均值无可靠方向
- `initial_opposite_bimodal`：样本形成相隔半周期的两个峰，用于验证圆周均值退化
- `initial_high_concentration_low_margin`：样本高度集中但均值仅略高于 $T/4$，用于区分稳定度与决策裕量
- `periodic_batches_near_threshold`：连续批次在 $5T/12$ 阈值两侧波动，用于观察保持区是否抑制反复切换
  - 实际切换次数：原算法 1 次，圆周候选 1 次。

## 解释边界

普通裕量由普通平均计算，圆周裕量由圆周平均计算；裕量只表示对应均值到有效决策边界的距离，不能证明该均值可信。
本报告只比较统计量及由同一阈值表产生的裁定。圆周算法目前是候选对照，
不是已确认替代方案；集中度阈值、异常值定义和失败恢复仍未规定。
