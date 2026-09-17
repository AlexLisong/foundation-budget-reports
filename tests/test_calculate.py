"""Business invariants using invented data, independent of report examples."""
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from foundation_budget.calculate import calculate, expression, read_project


def text(english="Synthetic example", chinese="合成示例"):
    return {"en": english, "zh": chinese}


def project():
    """Return fresh data; all dimensions and rates are deliberately invented."""
    return {
        "schema_version": 1,
        "project": {
            "slug": "synthetic-foundation",
            "title": text(), "location": text(), "scope": text(),
            "source": text(), "tax_note": text(), "price_note": text(),
            "currency": "USD", "estimate_date": "2026-01-01",
        },
        "inputs": {"length_ft": 27, "width_ft": 12, "thickness_in": 4},
        "quantities": [
            {
                "id": "slab", "label": text(), "basis": text(), "source": text(),
                "status": "derived", "unit": "yd3",
                "formula": "length_ft * width_ft * (thickness_in / 12) / 27",
            },
            {
                "id": "footings", "label": text(), "basis": text(), "source": text(),
                "status": "allowance", "unit": "yd3", "formula": "slab / 2",
            },
        ],
        "concrete": {
            "waste_fraction": 0.1, "order_increment_yd3": 0.5,
            "order_override_yd3": None, "price_basis": text(),
            "scenarios": {
                "low": {"volume_yd3": 6, "rate": 100},
                "base": {"rate": 120},
                "high": {"volume_yd3": 8, "rate": 140},
            },
        },
        "labor": {
            "tasks": [{"label": text(), "hours": 12}, {"label": text(), "hours": 8}],
            "basis": text(),
            "scenarios": {
                "low": {"hours": 16, "rate": 50},
                "base": {"rate": 60},
                "high": {"hours": 24, "rate": 70},
            },
        },
        "allowances": [
            {"label": text(), "basis": text(), "amounts": {"low": 250, "base": 300, "high": 400}},
        ],
        "markups": {
            "overhead_profit": {"low": 0.1, "base": 0.12, "high": 0.15},
            "contingency": {"low": 0.05, "base": 0.1, "high": 0.2},
        },
        "assumptions": [text()], "verification": [text()], "exclusions": [text()],
    }


def replace(data, path, value):
    for key in path[:-1]:
        data = data[key]
    data[path[-1]] = value


