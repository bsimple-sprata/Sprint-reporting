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

from summarize import _generate_from_template
from publish import publish_report


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
        snap = os.path.join(tmpdir, "snap.png")
        Path(snap).touch()
        summary = "Resumo de teste.\nTudo bem."
        report_path = publish_report(TEAM, summary, snap, tmpdir, "2024-W01")
        assert Path(report_path).exists()
        content = Path(report_path).read_text(encoding="utf-8")
        assert "Sprint 2024-W01" in content
        assert "Resumo de teste." in content


def test_publish_report_is_cumulative():
    with tempfile.TemporaryDirectory() as tmpdir:
        snap = os.path.join(tmpdir, "snap.png")
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
    snap = str(tmp_path / "snap.png")
    Path(snap).touch()
    pub_module.publish_report(TEAM, "Resumo.", snap, str(tmp_path), "2024-W01")
    assert Path(audit_path).exists()
    content = Path(audit_path).read_text(encoding="utf-8")
    assert "Equipa Test" in content
    assert "2024-W01" in content
