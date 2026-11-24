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
