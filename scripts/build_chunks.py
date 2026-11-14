"""Build data/processed/chunks.jsonl from the real documents and the PSI-25 metadata."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.document_processor import build_corpus, save_chunks
from src.source_manager import (get_publications, get_study_overview, load_investigation,
                                load_source_registry, overview_chunks)


def main() -> None:
    meta_chunks = []
    print("METADATA CHECK (from the PSI-25 zip)")
    try:
        fields = load_investigation()
        overview = get_study_overview(fields)
        pubs = get_publications(fields)
        meta_chunks = overview_chunks(overview)
        print(f"  study_id: {overview['study_id']} | title: {overview['title']}")
        print(f"  dataset_doi: {overview['dataset_doi']} | platform: {overview['flight_platform']}")
        print(f"  publications listed: {len(pubs)}, with DOI: {int((pubs['doi'] != '').sum())}")
        print(f"  metadata chunks created: {len(meta_chunks)}")
    except FileNotFoundError as exc:
        print(f"  STOP: {exc}")

    registry = load_source_registry()
    print(f"\nSOURCE REGISTRY: {len(registry)} entries")

    print("\nDOCUMENTS")
    try:
        chunks, report = build_corpus()
    except FileNotFoundError as exc:
        print(f"  STOP: {exc}")
        return
    for info in report:
        print(f"  {info['file']}: pages={info['n_pages']}, chunks={info['n_chunks']}, "
              f"words={info['n_words']}, pages_without_text={len(info['pages_without_text'])}")
    chunks.extend(meta_chunks)
    path = save_chunks(chunks)
    print(f"\nTotal chunks: {len(chunks)} (including {len(meta_chunks)} metadata chunks)\nSaved: {path}")


if __name__ == "__main__":
    main()