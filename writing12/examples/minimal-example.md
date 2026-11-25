# 最小调用示例（示意输出，非正式案例结果）

## 输入

`case.json`（最小版）：

```json
{
  "case_id": "demo-001",
  "task": "把下面两段英文摘要译为中文，输出段级双语对照",
  "source_lang": "en",
  "target_lang": "zh",
  "segments": ["P01", "P02"],
  "materials": "demo-source.md"
}
```

`demo-source.md`：

```markdown
## P01

EN: Scaffolds were printed at 7.0 wt% loading. Porosity was 71.6% (Fig. 2a).

## P02

EN: The modulus may be associated with the ceramic phase [12].
```

## 调用

```bash
python scripts/draft_bilingual.py --materials demo-source.md --out work/bilingual.md
# → 产出骨架：两段，ZH 位为 [待译]

# 按术语表填译文（术语先查表：scaffold→支架、porosity→孔隙率、modulus→模量）
# 填完落台账与门槛：
python scripts/build_outputs.py --result out/result.json --text work/bilingual.md --outdir out
python scripts/validate_result.py out/result.json --case case.json --text work/bilingual.md
```

## 示意输出（`work/bilingual.md` 片段）

```markdown
## P01

EN: Scaffolds were printed at 7.0 wt% loading. Porosity was 71.6% (Fig. 2a).

ZH: 支架以 7.0 wt% 负载量打印，孔隙率为 71.6%（图 2a）。

## P02

EN: The modulus may be associated with the ceramic phase [12].

ZH: 模量可能与陶瓷相有关 [12]。
```

## 示意输出（`selfcheck.md`）

```
- 段数：2；覆盖：100%；段序：保持
- 标记保留：100%（fig 1/1；cite_bracket 1/1）
- 术语落地：100%；漂移：0 处；术语表矛盾：0 条
- 数值落地：100%（2/2）
- 边界改动：0 条；模糊限制语保留：100%
- 译文字数：34；占位符：0
```

注意这里 `may be associated with` 译成「可能与…有关」而不是「导致」，
`Fig. 2a` 换成「图 2a」但编号 `2a` 不变，`7.0` 与 `71.6` 都没取整——
这三处正是本 Skill 与直译的分界线。

> 以上为接口示意，`case_id` 与内容均为虚构；正式案例由平台运行时提供，本作品不预置答案。
