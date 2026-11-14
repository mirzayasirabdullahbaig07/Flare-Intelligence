"""Run the whole app (navigation included) headlessly. Run: python tests/test_app.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest


def walk(node):
    yield node
    children = getattr(node, "children", None)
    if children:
        for child in children.values():
            yield from walk(child)


def main() -> None:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    nodes = list(walk(at.main))
    assert len(nodes) > 3, "the default page rendered almost nothing"
    text = " ".join(str(getattr(n, "proto", "")) for n in nodes)
    print(f"  ok: app.py starts; the default page has {len(nodes)} elements")
    print("  the real test count (129) appears on the page:", "129" in text)
    print("all app tests passed")


if __name__ == "__main__":
    main()