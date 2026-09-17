"""Render both languages from the exact same calculated result."""
from decimal import Decimal
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak

from .calculate import SCENARIOS, money, percent

TEXT = {
    "en": {
        "title": "Foundation Budget", "summary": "Preliminary construction estimate",
        "key": "Item", "value": "Estimate", "net": "Net concrete quantity",
        "waste": "Including waste", "order": "Budgeted concrete order",
        "concrete": "Ready-mix concrete", "labor": "Burdened labor",
        "direct": "Direct construction cost", "total": "Complete foundation budget",
        "range": "Low / high scenarios", "scope": "Included scope", "source": "Drawing basis",
        "quantity_title": "Concrete Quantities", "basis": "Basis / formula / source",
        "qty": "Net yd3", "assumptions": "Assumptions and unresolved dimensions",
        "cost_title": "Materials, Labor & Total Cost", "low": "Low", "base": "Base", "high": "High",
        "overhead": "Contractor overhead / profit", "contingency": "Contingency",
        "cost_basis": "Rates and allowance basis", "labor_title": "Labor & Verification",
        "hours": "Labor-hours", "labor_cost": "Base labor cost", "verify": "Verify before quoting / ordering",
        "exclusions": "Scope limits", "rounding": "Amounts are rounded to cents for display; calculations use unrounded values. Contingency applies to direct cost plus overhead/profit. Taxes are not added by the calculator; see the project tax note.",
        "footer": "PRELIMINARY FOUNDATION ESTIMATE", "drawing": "Drawing", "derived": "Derived",
        "allowance": "Allowance", "unconfirmed": "Unconfirmed", "example": "DE-IDENTIFIED HISTORICAL EXAMPLE - NOT CURRENT PRICING",
    },
    "zh": {
        "title": "完整基础工程预算", "summary": "初步施工预算",
        "key": "项目", "value": "预算", "net": "混凝土净工程量", "waste": "计入损耗后",
        "order": "混凝土预算订货量", "concrete": "预拌混凝土", "labor": "综合施工人工",
        "direct": "直接施工费", "total": "完整基础预算", "range": "低 / 高情景",
        "scope": "包含范围", "source": "图纸依据", "quantity_title": "混凝土工程量",
        "basis": "计算依据 / 公式 / 来源", "qty": "净量 yd3", "assumptions": "假设及待确认尺寸",
        "cost_title": "材料、人工及总价", "low": "低情景", "base": "基准", "high": "高情景",
        "overhead": "承包商管理利润", "contingency": "预备金", "cost_basis": "单价与暂列款依据",
        "labor_title": "人工与报价前复核", "hours": "人工小时", "labor_cost": "基准人工费",
        "verify": "报价及订货前核实", "exclusions": "范围边界",
        "rounding": "金额显示至小数点后两位，计算使用未取整金额。预备金按直接费加管理利润计取。计算器不另加税费，税费状态以项目说明为准。",
        "footer": "基础工程初步预算", "drawing": "图纸标注", "derived": "尺寸推算", "allowance": "预算假设",
        "unconfirmed": "待确认", "example": "去标识历史示例 - 单价不是当前报价",
    },
}


