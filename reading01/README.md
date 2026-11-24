# 科研 PDF 结构化解析 Skill

面向「文献文档解析」赛题的参赛 Skill。把科研 PDF 解析成结构化、可回溯原文的结果，供 Agent 在评测环境中调用。

## 目录

```
SKILL.md                          主文件：触发条件、工作流、输入输出、异常处理
README.md                         本说明
GITHUB_URL.txt                    作品公开链接（需提交前填写真实地址）
scripts/
  probe_pdf.py                    探查版式/文字层/加密/栏数
  extract_blocks.py               带坐标的块提取 + 阅读顺序修正
  validate_result.py              输出契约与证据一致性校验
references/
  reading-order.md                多栏、跨页、页眉页脚规则
  table-reconstruction.md         表格行列/合并/跨页续表
  structure-and-formula.md        章节层级/题注/公式/参考文献
  evidence-and-uncertainty.md     证据格式与不确定性标注
  ocr-and-edge-cases.md           扫描件与异常输入
examples/
  minimal-example.md              最小调用示例（示意，非官方案例）
```

## 设计与评分对应

| 评分维度 | 本 Skill 的应对 |
|---|---|
| 实际效果 40 | 带坐标提取 + 多栏顺序修正 + 表格/章节/公式结构化 + 逐条证据定位 |
| 使用增益 25 | 脚本自动化确定性工作（探查、提取、校验），Agent 专注语义，减少重跑与人工校对 |
| 创新增益 15 | 阅读顺序与证据绑定的可复用规则集、OCR 降级路径、quote 逐字回溯校验 |
| 可靠体验 10 | 五后端自动降级（含纯标准库兜底）、加密/扫描/乱码/跨页等异常分支、validate 自检 |
| 生态贡献 10 | 完整文档、规则集与脚本可复用、最小示例 |

## 依赖与安装

- Python 3.9+，**零依赖也能运行**
- 推荐：`pip install pymupdf`
- 可选：`pip install pdfplumber pypdf`；OCR：`pip install ocrmypdf` + 系统 tesseract-ocr、poppler-utils
- 降级顺序：PyMuPDF → pdfplumber → pdftotext → `scripts/pdf_fallback.py`（纯标准库）。兜底后端支持字面串与十六进制串，但不解析 CID/ToUnicode、不还原版面坐标、不识别表格图片，能力边界须在结果中如实声明。探测结果写入 probe.json，不依赖未声明的个人文件。

## 评测环境使用

1. 平台把 Skill 安装到 `/skills/weekly-skill`，用官方 DeepSeek Harness 在 3 个固定案例上运行。
2. 输入 `/input/case.json` + `/input/task.md`；脚本用到 `<skill_dir>` 的位置以运行时实际安装路径为准（见下方"路径解析"）。
3. 工作目录 `/app/work`，最终写 `/app/output/result.json`（含 `case_id` 及 `output_contract` 全部字段）与可选可编辑产物/预览。
4. 运行预算：64 次模型请求、900 秒、每响应 16384 tokens。先落完整初版，再增量改进。

**路径解析**：`SKILL.md` 中的 `<skill_dir>` 指本 Skill 的安装根目录。评测环境下平台会给出实际位置；若未显式给出，脚本位于安装根的 `scripts/` 子目录，可先用 `find / -name probe_pdf.py 2>/dev/null` 定位。

## 提交前检查

```bash
python scripts/validate_result.py <示例result> --blocks <示例blocks> --case <示例case>
```

资源约束：≤50 个 UTF-8 文本文件，单个 ≤500KB、总量 ≤2MB，禁止符号链接。当前目录远低于上限。

## GitHub 附加分（最高 +5）

在 `GITHUB_URL.txt` 第一行写作品公开链接（无需登录可见），第二行可选写提交目录中的相对路径。提交前用未登录浏览器打开确认可见。
