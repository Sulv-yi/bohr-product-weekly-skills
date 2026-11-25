# 人工复核记录（脚本判不了的部分）

对象：`evidence/check.md` 的 4 个需处理项 + 3 项脚本不覆盖的跨段检查。
每条都回到 `materials/paper.md` 的页码锚点复核，引文逐字取自原文。

---

## 一、4 个机器判定项的原回复核

### C02（PET_B 相对密度 0.2–0.28）· CONFLICT

- 原文 p1：「relative densities of 0.2 to 0.28」
- 原文 p7：「in PET_B sample the minimum in relative density is obtained at different
  foaming temperatures depending on the saturation pressure: at 220 °C for psat = 15 MPa,
  with a value of 0.35; and at 200 °C for psat = 30 MPa, reaching a value of 0.20」
- 判断：不是笔误，是**条件被压缩**。0.35 出现在 15 MPa 支路，0.28 这个端点正文没有单独出现
  （作者注明完整数值在支撑信息 Table S1，本次没有 S1）。所以摘要区间只对 30 MPa 支路成立。
- 准确写法：「30 MPa 饱和、200 ℃ 发泡时 PET_B 相对密度为 0.20；15 MPa 支路最低为 0.35。」

### C03（PET_C 泡孔 5–18 μm）· CONFLICT

- 原文 p1：「cell sizes from 5 to 18 μm」
- 原文 p9：「PET_C has two clear primary cell sizes in 3 and 6 μm, but it has some even
  bigger cells (some up to 20 μm) due to the size of some impurities」
- 判断：摘要的区间把**主分布的下端 3 μm 切掉了，上端 20 μm 也截断了**。属于分布描述被简化，
  不是造假。
- 准确写法：「PET_C 主分布 3 μm 与 6 μm，另有因杂质形成的大孔至 20 μm。」

### C09（减重 40% 的口径）· FAIL：DRIFT(weight reductions)

- 原文 p10：「a reduction of more than 40% in relative density in the 3D printed
  materials has been achieved」
- 原文 p10（讨论）：「weight reductions of up to 40% and cell sizes around 2 μm, can be
  transferred to 3D-printed parts」
- 判断：前者是相对密度（ρr）降幅，后者写成"重量降幅"。相对密度按定义等于 ρf/ρs，
  在体积不变的前提下才等于重量降幅；而同一页明确写了发泡时"dimensional expansion occurs"，
  体积变了，两个说法不能互换。
- 准确写法：引用 ρr 降幅 >40%；若要换算成减重，需给出膨胀后的体积，原文没给。

### C10（1.26 kg/m3）· FAIL：NO-ANCHOR(relative density)

- 原文 p10：「This 3D printed cap presents a density of 1.26 kg/m3, slightly lower than
  PET_B in film form」
- 判断：两个问题叠加。一是引文用的是 "a density of"，不是 relative density（口径锚点缺失）；
  二是单位。PET 固体密度在 1.3 g/cm³ 量级，薄膜态 rPET 约 1.33 g/cm³，1.26 只比它略低，
  与"slightly lower"自洽；若真是 1.26 kg/m³，则是固体密度的千分之一，与同句"略低于薄膜"
  直接矛盾。故单位应为 g/cm³（原文笔误）。
- 准确写法：「3D 打印帽固体密度 1.26 g/cm³（原文写作 kg/m3，按同句"略低于薄膜态"判断为笔误）。」

---

## 二、3 项脚本不覆盖、必须人读的检查

### 1. 摘要的比较级有没有同条件证据 → 没有

- 摘要 p1：「PET_B shows cell sizes close to 2 μm together with relative densities of
  0.2 to 0.28, outperforming virgin PET」
- 正文 p6：「in PET_V, the minimum relative density is obtained at Tf = 200 °C, irrespective
  of the saturation pressure, reaching values of 0.16 and 0.18 at 15 MPa and 30 MPa」
- 判断：outperform 在**密度**维度站不住（原生料 0.16 < PET_B 0.20），只在**泡孔尺寸**维度
  站得住。摘要用一个词包了两个指标，且其中一个方向相反。
- 影响：若把"回收料优于原生料"写进方案论证，会被同行直接反驳。

### 2. 对照臂规格是否对称 → 不对称，且作者自己说明了

- p2：PET_B「intrinsic viscosity of 0.70-0.80 dl/g」；PET_V「with low viscosity,
  0.63 dl/g, was selected as a rheological reference material」
- p4 表 1：MFI 为 PET_V 46.70、PET_B 11.52、PET_C 26.26（g/10 min）
- p2 作者原话：「Using a typical bottle-grade PET (0.80 dl/g) would result in significantly
  higher melt strength, which could bias the interpretation of foaming behavior」
- 判断：这是**刻意的对称化尝试**——为了不让黏度差成为解释变量，作者选了低黏度原生料。
  代价是：实验臂（PET_B，0.70–0.80）的熔体强度本来就高于对照臂（0.63），
  于是"回收料泡孔更细"里混进了黏度效应，不能全部归因于"回收料本身"。
- 准确写法：「在黏度匹配的低黏度原生料参照下，PET_B 泡孔更细；该对照不能代表瓶级原生料。」

### 3. "首次"有没有检索范围 → 没有

- p1：「we demonstrate for the first time that rPET 3D-printed components can be foamed
  while preserving their overall geometry」
- p2：「its application to recycled PET—particularly mixed-color post-consumer streams and
  3D-printed parts—has not been reported to date」
- 判断：两处一致，但全文没有给出检索的数据库、时间窗与关键词，也没有列出被排除的相近工作。
  属于**无法由本文材料核验**的主张。
- 处理：转述时写「作者称首次」。若要当作事实使用，需自己补一次检索（本次未做）。

---

## 三、本次复核没有覆盖的部分（如实记录）

- 支撑信息 Table S1 未取得：0.28 这个端点无法核到原始表格。
- 力学性能、热导率：本次只核了密度、泡孔、MFI、黏度四类指标，其余未逐条核。
- 只核了一篇论文的一个阅读问题（"结论是否可外推"），不代表这套流程能替代通读。
- 表 1 的数值来自抽取后的表格文本，未与 PDF 图像逐格比对（`materials/paper.md` 中表 1 保留
  了原始 `<br>` 结构，可人工复核）。
