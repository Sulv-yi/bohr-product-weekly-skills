# 别急着引用：把 AI 读论文的结论钉回原文条件

一句话：**AI 读文献真正会出事的地方，不是它读错，而是它把条件压掉之后，结论还是"对的"。**
这份分享给出一个可复跑的核对流程，和一篇真实论文上的完整核对记录。

- 案例论文：Merillas et al., *Upcycling post-consumer PET bottles into low-density films and
  3D-printed materials*, Materials Today Sustainability 34 (2026) 101352（CC BY-NC，开放获取）
- 阅读问题：**这篇论文的结论，能不能外推到我自己的体系？** 具体到三个可判定的子问题：
  摘要给的数字有没有覆盖正文的全部条件？"优于原生 PET"在哪个指标上成立？
  "减重 40%"是同一个量吗？
- 产出：14 条结论、15 行证据底账、一份机器判定报告、一份人工复核记录，
  以及两个可直接复用的脚本。

---

## 一、问题：结论为什么会"对但没用"

拿摘要里的这句话：

> PET_B shows cell sizes close to 2 μm together with relative densities of 0.2 to 0.28,
> **outperforming virgin PET**.（p1）

三个数字、一个比较级，读起来干净利落。但落到"我要不要用这个工艺"上，它缺三样东西：

1. **条件**。0.2–0.28 是哪个压力、哪个发泡温度下的？正文 p7 写得很清楚：
   PET_B 在 15 MPa 支路最低是 **0.35**（220 ℃），在 30 MPa 支路才是 0.20（200 ℃）。
   摘要的区间只覆盖了其中一支。
2. **口径**。同一篇里"减重 40%"出现过两种写法：p10 结果段是 "a reduction of more than 40%
   in **relative density**"，同页讨论段是 "**weight** reductions of up to 40%"。相对密度
   在有体积膨胀的前提下不等于重量，而同一页恰恰写了发泡会 "dimensional expansion"。
3. **对照臂**。PET_V 是作者特意选的低黏度原生料（0.63 dl/g，MFI 46.70），PET_B 是
   0.70–0.80 dl/g、MFI 11.52（p2、p4）。作者自己在 p2 说，若用瓶级 0.80 dl/g 会让熔体强度
   高出一截、"could bias the interpretation"。也就是说，比较在黏度上是**刻意不对称**的：
   实验臂熔体强度本来就更高。

这三样东西都不在摘要里，而人读完一遍摘要 + 扫一眼图，很容易漏。漏了不会立刻出错，
只会在半年后写方案时，把"回收料优于原生料"当成既成事实引进去。

## 二、方法：三步走，机器判可判的，人判不可判的

### 第 1 步 · 抽取保页码

用 PDF 抽取工具转 Markdown，要求保留 `<!-- page N -->` 锚点，只清噪声
（行末断词的软连字符 `\x02`、`◦`→`°`），**不改写句子**。这样后面每一条引文都能落到具体页。
脚本：`scripts/clean_extract.py`。本次结果：12 页、59 KB、`materials/extraction.log` 有原始输出。

### 第 2 步 · 结论绑定成表

每条带数字的结论写一行：`claim_id, subject, metric, value, page, quote, claim`。
硬规则三条：`quote` 逐字复制、不拼接、不跨页；摘要里的数和结果段的数分开记；
拿不准的指标写 `none`，不要硬塞。

这一步是"把脑内的读后印象落成可核对的记录"，也是整个流程里最容易被跳过、却最关键的一步——
没有 `quote` 就没有可核性。

### 第 3 步 · 机器核对五项 + 人工补三项

`scripts/claim_check.py`（纯标准库）判五件事：

| 项 | 判什么 | 不合格长什么样 |
| --- | --- | --- |
| B 绑定 | 引文归一化后能否在正文逐字命中，且落在声明页码 | `MISS` / `MISMATCH(p7)` |
| V 数值 | claim 里的每个数是否出现在它自己的引文里 | `MISS:0.28` |
| P 口径 | metric 的规范表述是否与引文用词一致 | `DRIFT(weight reductions)` / `NO-ANCHOR` |
| C 覆盖 | 证据底账里同料名同指标的数值是否都落在声明区间内 | `out-of-range:0.35` |
| U 可核 | 是否含 first/only 类断言 | `flag` |

