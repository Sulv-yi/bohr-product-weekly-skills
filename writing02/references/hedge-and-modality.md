# 限定词与情态强度守恒表

润色中最常见的"改坏"是限定强度漂移。下表给出强度等级，**跨级替换一律禁止**；同级替换也要有明确的语言学理由并写入 change_log。

## 一、确定性强度（由弱到强）

| 等级 | 英语典型形式 | 中文典型形式 |
|---|---|---|
| L0 否定 | no, not, none, never | 不、未、无、没有 |
| L1 可能 | may, might, could, possibly, suggest | 可能、或许、提示、表明 |
| L2 倾向 | tend to, likely, appear to, seem to, indicate | 倾向于、似乎、看起来、指示 |
| L3 一般 | generally, usually, often, typically | 通常、一般、往往 |
| L4 强断言 | is, are, demonstrate, clearly, definitely | 是、证明、显然、必定 |
| L5 全称 | all, every, always, invariably, must | 所有、每个、总是、必须 |

规则：
- L1→L4（suggest→demonstrate / 可能→证明）= **加强**，禁止
- L4→L1（is→may be / 是→可能是）= **削弱**，禁止
- L3→L2（usually→tend to）= 跨级，禁止
- 同级内 may→might 属弱微调，仍需记录理由

## 二、数量与范围限定

| 类型 | 不可改示例 | 常见破坏 |
|---|---|---|
| 近似 | approximately 30%, about 30%, 约30% | 去掉 approximately → 变成精确值 |
| 上界下限 | at least, at most, up to, more than, 至少/至多/超过 | up to 5% → 5% |
| 比例词 | most, some, several, a few, majority, minority | most→all、some→most |
| 频率 | occasionally, rarely, frequently | rarely→occasionally（强度变了） |
| 条件 | if, when, provided that, under ... conditions, 在…条件下 | 删除条件从句 |

## 三、逻辑关系

| 关系 | 保持要求 |
|---|---|
| 因果 | cause / lead to / result in ≠ correlate with / be associated with；不得互换 |
| 时序 | after/before/subsequently 不得改为同时关系 |
| 对比 | whereas / however / in contrast 的对比对象不得改变 |
| 目的 | to / in order to / for 的目的状语不得改成结果 |
| 否定范围 | "not all" ≠ "none"；"did not significantly increase" 不得写成 "significantly decreased" |

## 四、引用与图表指向（视为不可变 token）

- 引用编号 `[3]`、`(Smith, 2020)`、上标¹、Ref. 12 —— 逐字保留，包括顺序
- 图表指向 `Fig. 2`、`Table 1`、`图3`、`表2` —— 逐字保留
- 数字 + 单位组合（ `5 mg/kg`、`37 °C`、`p < 0.05`、`n = 12` ）—— 整体保留，不改有效数字、不改单位符号、不改不等号方向

## 五、守恒自检清单

改完每一句后逐条打勾：
- [ ] 限定词等级与原句相同（查表）
- [ ] 否定词数量与范围相同
- [ ] 数字、单位、有效数字、不等号方向相同
- [ ] 引用编号与图表指向逐字相同
- [ ] 因果/相关关系未互换
- [ ] 条件从句未删除
- [ ] 术语使用 term_map 中的统一写法

任何一项打不上勾，该句判 failed，回到最小编辑重做。
