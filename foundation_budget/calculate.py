"""Strict numeric inputs and a small arithmetic interpreter (no eval or Python calls)."""
import ast
import json
import re
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from pathlib import Path

SCENARIOS = ("low", "base", "high")
STATUSES = ("drawing", "derived", "allowance", "unconfirmed")


def fields(value, path, required, optional=()):
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    extra = set(value) - set(required) - set(optional)
    missing = set(required) - set(value)
    if extra:
        hint = ""
        if path == "concrete.scenarios.base": hint = "; change order_override_yd3 or takeoff inputs for the base volume"
        if path == "labor.scenarios.base": hint = "; change labor.tasks for base hours"
        raise ValueError(f"{path}: unknown fields {sorted(extra)}{hint}")
    if missing: raise ValueError(f"{path}: missing fields {sorted(missing)}")


def structure(data):
    fields(data, "project JSON", ("schema_version", "project", "inputs", "quantities", "concrete", "labor", "allowances", "markups", "assumptions", "verification", "exclusions"))
    fields(data["project"], "project", ("slug", "title", "location", "scope", "source", "tax_note", "price_note", "currency", "estimate_date"), ("example",))
    if "example" in data["project"] and type(data["project"]["example"]) is not bool:
        raise ValueError("project.example: expected a boolean")
    if not isinstance(data["inputs"], dict): raise ValueError("inputs: expected a JSON object")
    for name in ("quantities", "allowances", "assumptions", "verification", "exclusions"):
        if not isinstance(data[name], list): raise ValueError(f"{name}: expected a list")
    for row in data["quantities"]:
        fields(row, "quantity", ("id", "label", "formula", "unit", "basis", "source", "status"))
    fields(data["concrete"], "concrete", ("waste_fraction", "order_increment_yd3", "scenarios", "price_basis"), ("order_override_yd3",))
    fields(data["concrete"]["scenarios"], "concrete.scenarios", SCENARIOS)
    fields(data["labor"], "labor", ("tasks", "scenarios", "basis"))
    fields(data["labor"]["scenarios"], "labor.scenarios", SCENARIOS)
    if not isinstance(data["labor"]["tasks"], list): raise ValueError("labor.tasks: expected a list")
    for task in data["labor"]["tasks"]: fields(task, "labor.task", ("label", "hours"))
    for s in SCENARIOS:
        fields(data["concrete"]["scenarios"][s], f"concrete.scenarios.{s}", ("rate",) if s == "base" else ("rate", "volume_yd3"))
        fields(data["labor"]["scenarios"][s], f"labor.scenarios.{s}", ("rate",) if s == "base" else ("rate", "hours"))
    for item in data["allowances"]:
        fields(item, "allowance", ("label", "amounts", "basis"))
        fields(item["amounts"], "allowance.amounts", SCENARIOS)
    fields(data["markups"], "markups", ("overhead_profit", "contingency"))
    for key in ("overhead_profit", "contingency"):
        fields(data["markups"][key], f"markups.{key}", SCENARIOS)


def number(value, path, *, minimum=Decimal(0), maximum=None):
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{path}: fill in a finite numeric value; got {value!r}")
    result = Decimal(str(value))
    if not result.is_finite() or result < minimum or (maximum is not None and result > maximum):
        raise ValueError(f"{path}: value is outside the allowed range")
    return result


def bilingual(value, path):
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected an object with zh and en text")
    fields(value, path, ("zh", "en"))
    for lang in ("zh", "en"):
        if not isinstance(value.get(lang), str) or not value[lang].strip():
            raise ValueError(f"{path}.{lang}: non-empty text is required")


def expression(text, names):
    """Allow constants, names, parentheses, + - * / and unary signs only."""
    if not isinstance(text, str) or not text.strip() or len(text) > 1000:
        raise ValueError("quantity formula: expected 1-1000 characters")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid formula: {text}") from exc
    if len(list(ast.walk(tree))) > 150:
        raise ValueError("Formula is too complex")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant):
            return number(node.value, "formula literal")
        if isinstance(node, ast.Name):
            if node.id not in names:
                raise ValueError(f"Unknown formula input: {node.id}")
            return names[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if isinstance(node.op, ast.Div):
                if b == 0: raise ValueError("Division by zero in formula")
                return a / b
        raise ValueError("Formula allows only numbers, input names, + - * / and parentheses")

    result = visit(tree)
    if not result.is_finite() or result < 0:
        raise ValueError("Quantity formula must produce a finite, non-negative result")
    return result


def read_project(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), parse_float=Decimal)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read project JSON: {exc}") from exc


