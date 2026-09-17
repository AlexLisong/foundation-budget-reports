# Foundation Budget Reports

Turn a **reviewed drawing takeoff** into traceable Chinese and English preliminary foundation-budget PDFs. Covers concrete, labor, reinforcing, formwork, excavation/backfill, pumping and project-specific allowances.

One project JSON feeds one calculator and both language versions. The inspector extracts text and page images; it does not automatically perform an engineering takeoff. Drawing interpretation, dimension verification and local pricing remain part of the review workflow.

[中文](README.md) · [Takeoff workflow](docs/takeoff-workflow.md) · [Reusable prompts](docs/reuse-prompts.md)

## Run the examples

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/). Run commands from the repository root. Access to the private GitHub repository requires an authorized account.

```bash
git clone https://github.com/AlexLisong/foundation-budget-reports.git
cd foundation-budget-reports
uv sync --locked
uv run foundation-budget report examples/gazebo.json --lang both --out output/gazebo --preview
uv run foundation-budget report examples/residential.json --lang both --out output/residential --preview
```

Without uv: create/activate a virtual environment and run `python -m pip install -e .`, then use `foundation-budget ...` directly.

## Prepare a new estimate

```bash
mkdir -p inputs projects
uv run foundation-budget inspect '/absolute/path/new-plans.pdf' --out work/my-project/drawings
cp templates/project.json projects/my-project.json
# Fill in the JSON, then:
uv run foundation-budget validate projects/my-project.json
uv run foundation-budget calculate projects/my-project.json --out work/my-project/calculation.json
uv run foundation-budget report projects/my-project.json --lang both --out output/my-project --preview
```

The blank template intentionally contains null values and will fail validation until filled. Update the slug, title, location, date, scope, source sheets, inputs, rates, tasks, allowances, assumptions and exclusions. Add all applicable footing/pad/wall quantities; the template's slab formula alone does not represent a complete foundation.

Inspect full relevant plan/section/detail sheets visually, including handwritten notes and scanned content. Explicitly distinguish drawing dimensions, derived quantities, estimating allowances and unresolved details. Do not carry historical example dimensions or prices into a new project as facts.

Output filenames use `project.slug`: `<slug>-zh.pdf`, `<slug>-en.pdf` and `<slug>-calculation.json`. Use `--lang en` or `--lang zh` for one language. `--preview` renders every PDF page into PNGs for visual review. Existing outputs with the same slug/path are overwritten; use dated output directories to retain revisions.

## Data and calculation rules

- `project`: bilingual identity/location/scope/source, ISO date, currency, price status and tax note.
- `inputs`: numeric parameters with units in names. Nulls, booleans and non-finite values are rejected.
- `quantities`: concrete volume in `yd3`, formula, bilingual label/basis/source, and `drawing`, `derived`, `allowance` or `unconfirmed` status. An unresolved item still needs an explicitly disclosed numeric allowance to be priced.
- `concrete`: waste fraction, upward order increment, optional conservative override and scenario rates/volumes. Base cost uses the calculated order.
- `labor`: activity hours and scenario rates. Base hours are summed from the activities.
- `allowances`: material/equipment/subcontract costs, with inclusions to prevent duplicated operator or installation labor.
- `markups`: overhead/profit on direct cost; contingency on direct cost plus overhead/profit.
- `assumptions`, `verification`, `exclusions`: bilingual project-specific notes.

Formulas allow only numeric constants, input/prior-quantity names, parentheses and `+ - * /`; no Python execution. Money uses Decimal and half-up cent display. Taxes are not automatically calculated; state treatment accurately in `tax_note`. Both PDFs share the same numbers. The PDF shows substituted numeric formulas; calculation JSON retains the inputs and editable formulas.

## Historical benchmarks

The de-identified examples preserve the earlier estimates. They contain no client identity/address or raw drawings. Prices are historical unquoted allowances, not current market rates.

| Example | Net yd3 | Order yd3 | Base labor-hours | Base total USD |
|---|---:|---:|---:|---:|
| Gazebo | 12.6909 | 14 | 160 | 29,134.56 |
| Residential | 35.3272 | 40 | 448 | 79,108.96 |

See [sample PDFs](examples/reports/). Older reports displayed whole dollars; this version displays cents with the same underlying calculation.

## Verification and project files

```bash
uv run python -m unittest discover -s tests -v
```

After changing math or layouts, regenerate the affected language examples and visually inspect every page. Rendering alone is not a visual pass. Reports have four main sections and may continue onto extra pages as content grows.

Client plans, project JSONs, intermediates and generated outputs belong in ignored `inputs/`, `projects/`, `work/` and `output/`. Only reviewed, de-identified examples are versioned. This is a preliminary budgeting tool, not structural design, a firm contractor bid or a concrete purchase order.
