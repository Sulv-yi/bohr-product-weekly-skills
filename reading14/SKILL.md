---
name: nanopublication-extractor
description: 面向真实科研论文的 Nanopublication 抽取 Skill。把段落拆成可独立判断真假的原子断言（subject-relation-object），为每条绑定最小充分证据片段与原文位置，补全论文/作者/年份/版本/标识符溯源链，并导出可被下游直接解析的 JSON-LD。当任务要求做断言拆解、证据绑定、来源元数据、知识结构化或 nanopublication 生成时使用；关系走受控词表，证据必须回原文逐字匹配，证据不足/字段缺失/材料冲突如实标注，不臆造来源。
---

# Nanopublication 抽取（拆得细 · 对得上 · 追得回 · 读得懂）

把论文段落变成**可机器读取、可逐条回溯**的 nanopublication 结构，而不是把整段摘要塞进一个字段。四个性质互相咬合：

- **拆得细**：一段结论拆成若干条各自可判断真假的原子断言（subject–relation–object），保留条件与限定范围，处理并列与因果结构。
- **对得上**：每条断言关联最小充分证据片段并能指出原文位置，区分直接证据与间接推论。
- **追得回**：断言→证据→论文→作者→年份→版本→标识符链路完整，他人可回到原文。
- **读得懂**：导出符合约定字段与序列化形态（JSON-LD）的结构，下游可直接解析，无需人工清洗。

## 适用 / 不适用

**适用**：真实论文段落→断言拆解、证据绑定、来源元数据、断言质量检查、结构化导出、nanopublication 生成。

**不适用**：只要一段通顺摘要；无原文定位需求的通俗改写；要求凭空补作者/年份/标识符的场景（本 Skill 宁可标 unknown 也不臆造来源）。

## 输入

运行时读 `/input/case.json` 与 `/input/task.md`（若存在）。字段以实际文件为准：

| 字段 | 含义 | 处理 |
|---|---|---|
| `case_id` | 案例标识 | 原样写入 result.json |
| `task` / `question` | 具体任务 | 决定侧重拆解/绑定/核验/导出 |
| `material` / `pdf` / `files` | 材料路径 | **读真实文件**，不从题名猜内容 |
| `output_contract` | 必须输出字段 | 逐字段原样覆盖 |

工作目录 `/app/work`，最终 `/app/output/result.json` + JSON-LD 导出。

## 核心原则

1. **一条一断**：一条 nanopub 只含一个 subject/relation/object 核心；复合句拆开，别塞进一个字段。
2. **证据逐字**：证据片段必须是原文逐字片段（规范化后可匹配），位置精确到页码/段落/图表/字段。
3. **关系受控**：relation 必须命中 `assets/relation_vocab.json` 的 canonical；同义表述归一，相关≠因果。
4. **溯源完整**：来源元数据逐项记录，缺失写 unknown 并进 uncertainty，不编造。
5. **区分证据**：直接证据与间接推论分开标（type=direct/indirect），因果主张不能只靠间接。
6. **机读可解析**：导出 JSON-LD 三图结构（assertion/provenance/pubinfo），可 JSON 序列化，字段齐全。
7. **早存增量**：先落一版 result.json（哪怕 partial），再逐条改进，每步记 change。

## 工作流

### 第 0 步 · 识别边界
读 case.json / task.md，确认材料类型、拆解粒度、输出契约。PDF 先 `scripts/probe_pdf.py` 探查；无文字层/扫描件→标 partial 说明需 OCR，不臆造原文。

### 第 1 步 · 预切候选断言（拆得细）
```bash
python scripts/split_claims.py <原文文本|blocks.json> --out candidates.json
```
按句切分并标出"疑似复合/含关系动词"的候选，产出稳定 `claim_id`。这只是骨架，subject/relation/object 必须按原文核定。

### 第 2 步 · 逐条核定断言（拆得细）
对每条候选，填 `assertion`：
```json
{"subject":"Method M","relation":"achieves","object":"92.5% accuracy",
 "claim_text":"Method M reaches 92.5% accuracy","conditions":"on dataset D",
 "confidence":"high","confidence_basis":"直接证据，原文逐字数值"}
```
- relation 从 `assets/relation_vocab.json` 取 canonical（achieves / outperforms / causes / correlates_with / requires / limits ...），别名映射到 canonical。
- 复合句（"达到92.5%，优于基线5%，耗时1.2s"）拆成三条。
- 因果/增减断言必须写 conditions，防止断言过宽。

