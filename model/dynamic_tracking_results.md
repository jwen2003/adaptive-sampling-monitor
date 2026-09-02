# CPU 动态相位跟踪结果

$T = 120$，每批约 `3` 秒；探索门限为集中度 $\ge 0.9$、圆周裕量与 $T$ 的比值 $\ge 0.025$。

| 场景 | 相位中心序列 | 原算法首次切换 | 带门限首次切换 | 延迟 |
|---|---|---|---|---|
| slow_cross_to_rising | `44, 47, 49, 51, 52, 54, 56` | 第 4 批 | 第 6 批 | 2 批 / 约 6 秒 |
| slow_cross_to_falling | `16, 13, 11, 9, 8, 6, 4` | 第 4 批 | 第 6 批 | 2 批 / 约 6 秒 |
| fast_jump_to_rising | `40, 60, 60, 60` | 第 2 批 | 第 2 批 | 0 批 / 约 0 秒 |
| noisy_threshold_crossing | `48, 49, 51, 49, 52, 50, 54, 56` | 第 3 批 | 第 7 批 | 4 批 / 约 12 秒 |
| transient_cross_and_retreat | `45, 48, 49, 51, 49, 47, 45` | 第 4 批 | 未切换 | 带门限版本未切换 |

## 逐批采样沿

### slow_cross_to_rising

当前为下降沿，相位缓慢跨过 $5T/12$ 的上升沿切换边界

- 原算法：`falling -> falling -> falling -> rising -> rising -> rising -> rising`
- 带门限：`falling -> falling -> falling -> falling -> falling -> rising -> rising`

### slow_cross_to_falling

当前为上升沿，相位缓慢跨过 $T/12$ 的下降沿切换边界

- 原算法：`rising -> rising -> rising -> falling -> falling -> falling -> falling`
- 带门限：`rising -> rising -> rising -> rising -> rising -> falling -> falling`

### fast_jump_to_rising

相位从保持区直接跳入具有明显裕量的上升沿区域

- 原算法：`falling -> rising -> rising -> rising`
- 带门限：`falling -> rising -> rising -> rising`

### noisy_threshold_crossing

相位在 $5T/12$ 附近来回波动后继续深入上升沿区域

- 原算法：`falling -> falling -> rising -> rising -> rising -> rising -> rising -> rising`
- 带门限：`falling -> falling -> falling -> falling -> falling -> falling -> rising -> rising`

### transient_cross_and_retreat

相位短暂越过 $5T/12$ 后退回，比较是否产生不可逆的提前切换

- 原算法：`falling -> falling -> falling -> rising -> rising -> rising -> rising`
- 带门限：`falling -> falling -> falling -> falling -> falling -> falling -> falling`

## 解释限制

轨迹使用每批三个相邻整数样本构造，未加入真实抖动概率、测量丢失或频率变化。切换延迟按当前“每秒一个结果、三个结果一批”的重建换算。
