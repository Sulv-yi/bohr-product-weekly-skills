# 异常与边界处理

| 情形 | 识别信号 | 处理 | status |
|---|---|---|---|
| 扫描件/无文字层 | probe: has_text_layer=false | 说明需 OCR，不臆造原文 | partial |
| 原文无法访问 | 路径不存在/读取失败 | 说明访问失败与人工接管位置 | unable |
| 证据跨图表 | 数据在 Fig/Table 中 | 位置写图表编号，内容为图片则 type=indirect + uncertainty | partial |
| 断言找不到支撑片段 | 遍查原文无逐字支持 | 不编造证据，标证据不足并说明 | partial |
| 断言与证据冲突 | 证据片段与断言方向相反 | 两者都登记，uncertainty 写材料冲突 | partial |
| 来源字段缺失 | authors/year/identifier 无 | 写 unknown，进 uncertainty | partial |
| 多版本论文 | v1/v2 结论不同 | 每条断言标 version，分开记录 | partial |
| 非中文论文 | 英文原文 | term 用原文，中文译名入别名说明 | success |
| 任务越界 | 要求编造来源/无材料下结论 | refused + 原因 | refused |

## 与 verify_nanopub.py checks 对照

- `granular=warn` → 复合断言未拆，回第 2 步拆分。
- `aligned=failed` → 证据片段不在原文或 type 非法，回第 3 步。
- `traceable=failed` → 来源/溯源字段缺失，回第 4 步。
- `machine=failed` → relation 越词表/id 重复/不可序列化，回第 2/5 步。

## 与 export_jsonld.py 报错对照

- `无 head 节点` → 三图引用不完整，检查 nanopub id。
- `assertion 缺 X` / `provenance source 缺 X` → 补字段。
- `不可序列化` → 检查是否有非 JSON 类型（集合、日期对象等）。
