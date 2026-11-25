# 增益对照协议（A/B，可复现）

用途：让「加载 Skill 是否真的把 LaTeX 活干得更好」可以被第三方重跑，而不是靠文字自述。
平台会自己做基础 Agent 与 Skill Agent 的对照；本文件给出**同一套口径**，任何人换一份工程都能照做。

## 1. 对照条件必须逐项一致

| 条件 | 要求 | 如何保证 |
|---|---|---|
| 输入工程 | 同一份、同一版本 | 记录工程 tar 包的 sha256 前 12 位 |
| 任务指令 | 同一句 | 用同一 `task.md`，只改"是否加载 Skill" |
| 引擎与宏包 | 同一 TeX 发行版、同一版本 | 从 `probe_project.py` 的 `selected_engine` / `engine_version` 抄，不手写 |
| 轮次预算 | 相同模型、相同请求上限 | 记录 model 与 max_requests（题面为 64 轮 / 900s） |
| 评分口径 | 同一 `eval/rubric.json` | 阈值写死在文件里，不随人调 |
| 评分人 | 同一人 / 同一 judge | 记录 judge 标识 |
| 顺序 | A/B 匿名、随机 | 由第三方抽签决定呈现顺序 |

任何一项不同（尤其是引擎版本或宏包版本），编译类差值就不能归因于 Skill。

## 2. 两个条件

- **A（baseline）**：不加载本 Skill，指令为「按模板写出这份工程的 LaTeX 成稿并编译通过」。
- **B（skill）**：加载本 Skill，按 `SKILL.md` 第 0–9 步执行，产出 `main.tex` + `result.json` + `selfcheck.md` + `cite-map.csv` + `compile-report.json`。

两侧使用同一工程、同一引擎、同一轮次预算。

## 3. 重复性与取数

- 每个条件重复 **3 次**（与平台一致）。
- 指标取 3 次的**中位数**，同时报告极差（max−min）。
- 若 3 次的 `sections` 或 `compile_status` 不一致（例如两次 passed、一次 failed），
  说明输出不稳定，先修 Skill 再比较，不要拿最好的那次当结论。

## 4. 指标与判定

用 `eval/score_output.py` 分别对 A、B 算同一组指标：

| 指标 | 含义 | 方向 |
|---|---|---|
| `sections` | 成稿实际章节数 | 越高越好，不少于模板要求 |
| `total_real_chars` | 全篇实义字数（去命令、去空白） | 越高越好 |
| `min_section_chars` | 最薄一节的实义字数 | 越高越好，≥120 为过 |
| `equations` | 有真实内容的公式环境数 | 越高越好，≥1 |
| `tables` | 有真实数据行的表格数 | 越高越好，≥1 |
| `cite_keys` | 正文实际 `\cite` 的不同键数 | 越高越好 |
| `cite_resolved_rate` | 引用键能在 `.bib` 找到的比例 | 越高越好，1.0 为满 |
| `compile_status` | `passed` / `failed` / `unavailable` | 只认编译日志 |
| `compile_errors` | 编译错误条数 | 越低越好 |
| `compile_errors_located_rate` | 错误定位到 file:line 的比例 | 越高越好 |
| `repro_coverage` | 复现六要素（engine/version/packages/command/rounds…）覆盖率 | 越高越好 |
| `source_map_count` | 事实来源映射条数 | 越高越好，≥3 |
| `placeholder_errors` | 残留占位符 | 越低越好，0 为满 |

**增益判定**（只报差值，不报绝对分）：

```
Δmetric = median(B) − median(A)
```

- 质量增益成立：`Δtotal_real_chars > 0` 且 `Δcite_resolved_rate ≥ 0` 且 `Δplaceholder_errors ≤ 0`，
  且至少两项严格变好；`compile_status` 不得从 `passed` 退成 `failed`。
- 效率增益成立：`compile_errors` 不增的前提下，B 的 `compile_errors_located_rate` 不为 0，
  且 A 侧存在"首错即停、反复试探"的痕迹（日志轮次多、错误数在轮次间反复）。
- 任一项变差，如实写进 `result.uncertainty`，不挑选性报告。

**已知会持平或变差的两项，先说清楚**：

- `equations` / `tables`：如果任务本身不改公式与表格，A、B 应保持相同数值。B 侧若数值上升，
  必须能用 `source_map` 说明"新增内容来自材料"，否则视为超范围改动，不算增益。
- 本机无 TeX 引擎时 `compile_status` 两侧都是 `unavailable`，编译类指标（`compile_errors*`）
  在两侧都无意义，此时**只报结构类指标**，并在报告里写明"编译类差值需在有 latex-compiler 的镜像内复核"。
  `score_output.py` 在这种情况下把 `gain_verifiability` 判为 `n/a` 而不是 `pass`，就是为了不替环境说谎。

## 5. 盲评（结构指标覆盖不到的部分）

结构指标看得出"有没有公式表格"，看不出"公式对不对、表格列宽合不合理"。这部分交给盲评：

1. 把 A、B 两版去标识化为「版本 1」「版本 2」，顺序随机。
2. 评分人只看两份 `.tex` + 编译日志 + `eval/acceptance.md` 第 2 节的评分表。
3. 至少 2 人独立打分，不给对方看结果。
4. 报告均值与分歧项；分歧项必须写清"为什么分歧"（引用具体行号）。

## 6. 复现命令

```bash
# A 条件（不加载 Skill 的产物放在 /app/work/A/）
python eval/score_output.py --result /app/work/A/result.json \
    --case /input/case.json --tex /app/work/A/main.tex \
    --compile-report /app/work/A/compile-report.json --out /app/work/A/scorecard.json

# B 条件
python eval/score_output.py --result /app/output/result.json \
    --case /input/case.json --tex /app/output/main.tex \
    --compile-report /app/output/compile-report.json --out /app/output/scorecard.json

# 对比
python eval/compare_ab.py /app/work/A/scorecard.json /app/output/scorecard.json \
    --md /app/output/ab-report.md
```

`compare_ab.py` 的判定规则就是第 4 节，不含人工加权。

## 7. 边界

- 本协议不产生「正式案例成绩」，只用于开发期自测与第三方复现。
- `examples/` 中的稿件与输出均为示例（材料为演示用虚构内容），不冒充平台固定案例。
- 若平台已给出对照结果，以平台结果为准；本协议用于解释差异来源。
- 不声称编译通过率优于某个具体编辑器或模板向导——未在同一工程上实测过。
