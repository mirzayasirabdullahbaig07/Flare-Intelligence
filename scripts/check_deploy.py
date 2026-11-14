"""Check that the files the deployed app needs exist and that nothing too large is committed."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "app.py", "requirements.txt", "README.md", ".gitignore", ".streamlit/config.toml",
    "research/nasa_sources.csv", "research/findings.csv",
    "data/raw/bass-ii/PSI-25_Experimental table_BASS-II.csv",
    "data/raw/bass-ii/PSI-25_metadata_PSI_metadata_PSI-101_BASS-II.zip",
    "data/processed/chunks.jsonl",
]
SKIP_DIRS = {"venv", ".git", "__pycache__", ".pytest_cache"}
WARN_MB = 50


def main() -> None:
    problems = 0
    print("REQUIRED FILES")
    for rel in REQUIRED:
        path = ROOT / rel
        ok = path.exists() and path.stat().st_size > 0
        print(f"  {'ok     ' if ok else 'MISSING'}  {rel}")
        problems += 0 if ok else 1

    print("\nPAGES")
    for path in sorted((ROOT / "pages").glob("*.py")):
        ok = path.stat().st_size > 0
        print(f"  {'ok     ' if ok else 'EMPTY  '}  {path.name}")
        problems += 0 if ok else 1

    print("\nLARGEST FILES (outside venv)")
    sizes = []
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            p = Path(folder) / name
            sizes.append((p.stat().st_size, p.relative_to(ROOT)))
    for size, rel in sorted(sizes, reverse=True)[:6]:
        mark = "  <- over 50 MB: keep out of GitHub (see .gitignore)" if size > WARN_MB * 1024 * 1024 else ""
        print(f"  {size / 1024 / 1024:7.1f} MB  {rel}{mark}")

    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
    print("\n.GITIGNORE")
    for needle in ["venv/", "__pycache__/", "Summary Report.pdf"]:
        found = needle in ignore
        print(f"  {'ok     ' if found else 'MISSING'}  contains '{needle}'")
        problems += 0 if found else 1

    print("\nRESULT:", "ready to commit" if problems == 0 else f"{problems} problem(s) to fix first")


if __name__ == "__main__":
    main()