def render_report(data, result, lang, path):
    labels = TEXT[lang]
    font = "Helvetica"
    bold = "Helvetica-Bold"
    if lang == "zh":
        if "STSong-Light" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font = bold = "STSong-Light"
    ink, teal, muted = (colors.HexColor(v) for v in ("#183442", "#087F8C", "#51636C"))
    styles = {
        "title": ParagraphStyle("title", fontName=bold, fontSize=21, leading=26, textColor=ink, spaceAfter=10),
        "sub": ParagraphStyle("sub", fontName=font, fontSize=9, leading=13, textColor=muted, spaceAfter=10),
        "heading": ParagraphStyle("heading", fontName=bold, fontSize=12, leading=17, textColor=teal, spaceBefore=10, spaceAfter=7, keepWithNext=True),
        "body": ParagraphStyle("body", fontName=font, fontSize=9.2, leading=13, textColor=ink, spaceAfter=7),
        "small": ParagraphStyle("small", fontName=font, fontSize=8, leading=11, textColor=muted, spaceAfter=6),
        "cell": ParagraphStyle("cell", fontName=font, fontSize=8.3, leading=11.5, textColor=ink),
        "head": ParagraphStyle("head", fontName=bold, fontSize=8.3, leading=11.5, textColor=colors.white),
    }
    if lang == "zh":
        for style in styles.values(): style.wordWrap = "CJK"
    project = result["project"]
    currency = project["currency"]
    base = result["scenarios"]["base"]
    story = []

    def paragraph(value, kind="body"):
        safe = escape(str(value)).replace("\n", "<br/>")
        return Paragraph(safe, styles[kind])

    def add(value, kind="body"): story.append(paragraph(value, kind))

    def table(rows, widths):
        obj = Table([[paragraph(c, "head" if i == 0 else "cell") for c in row] for i, row in enumerate(rows)], colWidths=widths, repeatRows=1, hAlign="LEFT")
        obj.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), ink),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EDF5F6")]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("LINEBELOW", (0,-1), (-1,-1), .6, teal),
        ]))
        story.extend([obj, Spacer(1,7)])

    def section(title):
        if story: story.append(PageBreak())
        add(title, "title")
        add(f"{project['title'][lang]} | {project['location'][lang]} | {project['estimate_date']} | {currency}", "sub")

    def volume(value): return f"{value:.2f} yd3 ({value * Decimal('0.764554858'): .2f} m3)"
    def amount(value): return f"{currency} {money(value)}"
    def notes(title, values):
        add(title, "heading")
        for i, note in enumerate(values, 1): add(f"{i}. {note[lang]}", "small")

    section(labels["title"])
    if project.get("example", False): add(labels["example"], "heading")
    table([
        [labels["key"], labels["value"]],
        [labels["net"], volume(result["net_yd3"])],
        [f"{labels['waste']} (+{percent(result['waste_fraction'])})", volume(result["with_waste_yd3"])],
        [labels["order"], volume(result["order_yd3"])],
        [labels["concrete"], f"{base['volume_yd3']} yd3 x {amount(base['concrete_rate'])}/yd3 = {amount(base['concrete_cost'])}"],
        [labels["labor"], f"{base['labor_hours']} h x {amount(base['labor_rate'])}/h = {amount(base['labor_cost'])}"],
        [labels["direct"], amount(base["direct"])],
        [labels["total"], amount(base["total"])],
        [labels["range"], f"{amount(result['scenarios']['low']['total'])} - {amount(result['scenarios']['high']['total'])}"],
    ], [157,358])
    add(labels["scope"], "heading"); add(project["scope"][lang])
    add(labels["source"], "heading"); add(project["source"][lang])
    add(project["price_note"][lang], "small"); add(project["tax_note"][lang], "small")

    section(labels["quantity_title"])
    rows = [[labels["key"], labels["basis"], labels["qty"]]]
    formula_values = dict(result["inputs"])
    for item in result["quantities"]:
        # The PDF shows substituted numbers; the JSON retains the editable formula.
        def substitute(match):
            value = formula_values[match.group()]
            return format(value, '.6f').rstrip('0').rstrip('.') or '0'
        numeric_formula = re.sub(r"\b[a-z][a-z0-9_]*\b", substitute, item["formula"])
        detail = f"{item['basis'][lang]}\n{numeric_formula}\n[{labels[item['status']]}] {item['source'][lang]}"
        rows.append([item["label"][lang], detail, f"{item['quantity']:.2f}"])
        formula_values[item["id"]] = item["quantity"]
    rows += [[labels["net"], "", f"{result['net_yd3']:.2f}"],
             [labels["order"], f"{percent(result['waste_fraction'])} 损耗" if lang == "zh" else f"{percent(result['waste_fraction'])} waste", f"{result['order_yd3']:.2f}"]]
    table(rows, [113,343,59])
    notes(labels["assumptions"], data["assumptions"])

    section(labels["cost_title"])
    rows = [[labels["key"], *[labels[s] for s in SCENARIOS]]]
    for label, key in ((labels["concrete"], "concrete_cost"), (labels["labor"], "labor_cost")):
        rows.append([label, *[money(result["scenarios"][s][key]) for s in SCENARIOS]])
    for item in result["allowances"]:
        rows.append([item["label"][lang], *[money(item["amounts"][s]) for s in SCENARIOS]])
    for key in ("direct", "overhead", "contingency", "total"):
        label = labels[key]
        if key in ("overhead", "contingency"):
            rates = " / ".join(percent(result['scenarios'][s][key + '_rate']) for s in SCENARIOS)
            label += f" ({rates})"
        rows.append([label, *[money(result["scenarios"][s][key]) for s in SCENARIOS]])
    table(rows, [257,86,86,86])
    add(labels["rounding"], "small"); add(project["tax_note"][lang], "small")
    add(labels["cost_basis"], "heading"); add(data["concrete"]["price_basis"][lang], "small")
    for item in result["allowances"]:
        add(f"{item['label'][lang]}: {item['basis'][lang]}", "small")

    section(labels["labor_title"])
    rows = [[labels["key"], labels["hours"], labels["labor_cost"]]]
    for task in result["labor_tasks"]:
        rows.append([task["label"][lang], str(task["hours"]), money(task["hours"] * base["labor_rate"])])
    rows.append([labels["labor"], str(base["labor_hours"]), money(base["labor_cost"])])
    table(rows, [309,103,103])
    add(data["labor"]["basis"][lang])
    low, high = (result["scenarios"][s] for s in ("low", "high"))
    add(f"{labels['low']}: {low['labor_hours']} h x {amount(low['labor_rate'])}/h; {labels['high']}: {high['labor_hours']} h x {amount(high['labor_rate'])}/h.", "small")
    notes(labels["verify"], data["verification"])
    notes(labels["exclusions"], data["exclusions"])

    def footer(canvas, doc):
        canvas.setStrokeColor(teal); canvas.line(40,37,555,37)
        canvas.setFillColor(muted); canvas.setFont(font, 7.5)
        canvas.drawString(40,23,f"{labels['footer']} | {currency} | {project['estimate_date']}")
        canvas.drawRightString(555,23,str(doc.page))
    doc = SimpleDocTemplate(str(path), pagesize=(595.28,841.89), rightMargin=40, leftMargin=40,
                            topMargin=38, bottomMargin=49, title=f"{project['title'][lang]} - {labels['title']}", author="Foundation Budget Reports")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def preview_pdf(pdf_path, output_dir, dpi=110):
    import pymupdf
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(pdf_path) as document:
        for i, page in enumerate(document, 1):
            page.get_pixmap(dpi=dpi).save(output / f"page-{i:02}.png")
        return len(document)
