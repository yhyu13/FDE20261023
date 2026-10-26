"""
一次性核算脚本（非生产代码）· 爆款预测所需样本量测算
用途：为 `02_结合方向_爆款因子方法×申沃题02.md` §2 提供可复算的数字。
禁心算原则：所有数字由本脚本产出，改假设请重跑。

运行：python sample_size_calc.py
"""

import math
from statistics import NormalDist


def n_epv(base_rate: float, n_features: int, epv: int = 10):
    """EPV（每变量事件数）经验法则：需要的正样本数 = epv × 特征数"""
    events = epv * n_features
    return events, math.ceil(events / base_rate)


def n_two_proportions(p1: float, p2: float, alpha: float = 0.05, power: float = 0.8):
    """两比例检验所需每组样本量（双侧）"""
    za = NormalDist().inv_cdf(1 - alpha / 2)
    zb = NormalDist().inv_cdf(power)
    pbar = (p1 + p2) / 2
    n = ((za * math.sqrt(2 * pbar * (1 - pbar))
          + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / ((p1 - p2) ** 2)
    return math.ceil(n)


def years_needed(total_n: int, per_month: float) -> tuple:
    months = total_n / per_month
    return months, months / 12


print("=" * 62)
print("A. EPV 法：需要的爆款条数 / 总样本量")
print("=" * 62)
for p in (0.05, 0.10, 0.20):
    for k in (10, 20, 40):
        ev, n = n_epv(p, k)
        print(f"  爆款率 p={p:.0%}  特征数 k={k:>2}  ->  需爆款 {ev:>4} 条, 总样本 {n:>6} 条")

print()
print("=" * 62)
print("B. 申沃现实产量 -> 攒够样本所需时间")
print("=" * 62)
_, n_std = n_epv(0.05, 20)          # 4 000 条
_, n_opt = n_epv(0.10, 8)           #   800 条
print(f"  常规情形 k=20 / p=5%  -> 需 {n_std:,} 条")
print(f"  极乐观  k=8  / p=10% -> 需 {n_opt:,} 条")
for per_month, label in ((4, "现状 约4条/月(FB01-04外推)"),
                         (12, "加码 12条/月"),
                         (40, "矩阵化 40条/月")):
    m1, y1 = years_needed(n_std, per_month)
    m2, y2 = years_needed(n_opt, per_month)
    print(f"  {label:<24} 常规 {y1:>6.1f} 年 | 极乐观 {y2:>5.1f} 年")

print()
print("=" * 62)
print("C. 两比例检验：检出指定 lift 所需样本 (alpha=.05, power=.8)")
print("=" * 62)
for p1, p2 in ((0.05, 0.08), (0.05, 0.10), (0.05, 0.15), (0.20, 0.30)):
    n = n_two_proportions(p1, p2)
    print(f"  基线 {p1:.0%} -> {p2:.0%} (相对 +{(p2 / p1 - 1):.0%}): 每组 {n:>6,} 条, 合计 {2 * n:>6,} 条")

print()
print("=" * 62)
print("输入假设（均为假设值，非实测 —— 改假设请重跑）")
print("=" * 62)
print("  · 爆款率 5% / 10% / 20%：假设，无申沃实测依据")
print("  · 特征数 8-40：对应标签 Schema 粗细（见 03_ 文件）")
print("  · 月产量 4 条：由 FB01-FB04（4 条传播反馈）外推，可靠性低")
print("  · EPV=10 为经验法则，非精确样本量；特征共线性会进一步抬高需求")