def calculate(data):
    structure(data)
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    project = data["project"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", project["slug"]):
        raise ValueError("project.slug must contain lowercase letters, digits and hyphens")
    for key in ("title", "location", "scope", "source", "tax_note", "price_note"):
        bilingual(project[key], f"project.{key}")
    if not re.fullmatch(r"[A-Z]{3}", project["currency"]):
        raise ValueError("project.currency must be a 3-letter currency code")
    from datetime import date
    try: date.fromisoformat(project["estimate_date"])
    except (ValueError, TypeError) as exc: raise ValueError("project.estimate_date must be YYYY-MM-DD") from exc

    names = {}
    for key, value in data["inputs"].items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ValueError(f"Invalid input name: {key}")
        names[key] = number(value, f"inputs.{key}")
    rows = []
    if not data["quantities"]:
        raise ValueError("At least one concrete quantity is required")
    for row in data["quantities"]:
        ident = row["id"]
        if ident in names or not re.fullmatch(r"[a-z][a-z0-9_]*", ident):
            raise ValueError(f"Duplicate or invalid quantity id: {ident}")
        for key in ("label", "basis", "source"):
            bilingual(row[key], f"quantities.{ident}.{key}")
        if row["status"] not in STATUSES or row["unit"] != "yd3":
            raise ValueError(f"{ident}: status must be one of {STATUSES}; unit must be yd3")
        value = expression(row["formula"], names)
        names[ident] = value
        rows.append({**row, "quantity": value})
    net = sum((r["quantity"] for r in rows), Decimal(0))
    if net <= 0:
        raise ValueError("Total net concrete quantity must be positive")
    concrete = data["concrete"]
    waste = number(concrete["waste_fraction"], "concrete.waste_fraction", maximum=Decimal(1))
    increment = number(concrete["order_increment_yd3"], "concrete.order_increment_yd3", minimum=Decimal("0.01"))
    with_waste = net * (1 + waste)
    automatic = (with_waste / increment).to_integral_value(rounding=ROUND_CEILING) * increment
    override = concrete.get("order_override_yd3")
    order = automatic if override is None else number(override, "concrete.order_override_yd3")
    if order < with_waste:
        raise ValueError("Concrete order override cannot be below net quantity plus waste")
    bilingual(concrete["price_basis"], "concrete.price_basis")

    labor = data["labor"]
    if not labor["tasks"]:
        raise ValueError("At least one labor task is required")
    tasks = []
    for task in labor["tasks"]:
        bilingual(task["label"], "labor.tasks.label")
        tasks.append({**task, "hours": number(task["hours"], "labor.tasks.hours")})
    labor_hours = sum((t["hours"] for t in tasks), Decimal(0))
    if labor_hours <= 0:
        raise ValueError("Total labor-hours must be positive")
    bilingual(labor["basis"], "labor.basis")

    allowances = []
    for item in data["allowances"]:
        bilingual(item["label"], "allowances.label")
        bilingual(item["basis"], "allowances.basis")
        allowances.append({**item, "amounts": {s: number(item["amounts"][s], f"allowances.{s}") for s in SCENARIOS}})
    for group in ("assumptions", "verification", "exclusions"):
        if not data[group]:
            raise ValueError(f"{group}: include at least one explicit note")
        for note in data[group]: bilingual(note, group)

    scenarios = {}
    for s in SCENARIOS:
        volume = order if s == "base" else number(concrete["scenarios"][s]["volume_yd3"], f"concrete.{s}.volume_yd3", minimum=Decimal("0.01"))
        rate = number(concrete["scenarios"][s]["rate"], f"concrete.{s}.rate", minimum=Decimal("0.01"))
        hours = labor_hours if s == "base" else number(labor["scenarios"][s]["hours"], f"labor.{s}.hours", minimum=Decimal("0.01"))
        labor_rate = number(labor["scenarios"][s]["rate"], f"labor.{s}.rate", minimum=Decimal("0.01"))
        concrete_cost, labor_cost = volume * rate, hours * labor_rate
        direct = concrete_cost + labor_cost + sum((a["amounts"][s] for a in allowances), Decimal(0))
        overhead_rate = number(data["markups"]["overhead_profit"][s], f"markups.overhead_profit.{s}", maximum=Decimal(1))
        contingency_rate = number(data["markups"]["contingency"][s], f"markups.contingency.{s}", maximum=Decimal(1))
        overhead = direct * overhead_rate
        contingency = (direct + overhead) * contingency_rate
        scenarios[s] = dict(volume_yd3=volume, concrete_rate=rate, concrete_cost=concrete_cost,
                            labor_hours=hours, labor_rate=labor_rate, labor_cost=labor_cost,
                            direct=direct, overhead_rate=overhead_rate, overhead=overhead,
                            contingency_rate=contingency_rate, contingency=contingency,
                            total=direct + overhead + contingency)
    if not scenarios["low"]["total"] <= scenarios["base"]["total"] <= scenarios["high"]["total"]:
        raise ValueError("Scenario totals must be ordered low <= base <= high")
    return dict(project=project, inputs={key: names[key] for key in data["inputs"]}, quantities=rows, net_yd3=net, waste_fraction=waste,
                with_waste_yd3=with_waste, order_yd3=order, labor_tasks=tasks,
                allowances=allowances, scenarios=scenarios)


def decimal_json(value):
    if isinstance(value, Decimal): return str(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def money(value):
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}"


def percent(value):
    text = format(value * 100, "f")
    if "." in text: text = text.rstrip("0").rstrip(".")
    return text + "%"
