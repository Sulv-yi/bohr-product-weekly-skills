# 最小调用示例（示意，非正式案例结果）

> 下面的输入是示意数据，输出只展示字段形态，**不代表平台任何案例的真实结果**。

## 输入

`/input/case.json`

```json
{"case_id": "demo-001", "task": "文献文档解析：读取论文并按要求输出",
 "material": "/input/paper.pdf",
 "output_contract": {"fields": ["<本题要求的字段>"]}}
```

## 调用

```bash
python scripts/doctext.py /input/paper.pdf --out work/doc.json
```

## 输出（节选，示意）

```json
{"backend": "pypdf",
 "stats": {"pages": 9, "paragraphs": 143, "headings": 6, "captions": 21},
 "sections": [{"id": "p001-08", "page": 1, "title": "1 | INTRODUCTION", "level": 1}],
 "paragraphs": [{"id": "p001-09", "page": 1,
                "text": "Photopolymerization has received ...",
                "char_start": 0, "char_end": 320,
                "section": "1 | INTRODUCTION"}]}
```

然后按 `output_contract` 填写 `/app/output/result.json`，每条证据给
`page + paragraph_id + quote`，最后跑：

```bash
python scripts/readwork.py verify /app/output/result.json --doc work/doc.json
```
