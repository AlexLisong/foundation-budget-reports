# 从图纸到预算 / Drawing-to-budget workflow

## 1. 确认项目及范围

记录图纸名称、实际项目名称、图号、日期、地点和币种。文件名与图签不一致时，报告中说明按哪一份内容计算。沿用用户已确认的范围，通常包括：混凝土、钢筋、预埋件、模板、人工、泵车、挖土运土、回填压实、基层、需要的排水防水、管理利润和预备金。

“完整地基”仍应明确边界：上部木结构、屋顶、设备、图外露台、许可/设计/特殊检测，以及岩石、降水、特殊支护等是否包含。不要把价格示例当成本地报价，也不要把“全部包含”写成没有边界的固定施工合同。

## 2. 阅读与视觉检查

```bash
uv run foundation-budget inspect inputs/plan.pdf --out work/job/drawings --dpi 72
# 大图细节可指定页号，提高分辨率：
uv run foundation-budget inspect inputs/plan.pdf --out work/job/details --pages 2 --dpi 150
```

命令生成所有页的 `text.txt`、页数说明以及选定页的 PNG。图纸文字可能是扫描图片，手写修订也可能无法提取，必须查看图片。检查平面、尺寸、基础详图、结构总说明、剖面和高程之间是否一致。尺寸标注优先于按比例量取；不要只按建筑总面积估算所有基础。

## 3. 工程量与证据

在 `quantities` 的每一项记录：

| 字段 | 用途 |
|---|---|
| `id` | 唯一名称，也可在后续公式中引用 |
| `label` | 中英文项目名称 |
| `formula` | 只允许数字、输入名称、括号及 `+ - * /` |
| `unit` | 本版本混凝土工程量固定为 `yd3` |
| `basis` | 中英文计算依据、扣重方式、尺寸假设 |
| `source` | 页码或图号/详图号；暂估也需说明来源 |
| `status` | `drawing` 图纸明确、`derived` 尺寸推算、`allowance` 预算假设、`unconfirmed` 待确认 |

`unconfirmed` 仍须有明确标注的数值假设才能计价；未知且无假设的值保持 `null`，校验会拒绝生成报告。

常用换算：

- 地坪：`area_sf * thickness_in / 12 / 27`。
- 梁/条基：`length_ft * width_in / 12 * depth_in / 12 / 27`。
- 墙体：`length_ft * height_ft * thickness_in / 12 / 27`。
- `1 yd3 = 0.764554858 m3`。水泥粉吨数需要混凝土配合比，不能直接从建筑面积确定。

地坪按全幅计入时，基础梁只能增加未计入的部分。柱墩与梁、基础转角、墙与底座交叠不能重复累加。详图的 “MAX” 或 “MIN” 不是该位置已确认的实际尺寸；`3/4 in road base` 一般指粒径，不能当作基层厚度。

损耗量与净工程量分开。基准订货量自动将 `net * (1 + waste_fraction)` 向上取整到 `order_increment_yd3`；如需要更保守的暂估量，用 `order_override_yd3` 明确设置，并说明原因。该覆盖值不能低于净量加损耗。

## 4. 费用与人工

混凝土基准费用自动引用订货量，人工基准小时自动汇总 `labor.tasks`。低/高情景单独记录数量和费率。其他费用为 `allowances` 暂列款，逐项说明包含的材料、运输、设备或人员。

- 综合人工费率含工资和雇主用工负担；不同于工人实发工资。
- 机械土方和泵车若已含操作员，不要在普通人工里重复计费。
- 钢筋、模板材料项的安装人工是否已计入，必须说明。
- 总价 = 直接费 + 管理利润 + 预备金；预备金的基数是直接费加管理利润。
- 金额使用 Decimal 计算，显示至美分（ROUND_HALF_UP）；合计使用未舍入值。
- 本版本不自动计算税。`tax_note` 必须准确写明未计税、报价内税费或后续核实方式；需自动计税时，应明确扩展计算器，不能只改描述。

## 5. 双语与检查

两个语言版本的文字放在同一个 JSON 的 `zh` / `en` 字段中，所有数值由同一个计算对象生成。不要在英文模板重新手抄工程量、费用或总价。

```bash
uv run foundation-budget validate projects/job.json
uv run foundation-budget calculate projects/job.json --out work/job/calculation.json
uv run foundation-budget report projects/job.json --lang both --out output/job --preview
```

逐页打开 `output/job/preview/` 中的图片，检查字形、表格、分页、页脚和溢出。`--preview` 只生成图片，不会替代人工/视觉模型验收。可用系统 Poppler 再检查：`pdftoppm -scale-to 1400 -png output/job/job-en.pdf work/job/qa-en`。

报告必须说明未确认尺寸、未询价单价、关键土方条件、数量范围与范围排除；它是可追溯的初步预算，不是结构设计、订货单或承包商固定报价。

## English quick reference

Inspect the actual drawing pages, reconcile plans/sections/details, and record dimensions with drawing references. Identify assumptions explicitly; do not inherit site facts or rates from historical examples. Enter concrete volumes in cubic yards with transparent arithmetic and overlap deductions. Separate net concrete, waste and budgeted order quantity. Keep material, burdened labor and equipment/subcontract allowances distinct. State tax treatment and exclusions. Generate both languages from one JSON, render every page and visually review before delivery. The PDF inspector assists reading; it does not perform automatic engineering takeoff or verify design adequacy.
