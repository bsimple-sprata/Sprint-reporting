"""
Testes unitários para o módulo summarize e publish.
Não requerem credenciais reais do Azure DevOps.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from summarize import _generate_from_template, fetch_ado_metrics
from publish import publish_report
from report_guidelines import validate_report_markdown


TEAM = {
    "name": "Equipa Test",
    "dashboard_url": "https://dev.azure.com/org/proj/_dashboards/dashboard/123",
    "snapshot_time": "08:00",
    "timezone": "Europe/Lisbon",
    "frequency": "biweekly",
    "publish_to": "reports/equipa-test",
    "notes": "Equipa de teste",
}


def test_generate_from_template_contains_team_name():
    result = _generate_from_template("Equipa Test", {"total_work_items": 42}, "2024-01-01 00:00 UTC", "/tmp/snap.png")
    assert "Equipa Test" in result
    assert "42" in result


def test_generate_from_template_min_lines():
    result = _generate_from_template("Equipa Test", {}, "2024-01-01 00:00 UTC", "/tmp/snap.png")
    lines = [l for l in result.strip().splitlines() if l.strip()]
    assert len(lines) >= 5


def test_publish_report_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshots_dir = Path(tmpdir) / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        snap = str(snapshots_dir / "snap.png")
        Path(snap).touch()
        summary = "Resumo de teste.\nTudo bem."
        report_path = publish_report(TEAM, summary, snap, tmpdir, "2024-W01")
        assert Path(report_path).exists()
        content = Path(report_path).read_text(encoding="utf-8")
        assert "Sprint 2024-W01" in content
        assert "Resumo de teste." in content
        assert "![Dashboard Equipa Test](snapshots/snap.png)" in content


def test_publish_report_is_cumulative():
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshots_dir = Path(tmpdir) / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        snap = str(snapshots_dir / "snap.png")
        Path(snap).touch()
        publish_report(TEAM, "Resumo sprint 1.", snap, tmpdir, "2024-W01")
        publish_report(TEAM, "Resumo sprint 2.", snap, tmpdir, "2024-W03")
        report_path = Path(tmpdir) / "equipa-test.md"
        content = report_path.read_text(encoding="utf-8")
        assert "Sprint 2024-W01" in content
        assert "Sprint 2024-W03" in content
        assert "Resumo sprint 1." in content
        assert "Resumo sprint 2." in content


def test_audit_log_created(tmp_path, monkeypatch):
    audit_path = str(tmp_path / "audit.log")
    monkeypatch.setenv("AUDIT_LOG", audit_path)
    import importlib
    import publish as pub_module
    importlib.reload(pub_module)
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    snap = str(snapshots_dir / "snap.png")
    Path(snap).touch()
    pub_module.publish_report(TEAM, "Resumo.", snap, str(tmp_path), "2024-W01")
    assert Path(audit_path).exists()
    content = Path(audit_path).read_text(encoding="utf-8")
    assert "Equipa Test" in content
    assert "2024-W01" in content


def test_fetch_ado_metrics_uses_ado_base_url(monkeypatch):
    monkeypatch.setenv("ADO_BASE_URL", "https://cleopatra/BSimpleCollection/")

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"workItems": [{"id": 1}]}

    def fake_post(url, json, auth, timeout):
        assert url == "https://cleopatra/BSimpleCollection/bunity/_apis/wit/wiql?api-version=7.0"
        return DummyResponse()

    monkeypatch.setattr("summarize.requests.post", fake_post)
    metrics = fetch_ado_metrics(TEAM, "pat", "bunity")
    assert metrics["total_work_items"] == 1


def test_fetch_ado_metrics_requires_ado_base_url(monkeypatch):
    monkeypatch.delenv("ADO_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="ADO_BASE_URL não está definido."):
        fetch_ado_metrics(TEAM, "pat", "bunity")


def test_validate_report_detects_backslash_in_image_link(tmp_path):
    report_dir = tmp_path / "equipa-test"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "equipa-test.md"
    markdown = (
        "# Relatório de Sprint – Equipa Test\n\n"
        "## Sprint 2024-W01\n\n"
        "### Snapshot do Dashboard\n\n"
        "![Dashboard Equipa Test](snapshots\\snap.png)\n\n"
        "### Resumo Executivo\n\n"
        "Resumo.\n"
    )
    with pytest.raises(ValueError, match="usa '/' em vez de '\\\\'"):
        validate_report_markdown(markdown, report_path)


def test_validate_report_detects_missing_image(tmp_path):
    report_dir = tmp_path / "equipa-test"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "equipa-test.md"
    markdown = (
        "# Relatório de Sprint – Equipa Test\n\n"
        "## Sprint 2024-W01\n\n"
        "### Snapshot do Dashboard\n\n"
        "![Dashboard Equipa Test](snapshots/snap-inexistente.png)\n\n"
        "### Resumo Executivo\n\n"
        "Resumo.\n"
    )
    with pytest.raises(ValueError, match="Imagem referenciada não existe"):
        validate_report_markdown(markdown, report_path)


def test_validate_report_detects_missing_required_structure(tmp_path):
    report_dir = tmp_path / "equipa-test"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "equipa-test.md"
    markdown = "# Relatório de Sprint – Equipa Test\n\nConteúdo sem estrutura."
    with pytest.raises(ValueError, match="Estrutura obrigatória inválida"):
        validate_report_markdown(markdown, report_path)
