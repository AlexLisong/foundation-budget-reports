# 下次直接复制使用 / Reusable prompts

在这个仓库打开终端或让编码助手进入仓库后：

> 请按本仓库 AGENTS.md 和 docs/takeoff-workflow.md，读取 `/absolute/path/new-plans.pdf`，生成完整地基预算，包括混凝土、钢筋、模板、预埋件、人工、挖土运土、回填压实、基层、所需排水防水及泵车。按图纸实际地点和币种，明确未标尺寸和暂估单价。创建独立项目 JSON，用统一计算器生成中文和英文 PDF，并核对全部页面。项目名为 `my-project`，结果放在 `output/my-project/`。

补充预算条件时：

> 更新 `projects/my-project.json`：混凝土报价为每立方码 ___，是否含运输/税费为 ___；工人人工每小时 ___；挖土运土包价 ___。保持工程量假设可追溯，重新生成中英文报告，解释总价变化。

只要英文时：

> 使用同一个项目 JSON，生成英文 PDF，保持工程量、费用、假设和范围与中文版本一致。

English:

> Follow this repository's AGENTS.md and takeoff workflow. Inspect `/absolute/path/new-plans.pdf`, prepare a complete preliminary foundation budget, and create a reviewed project JSON. Include concrete, reinforcing, formwork, embeds, labor, excavation/haul-off/backfill/compaction, base, required drainage/waterproofing and pumping. Use the location/currency shown in the drawings. Label missing dimensions and unquoted rates as assumptions. Generate Chinese and English PDFs from the shared calculator and visually verify every page. Save the project as `my-project` and results under `output/my-project/`.
