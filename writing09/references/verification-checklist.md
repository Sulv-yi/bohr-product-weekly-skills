# 交付前自查清单（Verification Checklist）

## A. 写得全（六类要素）
- [ ] 步骤：有序、每步含输入/操作/输出/判断条件
- [ ] 实验设置：训练/验证/测试分离，无串台
- [ ] 参数：名称/取值/单位/作用对象/来源齐全
- [ ] 数据集：名称/版本/规模/预处理/划分/随机方式/用途
- [ ] 对照：基线+版本、同预算、指标、统计方式、重复次数
- [ ] 复现与限制：六要素 + 具体失效场景

## B. 写得准
- [ ] 正文每个数值都能在参数表找到来源
- [ ] 无串位（正文数值 == 参数表数值）
- [ ] 数据集版本与划分与材料一致
- [ ] 没有为顺畅补出的数值
- 脚本：`align_params.py`

## C. 做得着
- [ ] 代码版本 / 环境依赖 / 随机种子 / 命令 / 数据获取 / 划分方式 齐全
- [ ] 读者能按章节步骤复做
- 脚本：`check_reproducibility.py`

## D. 说得住
- [ ] 材料缺口写入 `questions_for_author`
- [ ] 不确定项写入 `uncertainty`
- [ ] 限制条件指向具体失效场景，非套话
- [ ] 状态与缺口级别一致（关键缺口 → partial）

## E. 契约
- [ ] `case_id` 一致
- [ ] `result` 含 target产出 / elements / reproducibility / questions / limitations
- [ ] `sources` 可逐条回溯
- [ ] `changes` 记录修订
- 脚本：`validate_result.py`

## 脚本对应
| 清单项 | 脚本 |
|---|---|
| B 数值对齐 | `align_params.py` |
| C 复现要素 | `check_reproducibility.py` |
| E 契约 | `validate_result.py` |
| A 齐全度 / D 具体性 | 人工复核（脚本无法判定语义） |