C 项需要一份**证据底账** `evidence/corpus.csv`：把正文里能承载该指标的句子逐行列出，
标好料名与页码。这份底账是人工建的，但正因为人工，它可以被评审逐行审计——
底账写漏了，C 项就会假通过，所以脚本同时校验底账本身每条引文是否逐字命中（本次 15 行全中）。

脚本判不了的三件事，必须人读：

1. 摘要的比较级（better / outperform）有没有同条件证据；
2. 同一物理量是否在不同段落换了口径（相对密度 / 密度 / 重量 / 体积膨胀）；
3. "first / only" 有没有给检索范围。

## 三、结果：14 条结论里 4 条要改，1 条要降级

机器判定（`evidence/check.md`，10 PASS / 2 CONFLICT / 2 FAIL）：

| 条目 | 判定 | 问题 | 准确写法 |
| --- | --- | --- | --- |
| C02 PET_B 相对密度 0.2–0.28 | CONFLICT（越界 0.35） | 摘要区间未覆盖 15 MPa 支路 | 30 MPa/200 ℃ 时 0.20；15 MPa 支路最低 0.35（p7） |
| C03 PET_C 泡孔 5–18 μm | CONFLICT（越界 3, 20） | 主分布 3/6 μm、大孔到 20 μm 被截断 | 主分布 3 μm 与 6 μm，另有至 20 μm（p9 Fig.11 段） |
| C09 减重 40% | FAIL：DRIFT | 相对密度降幅被写成重量降幅 | 只引 relative density 降幅（p10） |
| C10 帽体密度 1.26 kg/m3 | FAIL：NO-ANCHOR | 单位与"略低于薄膜"自相矛盾，应为 g/cm³ | 1.26 g/cm³（原文单位疑为笔误，p10） |
| C11 首次保形发泡 | PASS + flag | 属作者主张，无检索范围 | 写"作者称首次"（p1、p2） |

人工补的三条（`evidence/manual_verify.md`）：

1. **outperform 只在泡孔维度成立**。原生料最低相对密度 0.16（15 MPa、200 ℃）、0.18（30 MPa），
   比 PET_B 的 0.20 更低（p6）。所以"优于原生 PET"必须收窄成"泡孔更细"。
2. **对照臂刻意不对称**，且作者已说明理由：为了不让黏度差成为解释变量，选了低黏度原生料。
   代价是"回收料泡孔更细"里混进了熔体强度效应。结论的适用范围是"对比低黏度原生料"。
3. **首次主张无检索范围**，正文只有 "has not been reported to date"，没有数据库、时间窗、关键词。

### A/B 对照：同一个问题，加不加流程

两次运行同模型（deepseek-v4.1-flash）、同输入（同一份 `materials/paper.md`）、同为一次问答、
无额外工具权限，只改变是否加载这套流程与脚本。

| | A-without（`evidence/ai_pass1_naive.md`） | A-with（`evidence/ai_pass2_checked.md`） |
| --- | --- | --- |
| 提示词 | 「读一下这篇论文，告诉我它的主要结论和可借鉴的方法」 | `prompts/01→02→03` + `claim_check.py` |
| 产出 | 5 条结论 + 方法概述 | 8 条结论，全部带条件与页码 |
| 相对密度 0.2–0.28 | 直接采信 | 指出未覆盖 15 MPa 支路，改用分支值 |
| 优于原生 PET | 直接采信 | 收窄为泡孔更细，附原生料 0.16 反证 |
| 对照臂规格 | 未提 | 0.63 vs 0.70–0.80 dl/g、MFI 46.70 vs 11.52 |
| PET_C 泡孔 | 5–18 μm | 3–20 μm，主分布 3/6 μm |
| 减重 40% | 单一口径 | 标出两种口径不可互换 |
| 1.26 kg/m3 | 未察觉 | 判为单位笔误并给换算 |
| 耗时 | 约 1 分钟 | 约 18 分钟（含 1 次重试与 4 处回原文复核） |

诚实说明：A-without 的 6 处问题里，有 4 处属于"需要改写才能引用"，1 处需降级为作者主张，
不是错误答案。增益体现在**可引用性**上，不体现在"读不读得懂"上。
单篇、单模型、单次运行，**不构成统计结论**，不能据此声称这套流程普遍提升阅读质量。
A-with 的 18 分钟里，脚本只占 0.2 秒，其余是人工建底账与回原文复核——这部分没有被自动化，
也不应该被自动化。

## 四、复现

依赖：Python 3.8+，只用标准库。抽取用 `workbuddy-pdf`（也可换成任何保留页码的抽取器）。

