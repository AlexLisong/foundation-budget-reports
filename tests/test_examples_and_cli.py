import contextlib
import copy
from decimal import Decimal
import io
from pathlib import Path
import tempfile
import unittest

import pymupdf
from foundation_budget.calculate import calculate, read_project, percent
from foundation_budget.cli import main
from foundation_budget.report import render_report

ROOT = Path(__file__).resolve().parents[1]


class ExampleAndCliTests(unittest.TestCase):
    def test_historical_estimate_regressions(self):
        for name, net, order, hours, total in [
            ("gazebo", "12.690946502057612", "14", "160", "29134.56"),
            ("residential", "35.327160493827165", "40", "448", "79108.96"),
        ]:
            with self.subTest(name=name):
                result = calculate(read_project(ROOT / f"examples/{name}.json"))
                self.assertLess(abs(result["net_yd3"] - Decimal(net)), Decimal("0.0000001"))
                self.assertEqual(result["order_yd3"], Decimal(order))
                self.assertEqual(result["scenarios"]["base"]["labor_hours"], Decimal(hours))
                self.assertEqual(result["scenarios"]["base"]["total"], Decimal(total))

    def test_blank_template_refuses_to_generate_estimate(self):
        with self.assertRaisesRegex(ValueError, "fill in a finite numeric"):
            calculate(read_project(ROOT / "templates/project.json"))

    def test_unknown_fields_and_manual_base_edits_fail_loudly(self):
        original = read_project(ROOT / "examples/gazebo.json")
        for path, field, value in [
            ((), "sales_tax_fraction", .1),
            (("concrete", "scenarios", "base"), "volume_yd3", 140),
            (("labor", "scenarios", "base"), "hours", 1600),
            (("project",), "adress", "typo"),
        ]:
            with self.subTest(field=field):
                data = copy.deepcopy(original)
                node = data
                for key in path: node = node[key]
                node[field] = value
                with self.assertRaisesRegex(ValueError, "unknown fields"):
                    calculate(data)

    def test_schema_version_boolean_and_nonobject_root_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "JSON object"): calculate([])
        data = read_project(ROOT / "examples/gazebo.json")
        data["schema_version"] = True
        with self.assertRaisesRegex(ValueError, "schema_version"): calculate(data)

    def test_decimal_percentage_is_preserved_in_actual_pdf(self):
        data = read_project(ROOT / "examples/gazebo.json")
        data["concrete"]["waste_fraction"] = Decimal("0.085")
        data["markups"]["overhead_profit"]["base"] = Decimal("0.125")
        result = calculate(data)
        self.assertEqual(percent(Decimal("0.125")), "12.5%")
        self.assertEqual(result["scenarios"]["base"]["overhead"], Decimal("2827.5"))
        with tempfile.TemporaryDirectory() as temp:
            pdf = Path(temp) / "report.pdf"
            render_report(data, result, "en", pdf)
            with pymupdf.open(pdf) as doc:
                text = "\n".join(page.get_text() for page in doc)
                self.assertIn("8.5%", text)
                self.assertIn("12.5%", text)
                self.assertIn("2,827.50", text)

    def test_cli_invalid_root_uses_clean_error_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text("[]")
            err = io.StringIO()
            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as caught:
                main(["validate", str(path)])
            self.assertEqual(caught.exception.code, 2)
            self.assertIn("expected a JSON object", err.getvalue())

    def test_pdf_inspection_uses_real_page_count_and_selected_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with pymupdf.open() as doc:
                for value in ("Synthetic first sheet", "Synthetic second sheet"):
                    doc.new_page().insert_text((72,72), value)
                doc.save(root / "input.pdf")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["inspect", str(root / "input.pdf"), "--out", str(root / "inspect"), "--pages", "2", "--dpi", "36"]), 0)
            self.assertTrue((root / "inspect/page-02.png").exists())
            self.assertFalse((root / "inspect/page-01.png").exists())
            self.assertIn("Synthetic first sheet", (root / "inspect/text.txt").read_text())


if __name__ == "__main__": unittest.main()
