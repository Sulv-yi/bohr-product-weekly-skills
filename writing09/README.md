# 方法与实验章节写作 Skill

面向 Bohrium 产品周赛「写作09｜方法与实验章节写作」。把散落的实验材料整理成**可复现、可追溯**的方法与实验章节。

## 设计主线
题面四个关注点 → 本 Skill 的可执行能力：

| 题面关注 | 本 Skill 机制 | 对应脚本/文档 |
|---|---|---|
| 写得全 | 六类要素抽取清单（步骤/设置/参数/数据/对照/复现限制） | `element-extraction.md` |
| 写得准 | 正文数值与参数表对齐，无来源数值判失败 | `align_params.py` / `parameter-alignment.md` |
| 做得着 | 复现六要素完整性检查 | `check_reproducibility.py` / `reproducibility.md` |
| 说得住 | 缺口追问清单 + 具体失效场景限制 | `gap-questioning.md` |

## 目录
```
SKILL.md                        触发条件、6 步工作流、输入输出、异常处理
references/
  element-extraction.md         六类要素抽取（带来源）
  parameter-alignment.md        正文数值与参数表对齐、三类错误
  reproducibility.md            复现六要素、对照可比性、限制写法
  gap-questioning.md            缺口追问清单与状态规则
  verification-checklist.md     交付前逐条自查
scripts/
  extract_params.py             从配置/日志抽取参数骨架
  align_params.py               正文数值 vs 参数表，抓无来源/串位
  check_reproducibility.py      复现六要素完整性
  validate_result.py            输出契约自检
examples/minimal-example.md     最小输入输出示例（示意）
```

## 依赖与运行
- Python 3.9+，全部仅用标准库
- 路径相对本目录，不依赖任何个人文件；未打包测试答案
```bash
python3 scripts/extract_params.py config.yaml --out params.json
python3 scripts/align_params.py section.txt params.json
python3 scripts/check_reproducibility.py result.json
python3 scripts/validate_result.py result.json --case case.json
```

## 能力边界（如实说明）
- 脚本捕获**可机械判定**的硬伤（数值无来源、复现要素缺失、契约字段缺、状态与缺口不一致）
- 章节齐全度、限制条件真实性、语义恰当性需人工复核，写入 `uncertainty`
- 不为顺畅补数值；材料缺口标 `questions_for_author` 并降状态为 `partial`

## 评分对应
- 实际效果 40：六要素齐全成稿 + 数值可追溯
- 使用增益 25：齐全度/准确性/条件一致性的对照
- 创新增益 15：要素抽取→参数对齐→缺口追问的闭环能力
- 可靠体验 10：多材料形态、异常降级、追问清单
- 生态贡献 10：规则文档 + 可复用脚本 + 参数表/追问清单模板

注：本题题面未设 GitHub 公开链接附加分（与写作08/02 一致）。仓库链接见 `GITHUB_URL.txt`，仅用于复用与查阅。
