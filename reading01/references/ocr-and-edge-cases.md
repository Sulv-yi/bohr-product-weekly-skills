# 扫描件、OCR 与异常输入

## 判定扫描件

probe 结果出现以下任一即进入 OCR 分支：

- `has_text_layer=false`
- 某页 `char_count < 50` 但 `image_count >= 1`
- `image_only_pages` 非空

## OCR 流程

1. 优先 `ocrmypdf --output-type pdf` 生成带文字层的副本，写到 `/app/work/`，**不修改原始输入**。
2. 无 ocrmypdf 时用 `pdftoppm` 转图 + Tesseract 识别，语言包按文档语言选择（`eng` / `chi_sim` / `eng+chi_sim`）。
3. 预处理：300 DPI、去噪、纠偏（deskew）、二值化；低对比度页面先增强。
4. OCR 后仍走标准 extract 流程，但所有证据 `quote` 标注 `"source": "ocr"`，并在 uncertainty 注明 OCR 置信度与可能的错字。

## OCR 后处理校验

- 数字/单位：`0/O`、`1/l/I`、`5/S` 易混，结合上下文与单位合理性核对。
- 表格：OCR 常丢竖线，按文本对齐重建；无法确认的列归属写入 uncertainty。
- 公式：OCR 对本 skill 最难还原，保留图像截图作为证据，符号以 LaTeX 近似并标注不确定。

## 其他异常

| 情况 | 处置 |
|---|---|
| 加密 PDF | 无密码 → `blocked`；有密码由 case.json 提供时先解密副本 |
| 文件损坏 | 报告 `blocked`，保留原始错误信息 |
| 字体乱码 | 保留原始片段 + 尝试 ToUnicode 映射；失败写入 uncertainty |
| 页码错乱 | 物理页序为准，另记印刷页码映射 |
| 超长文档 | 分块处理，先保证核心章节与证据完整，其余标 partial |
