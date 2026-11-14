"""Open every built page through the real app navigation. Run: python tests/test_pages.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from src.ui import built_pages


def walk(node):
    yield node
    children = getattr(node, "children", None)
    if children:
        for child in children.values():
            yield from walk(child)


def page_text(at) -> str:
    return " ".join(str(getattr(n, "proto", "")) for n in walk(at.main))


def main() -> None:
    pages = built_pages()
    assert pages, "no built pages found"
    default = pages[0][0]
    failures = []
    for rel, title, _ in pages:
        try:
            at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
            at.run()
            if rel != default:
                at.switch_page(rel)
                at.run()
            if at.exception:
                failures.append((title, [str(e.value)[:300] for e in at.exception]))
                print(f"  FAIL: {title}")
                continue
            note = ""
            if rel != default and title not in page_text(at):
                note = "  (warning: the page title was not found in the page, check that the page really switched)"
            print(f"  ok: {title}{note}")
        except Exception as exc:  # report every page, do not stop at the first failure
            failures.append((title, [repr(exc)[:300]]))
            print(f"  FAIL: {title}")
    for title, messages in failures:
        print(f"\n{title}:")
        for message in messages:
            print(f"  {message}")
    assert not failures, f"{len(failures)} page(s) failed"
    print("all page tests passed")


if __name__ == "__main__":
    main()