### 第 3 步 · 绑定最小证据（对得上）
每条断言在 `provenance.evidence` 登记最小充分片段：
```json
{"text":"Method M reaches 92.5% accuracy","location":"p.3 ¶2 / Eq.(2)","type":"direct"}
```
- `text` 用原文逐字片段（规范化后需能在材料匹配）。
- `location` 精确到页/段/图表/字段，能到段不到章。
- `type` 为 direct / indirect；间接推论不能冒充直接证据。

### 第 4 步 · 补溯源链（追得回）
`provenance.source` 逐项填：`paper` / `authors` / `year` / `version` / `identifier`（DOI 等）/ `data_source`。
缺失写 `"unknown"` 并进 `uncertainty`；不编造作者、年份或 DOI。

### 第 5 步 · 导出与核验（读得懂）
```bash
# 核心四性质核验
python scripts/verify_nanopub.py result.json --material <原文|blocks.json> \
    --vocab assets/relation_vocab.json --case /input/case.json --out verify.json [--strict]

# JSON-LD 导出 + 可解析性校验
python scripts/export_jsonld.py result.json --out /app/output/nanopubs.jsonld
# 或仅校验：--check-only

# 契约自检
python scripts/validate_result.py result.json --case /input/case.json
```
任一项 failed → 回对应步骤修正。verify 的 checks 直接对应四问：granular / aligned / traceable / machine。

## 输入输出

输出 `/app/output/result.json` + `nanopubs.jsonld`：

```json
{
  "case_id": "...",
  "status": "success | partial | unable | refused",
  "result": {
    "nanopublications": [
      {
        "id": "np-001",
        "assertion": {"subject":"...","relation":"achieves","object":"...",
          "claim_text":"...","conditions":"...","confidence":"high","confidence_basis":"..."},
        "provenance": {
          "evidence": [{"text":"原文逐字片段","location":"p.3 ¶2","type":"direct"}],
          "source": {"paper":"...","authors":["..."],"year":"2020","version":"v1",
            "identifier":"DOI:...","data_source":"..."}
        },
        "publication_info": {"created_by":"...","created_at":"..."}
      }
    ]
  },
  "sources": [{"source_id":"s1","location":"p.3 ¶2","quote":"..."}],
  "uncertainty": ["未报告...", "无法判断...", "材料冲突..."],
  "changes": ["..."]
}
```

`status`：`success` 四性质全满足；`partial` 部分完成（必须写 uncertainty）；`unable` 材料不可用；`refused` 任务越界。**不预置答案、不编造来源、不虚构分数。**

## 异常处理

| 情形 | 处理 | status |
|---|---|---|
| 扫描件/无文字层 | 说明需 OCR，不臆造原文 | partial |
| 原文无法访问 | 说明访问失败与需人工接管位置 | unable |
| 证据跨图表/图片化 | 保留图表编号，正文写"图片内容未识别"，证据标 indirect | partial |
| 断言找不到支撑片段 | 不编造证据；标该断言证据不足并说明 | partial |
| 断言与证据冲突 | 两者都登记，uncertainty 写"材料冲突" | partial |
| 字段缺失/来源缺 | 写 unknown 并进 uncertainty，不臆造 | partial |

## 脚本

- `scripts/split_claims.py` — 段落预切候选断言骨架（拆得细）
- `scripts/verify_nanopub.py` — 四性质 + 证据/关系/溯源硬损伤核验（核心）
- `scripts/export_jsonld.py` — JSON-LD 三图导出与可解析性校验（读得懂）
- `scripts/validate_result.py` — 输出契约与状态自检
- `scripts/probe_pdf.py` — PDF 文字层/页数/语言探查（多级降级）

依赖：Python 3.9+ 标准库；PDF 可选 PyMuPDF/pdfplumber/pdftotext（缺失走降级链）。

## 资产与限制

`assets/relation_vocab.json` 为关系受控词表（canonical + 别名 + 方向 + 质量标记），`examples/claim-samples-20.md` 为 20 条断言字段样例（非真实案例答案）。详见 references/。

`verify_nanopub.py` 捕获可机械判定的硬损伤（证据不在原文、relation 越词表、溯源字段缺失、id 重复、复合断言提示），但"证据是否真的支持断言""主体是否混淆"等语义判断仍需人工/评审复核，已在 uncertainty 中如实声明。Skill 不依赖作者个人文件、不提交预制答案。
