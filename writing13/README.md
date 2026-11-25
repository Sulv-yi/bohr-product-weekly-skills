# 写作13｜LaTeX 写作与编译 — Skill 交付

对应挑战：`product-arena-07-865de7e4`（写作13｜LaTeX 写作与编译）。本题**无** GitHub 附加分项。

## 一句话

把 LaTeX 稿件真正做到编译得通、改得对、交得可用、复现得了——用结构预检 + 多轮编译全量报错定位 + 引用收敛 + 来源映射 + 可复现构建记录替代"看起来像 LaTeX 的片段"。

## 文件清单

```
SKILL.md                        主文件：用途/工作流/输入输出/异常处理
README.md                       本说明
GITHUB_URL.txt                  公开作品链接
scripts/
  probe_project.py              引擎/模板/主文件/依赖探查（不臆造软件状态）
  build_manuscript.py           按案例生成结构完整可编译的 .tex 成稿骨架 + refs.bib + 章节计划
  check_manuscript.py           成稿实质门槛（结构/篇幅/占位符/公式表格/引用闭合）
  static_check.py               无引擎结构硬损伤检查（括号/环境/label/引用）
  compile_and_parse.py          多轮编译 + 全量报错定位与根因分类 + 引用收敛
  verify_result.py              五性质 + 契约自检（success 强制过成稿门槛）
references/
  error-taxonomy.md             编译错误分类与修复策略
  reproducibility.md            可重复构建记录规范
  template-and-math.md          模板适配与公式表格引用要点
examples/
  minimal-example.md            最小调用示例（示意，非真实结果）
```

## 设计动机（对应题面四问）

- **成稿齐** → `build_manuscript.py` 先建出章节齐全、可直接编译的 .tex，再逐节写实；`check_manuscript.py` 卡住空骨架、占位符、凑不够篇幅的稿子。
- **编译得通** → `compile_and_parse.py` 多轮编译到收敛，全量解析每条 `!` 错误到 file:line + 根因，不止于首错。
- **改得对** → `static_check.py` 预检 label/引用/cite/环境；`source_map` 逐条绑定事实来源与改动记录。
- **交得可用** → `verify_result.py` 强制交付通过实质门槛的可编辑 .tex，禁止 PDF/截图/片段/检查报告顶替。
- **复现得了** → `probe_project.py` 探测真实引擎/版本/依赖，`reproduction` 记录命令与轮次；探测不到写 unknown。

## 引擎缺失降级

本机无 TeX 引擎时：`probe_project.py` 如实标记；`static_check.py` 照常跑；`compile_and_parse.py` 返回 `status=unavailable` 并支持 `--log` 解析已有日志；`result.status` 只能到 partial，不伪造编译成功。评测镜像提供 `latex-compiler`，按真实引擎执行。

## 运行

Python 3.9+ 标准库即可。编译能力取决于环境是否提供 TeX 引擎。详见 SKILL.md 与 examples/minimal-example.md。

## 资源限制合规

12 个文本文件（≤50），均 UTF-8，总量远小于 2MB，单文件远小于 500KB，无符号链接，无凭证残留，无预置答案。
