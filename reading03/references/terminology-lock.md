# 术语锁定（Terminology Lock）

## 目标
同一术语在标题、摘要、正文、图注、表头、结论中始终使用同一译名。术语表必须**被脚本执行回扫**，而不是只写在提示词里。

## 抽取候选术语
`build_glossary.py` 用三类规则抽取（可叠加）：
1. 全大写缩写：`API`, `CNN`, `SVM`, `NMR`, `DFT`
2. 连写复合词：`state-of-the-art`, `machine-learning`, `X-ray diffraction`
3. 高频定冠词短语：`the proposed method`, `attention mechanism`

抽取结果是**候选**，需要译者确认译名。不要把每个候选都当术语——只锁定有领域含义、且全篇反复出现的词。

## 术语表格式（glossary.json）
```json
{
  "terms": [
    {"term": "solid electrolyte interphase", "translation": "固体电解质界面膜",
     "scope": "全文", "note": "简称 SEI 时沿用同一译名"},
    {"term": "SEI", "translation": "SEI 膜", "scope": "全文", "note": "保留英文缩写"}
  ]
}
```
字段：
- `term`：原文术语（区分大小写）
- `translation`：唯一译名，**确定后不得逐段改动**
- `scope`：适用范围（全文 / 某章节）
- `note`：缩写、同义词归并说明

## 翻译阶段的执行规则
1. 翻译每段前，先查术语表；命中术语**必须**用锁定译名。
2. 遇到术语表未收录、但看似专业的词，先加入候选，不得临时自造多个译名。
3. 同一英文术语的不同形态（单复数、时态）沿用同一译名词根。
4. 缩写首次出现给全称+译名，后续沿用；不要一句一变。

## 回扫验证
`verify_translation.py --glossary glossary.json` 检查：
- 术语表中每个 `term` 在译文里是否出现对应 `translation`
- 是否出现该术语的**其他常见误译**（通过 `note` 里的别名清单）
- 出现漂移 → 列出 `source_id` / 术语 / 锁定译名 / 实际译名，判 `term_drift` 失败

## 常见失败
| 失败模式 | 例 | 处理 |
|---|---|---|
| 同术语多译名 | "attention" 一段译"注意力"一段译"关注" | 锁定一个，全篇回填 |
| 缩写忽译忽留 | "SEI" 一段译"固体电解质界面膜"一段留"SEI" | 按 `note` 统一 |
| 图注漏锁 | 正文锁了译名，图注用另一个 | 图注纳入回扫范围 |
| 表头漂移 | 表头术语与正文不一致 | 表头成段单独校验 |