```bash
# 1. 抽取与清洗（PDF 需自备，见 materials/paper_source.md）
workbuddy-pdf paper.pdf work/raw.md --format md-plain
python3 scripts/clean_extract.py --in work/raw.md --out materials/paper.md

# 2. 生成结论清单与证据底账（引文会逐字校验，抄错会直接报错）
python3 scripts/build_claims.py

# 3. 核对
python3 scripts/claim_check.py --paper materials/paper.md \
    --claims evidence/claims.csv --corpus evidence/corpus.csv --out-prefix evidence/check

# 4. 看结果：有 FAIL/CONFLICT 时退出码为 1
cat evidence/check.md
```

本次实际输出（`evidence/check.md` 头部）：

```
- 结论条数：14
- PASS：10
- FAIL（引文/数值/口径对不上）：2 —— C09, C10
- CONFLICT（底账里有越出声明区间的数值）：2 —— C02, C03
- 底账错误：0
```

怎么判读：`MISS` 说明引文抄错或跨页了；`out-of-range` 说明同一个料名同一个指标还有别的数，
要么补条件、要么改区间；`DRIFT` 说明同一个量换了名字，必须统一；`NO-ANCHOR` 说明这段引文
根本没提这个指标，通常是转述时换了主语或单位。

换一篇论文时，要改的只有两处：`build_claims.py` 里的 `CLAIMS`/`CORPUS`（你的结论与底账），
以及 `claim_check.py` 里的 `CANON`/`DRIFT`（你的指标词表）。

## 五、局限

- 只覆盖**能定位到原文**的数值型结论。机理是否成立、实验是否能复现，不在范围内。
- 证据底账是人工建的，底账漏一句，C 项就会假通过；脚本只能保证底账**引文真实**，
  不能保证底账**完整**。
- 支撑信息未取得：0.28 这个端点正文没有单独出现，作者注明在 Table S1，本次只能标"证据缺口"。
- 对照臂是否对称，依赖领域常识（黏度、厚度、测试标准），脚本不判。
- 只核了一篇论文的一个阅读问题，指标只覆盖相对密度、泡孔、MFI、减重四类。
- 单位笔误（1.26 kg/m3）是靠"与同句自述矛盾 + 材料常识"判的，属于推断，不是原文事实。

## 六、来源与贡献

- **论文**：Merillas M. 等，*Upcycling post-consumer PET bottles into low-density films and
  3D-printed materials*，Materials Today Sustainability 34 (2026) 101352，
  DOI 10.1016/j.mtsust.2026.101352，CC BY-NC 4.0。本包内 `materials/paper.md` 是该文的
  机器抽取文本（59 KB），仅用于同行核对与非商业分享；所有引文均标注物理页码，
  读者可用 DOI 回到原文逐句比对。未附 PDF 原件，避免再分发原文文件。
- **工具**：`workbuddy-pdf`（PDF→Markdown，保留页锚点）。其余脚本为本包原创。
- **本次个人贡献**：阅读问题的设定、14 条结论与 15 行证据底账的抽取、两个脚本的编写、
  A/B 两次运行与全部人工复核记录。论文的方法与数据归原作者。
- **没有做的事**：没有复现实验、没有检索"首次"主张、没有取得支撑信息、
  没有对力学与热学数据做核对。

## 七、文件索引

| 路径 | 内容 |
| --- | --- |
| `README.md` | 本文（正文入口） |
| `skill/SKILL.md` | 可复用的核对 Skill：何时用、步骤、质量检查、边界 |
| `materials/paper.md` | 论文抽取文本（12 页，带 `<!-- page N -->` 锚点） |
| `materials/paper_source.md` | 论文出处、许可与页码对照 |
| `materials/extraction.log` | 抽取与清洗的真实命令输出 |
| `prompts/00_naive_summary.md` | A-without 用的单句提示词 |
| `prompts/01_extract.md` `02_bind.md` `03_condition.md` | A-with 的三步提示词 |
| `evidence/claims.csv` | 14 条结论（输入） |
| `evidence/corpus.csv` | 15 行证据底账（对照集） |
| `evidence/check.csv` `check.md` | 机器判定结果与报告 |
| `evidence/manual_verify.md` | 人工复核：4 项失败的原因与准确写法 |
| `evidence/ai_pass1_naive.md` | A-without 原始输出 |
| `evidence/ai_pass2_checked.md` | A-with 原始输出 |
| `scripts/clean_extract.py` `build_claims.py` `claim_check.py` | 运行代码 |
