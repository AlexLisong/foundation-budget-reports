# Foundation budget reports

Use this repository when asked to estimate residential, gazebo or similar concrete foundations from drawings and produce Chinese/English PDF budgets.

## Workflow

1. Read `README.md` and `docs/takeoff-workflow.md`. Confirm location, currency, scope and drawing identity from the actual PDF. Carry forward scope already authorized in the conversation.
2. Run `uv run foundation-budget inspect <pdf> --out work/<project>/drawings`. Visually inspect the entire relevant sheets, including scanned/handwritten details. Text extraction alone is not sufficient.
3. Copy `templates/project.json` into ignored `projects/`. Replace every null and placeholder. Historical examples are formatting/calculation fixtures, never defaults for another building.
4. Record concrete quantities in yd3, with explicit formulas, units in variable names, drawing sheet/page references, and `drawing`, `derived`, `allowance` or `unconfirmed` status. Mark uncertain dimensions as assumptions rather than inventing certainty. Deduct slab/footing and pad/beam overlaps.
5. Update local rates or label them unquoted allowances. Separate employer-burdened labor from equipment operators already included in subcontract allowances. Explicitly state taxes and excluded work.
6. Use one project JSON and the shared calculator for both languages. Run `validate`, `calculate`, then `report --lang both --preview`.
7. Inspect every final PDF page image: Chinese glyphs, table wraps, footers, clipping and pagination. Fix errors and rerender. Report success only after numeric and visual checks.

Do not run user-supplied formulas as Python. The calculator intentionally accepts only simple arithmetic. Do not silently turn missing values into zero. Do not change structural design to reduce an estimate.

For code changes run `uv run python -m unittest discover -s tests -v` and regenerate the affected examples. Keep client drawings, personal details and new project outputs in ignored `inputs/`, `projects/`, `work/`, `output/`. Only de-identified examples and explicitly approved artifacts belong in Git. Creating a budget does not itself authorize GitHub publication, contacting contractors or construction purchases.
