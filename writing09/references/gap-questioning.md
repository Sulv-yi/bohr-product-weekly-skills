# 缺口追问（Gap Questioning）

## 原则
材料不足时**显式追问，不自行补写**。这对应题面的"说得住"：缺口与不确定处被标出并交作者确认。

## 何时追问
- 参数为空白或标 `N/A`、`?`、`TBD`
- 数据集版本 / 规模 / 划分方式缺失
- 同一参数在不同材料里不一致（配置 vs 日志 vs 代码）
- 随机种子未记录
- 基线版本或对照预算不明
- 步骤之间的判断条件缺失（不知道何时应停止/转向）
- 材料是扫描件/图片，关键数值无法读取

## 追问清单格式（questions_for_author）
```json
[
  {"item": "random_seed", "question": "训练随机种子未记录，请提供以便复现。",
   "location": "config.yaml 未见 seed 字段", "blocking": true},
  {"item": "dataset_version", "question": "数据集版本在材料中出现 v1/v2 两种，请确认使用哪版。",
   "location": "data.md vs log.txt", "blocking": true}
]
```
`blocking: true` 的追问未解决时，状态保持 `partial`，对应章节段落用占位标注（如"[待作者确认：随机种子]"），不编造。

## 追问与状态
| 情况 | status |
|---|---|
| 无缺口，六要素齐全 | `success` |
| 有非关键缺口（不影响理解） | `success`，缺口写入 uncertainty |
| 有关键缺口（影响复现/正确性） | `partial`，blocking 追问 |
| 材料整体不可用 | `unable` |

## 反例（禁止）
- 为了让章节完整，自己填一个"合理"的种子或版本
- 把"[待确认]"删掉让段落看起来更顺
- 用"经验值""默认值"掩盖来源缺失
