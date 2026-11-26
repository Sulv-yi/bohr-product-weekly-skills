# HRR 分区数计算：p(80) … p(800)

按题目要求实现 Hardy–Ramanujan–Rademacher 级数计算精确分区数，
并用**精确整数 DP** 独立复算做交叉验证。两条路径的 5 个结果完全一致。

## 结果（即 `/app/outputs/partition_results.json` 内容）

| n | p(n) |
|---|---|
| 80 | 15796476 |
| 120 | 1844349560 |
| 200 | 3972999029388 |
| 400 | 6727090051741041926 |
| 800 | 5733052172321422504456911979 |

JSON 见根目录 `partition_results.json`（与 `results/partition_results.json` 同内容）。

## 方法

按题面式 (1.4)(1.5)(2.1) 逐项实现：

```
p(n) = Σ_{k=1..N} sqrt(3/k) · 4/(24n−1) · A_k(n) · U(C(n)/k)
U(x) = cosh(x) − sinh(x)/x,   C(n) = π/6·sqrt(24n−1)
```

- `A_k(n)` 用题面 Algorithm 1 的循环形式：`k≤1 → k`，`k=2 → (−1)^n`，
  其余用 `(s,r,m)←(0,2,n mod k)` 逐 l 累加 `(−1)^l cos(π(6l+1)/(6k))`。
- 截断项数 `N = ceil(sqrt(n))`（题面指出 n≥65 时充分），并**按式 (1.8) 验证**：
  余项上界 M(n,N) 必须 < 0.5，四舍五入才可靠。
- 工作精度 80 位十进制（mpmath），远高于所需——p(800) 只有 28 位。

## 交叉验证

| n | 精确 DP | HRR 级数 | N | 两法之差 | 余项上界 M(n,N) |
|---|---|---|---|---|---|
| 80 | 15796476 | 15796476 | 9 | 0 | 4.986e-01 |
| 120 | 1844349560 | 1844349560 | 11 | 0 | 4.511e-01 |
| 200 | 3972999029388 | 3972999029388 | 15 | 0 | 3.783e-01 |
| 400 | 6727090051741041926 | 6727090051741041926 | 20 | 0 | 3.349e-01 |
| 800 | 5733052172321422504456911979 | 5733052172321422504456911979 | 29 | 0 | 2.753e-01 |

DP 是无浮点的整数计数（`p[n] += p[n−k]`），不会出错；HRR 是 80 位浮点解析级数。
两者算法路径完全不同，同时得到同一个整数，可以排除实现 bug 与精度不足。
余项上界全部 < 0.5（最紧的是 p(80)：0.4986），取整有效。

## 复现

```bash
python3 src/reproduce.py     # 双路径计算 + 比对 + 写 results/partition_results.json
python3 scripts/partition_hrr.py --check-bound   # 仅 HRR，附余项上界
python3 scripts/partition_dp.py                  # 仅精确 DP
```

`reproduce.py` 在两法不一致时会以非零码退出并拒绝写出结果，
所以落盘的值必然是两法一致的。

## 依赖

- Python 3.10+
- mpmath 1.4.1（`python3 -m pip install mpmath`）
- 纯标准库即可完成 DP 路径，无第三方依赖

## 文件

```
partition_results.json      交付结果（契约同构）
results/partition_results.json  同一份结果的副本
scripts/partition_hrr.py    HRR 级数实现 + 余项上界检查
scripts/partition_dp.py     精确整数 DP 交叉验证
src/reproduce.py            一键复现与比对
```
