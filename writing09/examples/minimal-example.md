# 最小调用示例（示意，非官方案例结果）

以下为**示意输出**，仅展示接口和流程，不代表题面固定案例的真实章节。

## 输入 case.json
```json
{"case_id":"demo-001","output_contract":["section","elements","reproducibility","questions_for_author","limitations"]}
```

## 材料片段（config.yaml）
```
lr: 1e-4
batch_size: 32
epochs: 100
seed: 42
dataset: CIFAR-10 v1
```

## 步骤
```bash
# 1. 抽取参数骨架
python3 scripts/extract_params.py config.yaml --out params.json
#    确认 unit/scope/source，设 confirmed=true

# 2. 写章节正文（section.txt），数值与参数表对齐
python3 scripts/align_params.py section.txt params.json

# 3. 复现要素检查 + 契约自检
python3 scripts/check_reproducibility.py result.json
python3 scripts/validate_result.py result.json --case case.json
```

## 示意输出 result.json（片段）
```json
{
  "case_id": "demo-001",
  "status": "partial",
  "result": {
    "section": "我们在 CIFAR-10 v1（50000 训练 / 10000 测试）上训练。采用 Adam 优化器，学习率 1e-4（config.yaml:1），批大小 32（config.yaml:2），共 100 轮（config.yaml:3），随机种子 42（config.yaml:4）。每 10 轮在验证集评估一次……[待作者确认：验证集划分比例]",
    "elements": {
      "steps": [{"input":" batches","operation":"前向+反传","output":"更新参数","condition":"验证损失连续5轮不降则早停"}],
      "parameters": [{"name":"lr","value":"1e-4","unit":"—","scope":"Adam","source":"config.yaml:1","confirmed":true}],
      "dataset": {"name":"CIFAR-10","version":"v1","size":"50000/10000","split":"待确认"},
      "baselines": [{"name":"ResNet-18","version":"torchvision 0.13","budget":"同100轮"}],
      "environment": {"gpu":"A100","framework":"PyTorch 1.13"}
    },
    "reproducibility": {
      "code_version": "git@github.com:xxx/repo.git@a1b2c3d",
      "environment": "Python 3.9, PyTorch 1.13, CUDA 11.7",
      "seed": "42",
      "command": "python train.py --config config.yaml",
      "data": "CIFAR-10 官方下载",
      "split": ""
    },
    "questions_for_author": [
      {"item":"split","question":"验证集划分比例未给出，请确认。","location":"config.yaml 无 split 字段","blocking":true}
    ],
    "limitations": ["仅在 CIFAR-10 上验证；对细粒度类别（如 bird/airplane 混淆）错误率较高。"]
  },
  "sources": [{"element":"lr","value":"1e-4","source":"config.yaml:1"}],
  "uncertainty": ["验证集划分方式缺失，已标 blocking 追问"],
  "changes": ["将正文学习率从 1e-3 修正为参数表一致的 1e-4"]
}
```

## 校验预期
- 对齐：正文数值 1e-4/32/100/42 均在参数表且有来源 → passed
- 复现：split 缺失 → partial（blocking）
- 契约：status=partial 且 uncertainty 非空 → passed

---

## 附：真实材料参数映射演示（用公开文献元数据，标注为示例）

> 本段只演示“材料事实 → sources 条目 → 正文数值”的映射形态，文献元数据取自本地 PDF 文件名/首页。
> **实际数值与 quote 必须在运行时从原文逐字提取**，此处不预填、不冒充正式案例结果。

示例材料（本地文献，非官方案例）：Li et al., 2024, "A low mobility UV-LED benzophenone photoinitiator"（题目见本地 PDF 文件名）；另一篇 Huang & Chen, 2022, "Synthesis and free radical photopolymerization of one-component type II photoinitiator based on benzophenone..."。

演示映射（参数取值须来自原文，示例仅示形态）：

```json
{
  "element": "photoinitiator",
  "value": "<运行时从原文提取的化合物/迁移率数值，示例不预填>",
  "source": "Li et al. 2024 - A low mobility UV-LED benzophenone photoinitiator.pdf",
  "locator": "p.<运行时确认> / section <运行时确认>",
  "quote": "<运行时从该页逐字提取；示例不预填>"
}
```

要点：写作方法章节时，任何迁移率、吸收波长、引发效率等数值都必须有对应 sources 条目；
材料中未报告的项写入 `questions_for_author` + `uncertainty`，标 `partial`，绝不为段落顺畅补数值。
换成组织方固定案例时流程相同——只换材料与 case_id，不复用本示例的任何数值或文字。
