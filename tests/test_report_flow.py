import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import report_cli
import report_flow


TEAM = {
    "name": "Equipa Delta",
    "dashboard_url": "https://cleopatra/BSimpleCollection/bunity/_dashboards/dashboard/123",
    "publish_to": "reports/equipa-delta",
}
CONFIG = {"teams": [TEAM], "global": {"project": "{project}"}}


def sample_data(snapshot=None):
    return {
        "kind": "collection", "team": "Equipa Delta", "sprint": "Sprint-290",
        "captured_at": "2026-09-30 12:00 UTC", "dashboard_url": TEAM["dashboard_url"],
        "metrics": {"total_work_items": {
            "value": 12, "source": "WIQL", "captured_at": "2026-09-30 12:00 UTC"}},
        "warnings": [], "snapshot": snapshot,
    }


def test_team_resolution_and_project(tmp_path):
    assert report_flow.resolve_team(CONFIG, "  equipa DELTA ") == TEAM
    assert report_flow.project_for_team(CONFIG, TEAM) == "bunity"
    with pytest.raises(ValueError, match="não encontrada"):
        report_flow.resolve_team(CONFIG, "Equipa Inexistente")
    config_path = tmp_path / "config.yaml"
    config_path.write_text("teams: []\n", encoding="utf-8")
    assert report_flow.load_config(config_path)["teams"] == []
    with pytest.raises(ValueError, match="fora de reports"):
        report_flow.ensure_not_published_output(report_flow.ROOT / "reports/equipa-delta/draft.md")


def test_collect_records_only_available_structured_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(report_flow, "fetch_ado_metrics", lambda *_: {"total_work_items": "N/A"})
    monkeypatch.setattr(report_flow, "collect_dashboard_widgets", lambda *_: ([{"id": 0, "text": "Sprint"}], None))
    output = tmp_path / "workspace/dashboard.json"
    data = report_flow.collect(CONFIG, "Equipa Delta", "Sprint-290", output, "test-pat")
    assert data["metrics"] == {}
    assert data["widgets"][0]["text"] == "Sprint"
    assert data["warnings"]
    assert "test-pat" not in output.read_text(encoding="utf-8")
    assert report_flow.read_collection(output) == data


def test_render_validate_and_reject_unsupported_claims(tmp_path):
    data = sample_data()
    draft = report_flow.render(data)
    report_flow.validate_draft(draft, data, tmp_path / "draft.md")
    assert "12 work items" in draft
    with pytest.raises(ValueError, match="Número sem evidência"):
        report_flow.validate_draft(draft.replace("12 work items", "42 work items"),
                                   data, tmp_path / "draft.md")
    with pytest.raises(ValueError, match="Número sem evidência"):
        report_flow.validate_draft(draft.replace("12 work items", "29 work items"),
                                   data, tmp_path / "draft.md")
    with pytest.raises(ValueError, match="equipa"):
        report_flow.validate_draft(draft.replace("Rascunho de Sprint – Equipa Delta",
                                                  "Rascunho de Sprint – Outra Equipa"),
                                   data, tmp_path / "draft.md")
    widget_data = {**data, "widgets": [{"id": 0, "text": "Bugs: 42"}]}
    report_flow.validate_draft(draft.replace("12 work items", "42 bugs"),
                               widget_data, tmp_path / "draft.md")


def test_cli_render_stdout_and_file_without_publication(tmp_path, capsys):
    collection = tmp_path / "dashboard.json"
    collection.write_text(json.dumps(sample_data()), encoding="utf-8")
    assert report_cli.main(["render", "--input", str(collection)]) == 0
    assert "# Rascunho de Sprint" in capsys.readouterr().out
    draft = tmp_path / "report.md"
    assert report_cli.main(["render", "--input", str(collection), "--output", str(draft)]) == 0
    assert report_cli.main(["validate", "--input", str(collection), "--draft", str(draft)]) == 0
    assert not (tmp_path / "reports").exists()
    assert report_cli.main(["publish", "--input", str(collection), "--draft", str(draft)]) == 1


def test_snapshot_draft_uses_forward_slashes_and_publish_needs_snapshot(tmp_path):
    image = tmp_path / "source.png"
    image.touch()
    data = sample_data(str(image))
    draft_dir = tmp_path / "output"
    (draft_dir / "snapshots").mkdir(parents=True)
    (draft_dir / "snapshots/source.png").touch()
    draft_path = draft_dir / "draft.md"
    text = report_flow.render(data, image="snapshots/source.png")
    draft_path.write_text(text, encoding="utf-8")
    report_flow.validate_draft(text, data, draft_path)
    with pytest.raises(ValueError, match="--confirm"):
        report_flow.publish_draft(data, draft_path, CONFIG, False)
    with pytest.raises(ValueError, match="snapshot"):
        report_flow.publish_draft({**data, "snapshot": None}, draft_path, CONFIG, True)


def test_explicit_publish_appends_only_after_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(report_flow, "ROOT", tmp_path)
    monkeypatch.setenv("AUDIT_LOG", str(tmp_path / "audit.log"))
    image = tmp_path / "source.png"
    image.touch()
    data = sample_data(str(image))
    draft = tmp_path / "draft.md"
    draft.write_text(report_flow.render(data), encoding="utf-8")
    with pytest.raises(ValueError, match="--confirm"):
        report_flow.publish_draft(data, draft, CONFIG, False)
    assert not (tmp_path / "reports").exists()
    published = Path(report_flow.publish_draft(data, draft, CONFIG, True))
    assert published.exists()
    assert "snapshots/source.png" in published.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="já existe"):
        report_flow.publish_draft(data, draft, CONFIG, True)
    assert published.read_text(encoding="utf-8").count("## Sprint ") == 1
