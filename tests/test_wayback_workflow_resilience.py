from __future__ import annotations

from pathlib import Path


def test_wayback_results_persist_even_if_replay_enrichment_fails() -> None:
    workflow = Path(".github/workflows/wayback-save.yml").read_text(encoding="utf-8")

    assert "id: replay\n        continue-on-error: true" in workflow
    assert "id: text_replay\n        continue-on-error: true" in workflow
    assert "id: pdf_equivalence\n        continue-on-error: true" in workflow
    assert "- name: Persist archive results and replay evidence\n        if: always()" in workflow
    assert "- name: Surface replay enrichment failures" in workflow
    assert "Terminal Wayback results were persisted, but replay enrichment failed." in workflow