class CalculationTests(unittest.TestCase):
    def test_dimensions_convert_to_cubic_yards_and_can_reference_prior_quantity(self):
        result = calculate(project())
        self.assertEqual([row["quantity"] for row in result["quantities"]], [Decimal(4), Decimal(2)])
        self.assertEqual(result["net_yd3"], Decimal(6))

    def test_waste_rounds_up_to_order_increment(self):
        result = calculate(project())
        self.assertEqual(result["with_waste_yd3"], Decimal("6.6"))
        self.assertEqual(result["order_yd3"], Decimal(7))
        self.assertEqual(result["scenarios"]["base"]["volume_yd3"], Decimal(7))

    def test_exact_order_increment_does_not_add_an_extra_increment(self):
        data = project()
        data["concrete"]["waste_fraction"] = 0.25
        self.assertEqual(calculate(data)["order_yd3"], Decimal("7.5"))

    def test_manual_order_cannot_be_less_than_net_plus_waste(self):
        for override in (0, 6, 6.59):
            with self.subTest(override=override):
                data = project()
                data["concrete"]["order_override_yd3"] = override
                with self.assertRaisesRegex(ValueError, "below net quantity plus waste"):
                    calculate(data)
        data = project()
        data["concrete"]["order_override_yd3"] = 7.5
        result = calculate(data)
        self.assertEqual(result["order_yd3"], Decimal("7.5"))
        self.assertEqual(result["scenarios"]["base"]["concrete_cost"], Decimal(900))

    def test_base_labor_hours_and_cost_follow_task_hours(self):
        result = calculate(project())
        self.assertEqual(result["scenarios"]["base"]["labor_hours"], Decimal(20))
        self.assertEqual(result["scenarios"]["base"]["labor_cost"], Decimal(1200))
        data = project()
        data["labor"]["tasks"][0]["hours"] = 13
        result = calculate(data)
        self.assertEqual(result["scenarios"]["base"]["labor_hours"], Decimal(21))
        self.assertEqual(result["scenarios"]["base"]["labor_cost"], Decimal(1260))

    def test_each_scenario_adds_profit_then_contingency_on_subtotal(self):
        # Independently worked totals: concrete + labor + allowance, then
        # overhead/profit on direct cost, then contingency including overhead.
        expected = {
            "low": ("1650", "165", "90.75", "1905.75"),
            "base": ("2340", "280.8", "262.08", "2882.88"),
            "high": ("3200", "480", "736", "4416"),
        }
        scenarios = calculate(project())["scenarios"]
        for scenario, values in expected.items():
            with self.subTest(scenario=scenario):
                self.assertEqual(
                    tuple(scenarios[scenario][key] for key in ("direct", "overhead", "contingency", "total")),
                    tuple(Decimal(value) for value in values),
                )

    def test_reversed_scenario_total_is_rejected(self):
        data = project()
        data["allowances"][0]["amounts"]["low"] = 10000
        with self.assertRaisesRegex(ValueError, "low <= base <= high"):
            calculate(data)

    def test_required_numeric_fields_reject_missing_nonfinite_and_boolean_values(self):
        paths = [
            ("inputs", "length_ft"),
            ("concrete", "waste_fraction"),
            ("concrete", "order_increment_yd3"),
            ("concrete", "scenarios", "low", "volume_yd3"),
            ("concrete", "scenarios", "base", "rate"),
            ("labor", "tasks", 0, "hours"),
            ("labor", "scenarios", "high", "hours"),
            ("labor", "scenarios", "base", "rate"),
            ("allowances", 0, "amounts", "base"),
            ("markups", "overhead_profit", "base"),
            ("markups", "contingency", "base"),
        ]
        for path in paths:
            for invalid in (None, float("nan"), float("inf"), True, False, "12"):
                with self.subTest(path=path, invalid=invalid):
                    data = project()
                    replace(data, path, invalid)
                    with self.assertRaises(ValueError):
                        calculate(data)

    def test_manual_override_accepts_null_but_rejects_other_invalid_numbers(self):
        self.assertEqual(calculate(project())["order_yd3"], Decimal(7))
        for invalid in (float("nan"), float("inf"), True, False, "7"):
            with self.subTest(invalid=invalid):
                data = project()
                data["concrete"]["order_override_yd3"] = invalid
                with self.assertRaises(ValueError):
                    calculate(data)

    def test_nonpositive_total_quantities_or_labor_are_rejected(self):
        data = project()
        data["inputs"]["length_ft"] = 0
        with self.assertRaisesRegex(ValueError, "net concrete quantity must be positive"):
            calculate(data)
        data = project()
        for task in data["labor"]["tasks"]:
            task["hours"] = 0
        with self.assertRaisesRegex(ValueError, "labor-hours must be positive"):
            calculate(data)

    def test_bilingual_fields_require_both_nonempty_translations(self):
        paths = [
            *(("project", key) for key in ("title", "location", "scope", "source", "tax_note", "price_note")),
            *(("quantities", 0, key) for key in ("label", "basis", "source")),
            ("concrete", "price_basis"), ("labor", "basis"), ("labor", "tasks", 0, "label"),
            ("allowances", 0, "label"), ("allowances", 0, "basis"),
            ("assumptions", 0), ("verification", 0), ("exclusions", 0),
        ]
        for path in paths:
            for invalid in ({"en": "Only English"}, {"zh": "只有中文"}, {"en": "English", "zh": "  "}):
                with self.subTest(path=path, invalid=invalid):
                    data = project()
                    replace(data, path, invalid)
                    with self.assertRaises(ValueError):
                        calculate(data)

    def test_json_slug_cannot_escape_output_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "project.json"
            for slug in ("../outside", "../../outside", "/tmp/outside", "..\\outside", ".", "..", "safe/../../outside"):
                with self.subTest(slug=slug):
                    data = project()
                    data["project"]["slug"] = slug
                    path.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "project.slug"):
                        calculate(read_project(path))

    def test_json_decimal_rates_keep_expected_costs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "project.json"
            path.write_text(json.dumps(project()), encoding="utf-8")
            loaded = read_project(path)
            self.assertEqual(loaded["markups"]["overhead_profit"]["base"], Decimal("0.12"))
            self.assertEqual(calculate(loaded)["scenarios"]["base"]["total"], Decimal("2882.88"))


class FormulaTests(unittest.TestCase):
    def test_arithmetic_supports_precedence_parentheses_and_unary_signs(self):
        self.assertEqual(expression("(+length - -2) * (6 / 3)", {"length": Decimal(3)}), Decimal(10))

    def test_unknown_and_forward_references_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown formula input"):
            expression("unknown * 2", {})
        data = project()
        data["quantities"][0]["formula"] = "footings * 2"
        with self.assertRaisesRegex(ValueError, "Unknown formula input"):
            calculate(data)

    def test_executable_or_nonnumeric_expressions_are_rejected(self):
        for formula in (
            "__import__('os').getcwd()", "sum([1, 2])", "(1).__class__",
            "[1][0]", "[x for x in [1]]", "(lambda: 1)()", "1 ** 1000", "True", "None", "'2'",
        ):
            with self.subTest(formula=formula):
                with self.assertRaises(ValueError):
                    expression(formula, {})

    def test_division_by_zero_negative_and_nonfinite_results_are_rejected(self):
        for formula in ("1 / 0", "2 - 3", "1e999"):
            with self.subTest(formula=formula):
                with self.assertRaises(ValueError):
                    expression(formula, {})


if __name__ == "__main__":
    unittest.main()
