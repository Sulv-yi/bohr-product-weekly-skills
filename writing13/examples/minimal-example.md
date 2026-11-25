# 最小调用示例（示意，非真实案例结果）

> 本页为接口与流程示意，不代表任何正式测试案例的答案或评分。

## 输入（假设 /input/case.json）

```json
{
  "case_id": "demo-latex-001",
  "task": "修复给定 .tex 工程的编译错误，保留公式表格引用，交付可编辑源码与复现记录。",
  "material": "/input/project/",
  "engine": "pdflatex",
  "output_contract": ["artifacts", "source_map", "build", "reproduction"]
}
```

## 调用链

```bash
# 0. 探查工程与引擎
python scripts/probe_project.py /input/project/ --out /app/work/project.json --engine pdflatex

# 1. 静态预检（无需引擎）
python scripts/static_check.py /input/project/ --out /app/work/static_check.json --strict

# 2. 多轮编译 + 全量报错解析
python scripts/compile_and_parse.py /input/project/ --out /app/work/compile_report.json \
    --engine pdflatex --rounds 3 --main main.tex
# 若环境无引擎但已有日志：--log /app/work/compile.log

# 3. 按 compile_report.errors 逐条定位修复 .tex，重编到 error_count=0 且 converged=true

# 4. 写 /app/output/result.json（artifacts/source_map/build/reproduction）

# 5. 契约自检
python scripts/verify_result.py /app/output/result.json --case /input/case.json \
    --static /app/work/static_check.json --compile /app/work/compile_report.json
```

## 示意输出（节选）

```json
{
  "case_id": "demo-latex-001",
  "status": "success",
  "result": {
    "artifacts": [{"path":"main.tex","kind":"editable_source"}],
    "changed_files": ["main.tex"],
    "source_map": [{"claim":"公式(2) 的阈值 0.85","source":"原文 §3.1 Eq.(2)","change":"保持数值，改为 align 环境并加 label"}],
    "build": {"compile_status":"success","converged":true,"error_count":0},
    "reproduction": {"engine":"pdflatex","engine_version":"TeX Live 2023","template":"article",
      "packages":{"amsmath":"v3.4"},"fonts":["Latin Modern"],
      "command":"latexmk -pdf main.tex","rounds":3}
  },
  "sources": [{"source_id":"s1","location":"§3.1 p.4","quote":"（原文片段示意）"}],
  "uncertainty": [],
  "changes": ["fix undefined \\eqref by adding \\label{eq:2}", "switch eqnarray to align"]
}
```

## 破坏性对照（应报错）

- 交付物只写 `paper.pdf` 无 `.tex` → `usable_source` failed。
- `compile_report.status=failed` 但 `result.status=success` → 编译一致性 error。
- `reproduction` 缺 `engine`/`command`/`rounds` → 复现要素缺失 error。
- `static_check.status=failed` 但声明 success → 契约 error。

---

## 附：成稿链路最小示例（示意，非正式案例结果）

> 以下命令与输出仅演示接口和判定形态，`case_id`、章节名与数值均为示例，
> **不代表任何正式案例，也不得作为预制答案使用**。真实运行时以 `/input/case.json` 为准。

```bash
# 1) 建结构（章节取自 case.required_sections，没有则用通用科研结构）
python scripts/build_manuscript.py --case /input/case.json --out /app/output --main main.tex
# -> main.tex / refs.bib / manuscript_plan.json

# 2) 按 manuscript_plan.json 逐节写实（这一步是 Agent 的主要工作，不能跳过）

# 3) 成稿硬门槛
python scripts/check_manuscript.py /app/output/main.tex --case /input/case.json --bib /app/output/refs.bib
```

空骨架会被判失败，形如：

```json
{"status": "failed",
 "errors": ["仍是 build_manuscript 生成的空骨架：需逐节写实后删除该提示",
            "以下章节实质篇幅不足 120 字: Introduction(0字); Method(0字)",
            "摘要实质篇幅不足 40 字",
            "表格只有表头骨架，没有真实数据行（当前最多 0 行，需 >=2 行）"]}
```

逐节写实后应为：

```json
{"status": "passed",
 "stats": {"sections": 3, "total_real_chars": 552,
           "section_chars": {"Introduction": 169, "Method": 136, "Results": 153},
           "cite_keys": ["carmenini2025"], "equations": 1, "tables": 1}}
```

最后 `verify_result.py` 还会复核：`status=success` 时必须定位得到这份 .tex、成稿过门槛、
`source_map` ≥3 条、`reproduction` 要素齐全。少任何一项都会被判 failed 并给出具体缺什么。
