# 结论核对报告

- 结论条数：14
- PASS：10
- FAIL（引文/数值/口径对不上）：2 —— C09, C10
- CONFLICT（底账里有越出声明区间的数值）：2 —— C02, C03
- 底账错误：0

## 需要处理的条目

### C02 · CONFLICT
- 命题：PET_B / relative_density = 0.2,0.28（声明 p1）
- 绑定 ok；页码 ok；数值 ok；口径 ok
- 覆盖：out-of-range:0.35
- 备注：底账内同料名数值 0.35 越出声明区间 0.2,0.28

### C03 · CONFLICT
- 命题：PET_C / cell_size = 5,18（声明 p1）
- 绑定 ok；页码 ok；数值 ok；口径 ok
- 覆盖：out-of-range:3,20
- 备注：底账内同料名数值 3,20 越出声明区间 5,18

### C09 · FAIL
- 命题：3D-printed / density_reduction = 40（声明 p10）
- 绑定 ok；页码 ok；数值 ok；口径 DRIFT(weight reductions)
- 覆盖：ok
- 备注：底账覆盖 40

### C10 · FAIL
- 命题：3D-printed / relative_density = 1.26（声明 p10）
- 绑定 ok；页码 ok；数值 ok；口径 NO-ANCHOR(relative density)
- 覆盖：ok
- 备注：底账覆盖 1.26

### C11 · PASS（不可核验断言）
- 命题：3D-printed / none = —（声明 p1）
- 绑定 ok；页码 ok；数值 ok；口径 skip
- 覆盖：no-corpus
- 备注：含 first/only 类断言，需检索依据
