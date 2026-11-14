"""Inventory real files in data/raw. Reports only what is actually inside them."""
import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
OUT = Path("data/metadata/file_inventory.csv")
TEXT_OUT = Path("data/processed/docx_text")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()[:16]


def read_docx(path: Path) -> str:
    import docx
    d = docx.Document(path)
    parts = [p.text for p in d.paragraphs if p.text.strip()]
    for t in d.tables:
        for row in t.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n".join(parts)


def describe(path: Path) -> str:
    ext = path.suffix.lower()
    try:
        if ext in {".csv", ".tsv", ".txt"}:
            df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
            return f"{len(df)} rows, {len(df.columns)} cols: {list(df.columns)}"
        if ext in {".xlsx", ".xls"}:
            sheets = pd.read_excel(path, sheet_name=None)
            summary = "; ".join(f"{k}: {len(v)} rows x {len(v.columns)} cols" for k, v in sheets.items())
            first_name, first_df = next(iter(sheets.items()))
            return f"{summary} || columns of '{first_name}': {list(first_df.columns)}"
        if ext == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            return f"json {type(data).__name__}, top keys: {list(data)[:12] if isinstance(data, dict) else len(data)}"
        if ext == ".docx":
            text = read_docx(path)
            TEXT_OUT.mkdir(parents=True, exist_ok=True)
            (TEXT_OUT / f"{path.stem}.txt").write_text(text, encoding="utf-8")
            return f"{len(text)} text chars (saved to {TEXT_OUT / (path.stem + '.txt')})"
        if ext == ".zip":
            with zipfile.ZipFile(path) as z:
                return "contains: " + ", ".join(z.namelist()[:20])
        if ext == ".pdf":
            import pymupdf
            with pymupdf.open(path) as doc:
                chars = sum(len(p.get_text()) for p in doc)
                return f"{doc.page_count} pages, {chars} text chars"
        return "not inspected (unsupported type)"
    except Exception as exc:  # report, never hide
        return f"ERROR reading file: {exc}"


def main() -> None:
    files = [p for p in RAW.rglob("*") if p.is_file()]
    if not files:
        print("No files in data/raw yet. Nothing was fabricated.")
        return
    rows = [{
        "path": str(p.relative_to(RAW)),
        "size_kb": round(p.stat().st_size / 1024, 1),
        "sha256_prefix": sha256(p),
        "contents": describe(p),
    } for p in sorted(files)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    for r in rows:
        print(f"\n{r['path']}  ({r['size_kb']} KB)\n  {r['contents']}")
    print(f"\nSaved: {OUT}")


if __name__ == "__main__":
    main()