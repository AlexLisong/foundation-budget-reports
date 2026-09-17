import argparse
from datetime import date
import json
from pathlib import Path
import sys

from .calculate import calculate, decimal_json, read_project


def inspect_pdf(path, output, pages, dpi):
    import pymupdf
    output.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(path) as document:
        if document.needs_pass:
            raise ValueError("Encrypted PDF requires an unlocked copy")
        selected = list(range(1,len(document)+1)) if not pages else [int(x) for x in pages.split(",")]
        if any(p < 1 or p > len(document) for p in selected):
            raise ValueError(f"Page numbers must be between 1 and {len(document)}")
        metadata = dict(page_count=len(document), selected_pages=selected, dpi=dpi,
                        note="Extracted text and images are aids for human takeoff, not verified quantities.")
        text = []
        for i, page in enumerate(document,1):
            text.append(f"\n--- PAGE {i} ---\n{page.get_text()}")
            if i in selected: page.get_pixmap(dpi=dpi).save(output / f"page-{i:02}.png")
        (output / "text.txt").write_text("\n".join(text), encoding="utf-8")
        (output / "metadata.json").write_text(json.dumps(metadata,indent=2), encoding="utf-8")
        print(f"Inspected {len(document)} pages; rendered {len(selected)} pages in {output}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reviewed takeoff JSON -> traceable bilingual foundation budget PDFs")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "calculate", "report"):
        p = sub.add_parser(name)
        p.add_argument("project", type=Path)
        if name == "calculate": p.add_argument("--out", type=Path)
        if name == "report":
            p.add_argument("--lang", choices=("zh", "en", "both"), default="both")
            p.add_argument("--out", type=Path, default=Path("output"))
            p.add_argument("--preview", action="store_true", help="Render every generated PDF page to PNG for visual QA")
    p = sub.add_parser("inspect", help="Extract text and render drawing pages; does not perform automatic takeoff")
    p.add_argument("pdf", type=Path); p.add_argument("--out", type=Path, required=True)
    p.add_argument("--pages", help="1-based comma-separated pages; defaults to all")
    p.add_argument("--dpi", type=int, choices=range(36,301), metavar="36..300", default=72)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            inspect_pdf(args.pdf, args.out, args.pages, args.dpi)
            return 0
        data = read_project(args.project)
        result = calculate(data)
        if args.command == "validate":
            print(f"Valid: {result['project']['slug']}; {result['net_yd3']:.4f} net yd3; {result['order_yd3']} ordered yd3")
        elif args.command == "calculate":
            output = json.dumps(result, ensure_ascii=False, indent=2, default=decimal_json) + "\n"
            if args.out:
                args.out.parent.mkdir(parents=True,exist_ok=True)
                args.out.write_text(output,encoding="utf-8")
                print(args.out)
            else: print(output,end="")
        else:
            from .report import render_report, preview_pdf
            args.out.mkdir(parents=True,exist_ok=True)
            slug = result["project"]["slug"]
            for lang in (("zh","en") if args.lang == "both" else (args.lang,)):
                path = args.out / f"{slug}-{lang}.pdf"
                render_report(data,result,lang,path)
                print(path)
                if args.preview:
                    count = preview_pdf(path,args.out / "preview" / f"{slug}-{lang}")
                    print(f"  {count} pages rendered for visual review")
            (args.out / f"{slug}-calculation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,default=decimal_json),encoding="utf-8")
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
