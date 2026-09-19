# Foundation Budget Reports

把**已核对的建筑图纸工程量**整理为可追溯的中英文地基预算 PDF。适用于住宅、凉亭等混凝土基础的初步预算：混凝土用量、人工、钢筋模板、机械土方、泵送及其他暂列费用。

**一份项目 JSON → 一套计算结果 → 中文和英文 PDF。** 脚本负责计算和排版；图纸判读、尺寸核实及当地询价需要人工或 AI 助手完成。

[English README](README.en.md) · [详细核量流程](docs/takeoff-workflow.md) · [下次可直接复制的提示词](docs/reuse-prompts.md)

无需安装即可查看示例报告：凉亭 [中文 PDF](examples/reports/gazebo-example-zh.pdf) / [English PDF](examples/reports/gazebo-example-en.pdf)，住宅 [中文 PDF](examples/reports/residential-example-zh.pdf) / [English PDF](examples/reports/residential-example-en.pdf)。示例已去标识，原客户图纸不在仓库中。

## 最快上手

需要 Python 3.10+ 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。所有命令在本仓库目录运行。

```bash
git clone https://github.com/AlexLisong/foundation-budget-reports.git
cd foundation-budget-reports
uv sync --locked

# 先复现凉亭示例，同时生成中英文及逐页预览
uv run foundation-budget report examples/gazebo.json --lang both --out output/gazebo --preview

# 住宅示例
uv run foundation-budget report examples/residential.json --lang both --out output/residential --preview
```

不使用 uv 也可以：`python3 -m venv .venv`，激活环境后 `python -m pip install -e .`，再直接运行 `foundation-budget ...`。

## 新项目怎么做

1. 把图纸保存在 `inputs/`，用提取工具生成文字及图片。
2. 查看完整相关页，核对尺寸、结构做法、基础高差、柱墩和地坪重合处。
3. 将空白模板复制到 `projects/`，填写新项目数据和双语说明。**模板中的 `null` 必须填写**；历史示例不是新项目默认值。
4. 验证并计算，生成中英文报告。
5. 逐页查看预览图片，确认没有缺字、遮挡或表格溢出，再交付。

```bash
mkdir -p inputs projects
uv run foundation-budget inspect '/absolute/path/new-plans.pdf' --out work/my-project/drawings
cp templates/project.json projects/my-project.json

# 编辑 JSON：至少修改 slug、名称、地点、日期、范围、图纸依据、尺寸、费率、人工、暂列款、假设及排除项
# 根据图纸添加条基、柱基、挡土墙等数量项；空白模板仅示范地坪公式，不代表完整基础

uv run foundation-budget validate projects/my-project.json
uv run foundation-budget calculate projects/my-project.json --out work/my-project/calculation.json
uv run foundation-budget report projects/my-project.json --lang both --out output/my-project --preview
```

如果只需要英文，把 `--lang both` 改为 `--lang en`。中文使用 `--lang zh`。输出名由 JSON 中的 `project.slug` 决定；默认 `report` 输出到 `output/`。

`report` 在指定目录生成 `<slug>-zh.pdf`、`<slug>-en.pdf` 和 `<slug>-calculation.json`；`--preview` 另外生成逐页 PNG。**相同目录和 slug 会覆盖以前的生成文件**，需留版本时换输出目录，例如 `output/my-project/2026-09-16/`。

## 最简单的复用方式

下次给助手以下指令，并附图纸路径：

> 使用 AlexLisong/foundation-budget-reports 仓库，按 AGENTS.md 核对这份图纸，做完整地基预算，生成中文和英文 PDF。包括混凝土、钢筋模板、人工、挖土运土回填压实、泵车及需要的排水防水。明确估算假设和未询价费用，并逐页检查报告。

完整提示词及更新报价的例子见 [docs/reuse-prompts.md](docs/reuse-prompts.md)。

## 项目数据结构

| 字段 | 内容 |
|---|---|
| `project` | 名称、地点、日期、币种、范围、图纸依据、单价状态和税费说明 |
| `inputs` | 数值参数；变量名写明单位，例如 `wall_height_ft` |
| `quantities` | 每项混凝土的公式、单位、双语依据、图纸页码及来源状态 |
| `concrete` | 损耗、订货取整、可选订货覆盖、低中高数量/单价 |
| `labor` | 工序和基准小时数、三档人工费率、低高小时数 |
| `allowances` | 钢筋、模板、挖土、泵车等暂列款及各自包含项 |
| `markups` | 管理利润、预备金三档比例，例如 `0.12` 表示 12% |
| `assumptions` / `verification` / `exclusions` | 假设、待核事项、排除范围 |

所有面向报告的文字使用 `{"zh": "中文", "en": "English"}`。公式只允许数字、已有输入或前序数量项名称、括号及 `+ - * /`，不执行 Python。金额使用 Decimal，报告显示至美分。税费不自动加入，必须在 `tax_note` 明确说明。

报告包含四个主要部分：摘要、工程量及假设、费用明细、人工及复核事项。内容较多时会自动续页，不能以固定页数代替版面检查。

## 已验证的历史示例

示例去除了客户姓名、门牌地址和原图纸；**单价是历史暂估输入，不是当前市场报价**。两套计算保留本次住宅/凉亭预算的关键结果：

| 示例 | 净混凝土 yd3 | 预算订货 yd3 | 基准人工小时 | 基准总价 USD |
|---|---:|---:|---:|---:|
| [凉亭 JSON](examples/gazebo.json) | 12.6909 | 14 | 160 | 29,134.56 |
| [住宅 JSON](examples/residential.json) | 35.3272 | 40 | 448 | 79,108.96 |

样本 PDF：

- 凉亭：[中文](examples/reports/gazebo-example-zh.pdf) / [English](examples/reports/gazebo-example-en.pdf)
- 住宅：[中文](examples/reports/residential-example-zh.pdf) / [English](examples/reports/residential-example-en.pdf)

旧报告金额按整美元显示，本版本显示美分，公式和关键总价保持一致。原来硬编码的表格现在由同一计算器生成；PDF 显示代入数值的公式，配套 JSON 保留输入值及可编辑公式。

## 开发与验证

```bash
uv run python -m unittest discover -s tests -v
uv run foundation-budget validate examples/gazebo.json
uv run foundation-budget validate examples/residential.json
```

任何计算或模板变更后，重新生成受影响示例并查看全部 PDF 页面。预览命令仅渲染，不自动认定布局通过。复用前先读 [核量流程](docs/takeoff-workflow.md)，尤其是板/梁/柱基扣重、MIN/MAX 尺寸和人工重复计费。

`inputs/`、`projects/`、`work/`、`output/` 默认被 Git 忽略，便于保存客户图纸和本地报告。仓库只收录去标识示例。当前工具用于初步预算，不进行自动结构设计、承包商询价或混凝土采购。
