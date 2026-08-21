"""
publish.py
Publica o relatório de forma cumulativa em ficheiro Markdown.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from report_guidelines import (
    build_report_section,
    normalize_snapshot_markdown_path,
    validate_report_markdown,
)

logger = logging.getLogger(__name__)

AUDIT_LOG_DEFAULT = "reports/audit.log"


def publish_report(
    team: dict,
    summary: str,
    snapshot_path: str,
    output_dir: str,
    sprint_label: str,
) -> str:
    """
    Adiciona (de forma cumulativa) uma nova secção ao relatório Markdown da equipa.

    Args:
        team: dicionário com os dados da equipa
        summary: texto do resumo executivo
        snapshot_path: caminho relativo para a imagem do snapshot
        output_dir: diretório de destino do relatório
        sprint_label: identificador legível da sprint (ex: "2024-W01-W02")

    Returns:
        Caminho do ficheiro de relatório atualizado
    """
    team_slug = team["name"].lower().replace(" ", "-")
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{team_slug}.md"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Cabeçalho do ficheiro se não existir
    if not report_path.exists():
        header = (
            f"# Relatório de Sprint – {team['name']}\n\n"
            f"> Gerado automaticamente a cada 2 semanas.\n\n"
            f"---\n\n"
        )
        report_path.write_text(header, encoding="utf-8")

    rel_image = normalize_snapshot_markdown_path(snapshot_path, report_dir)
    new_section = build_report_section(team["name"], sprint_label, now, summary, rel_image)

    current_content = report_path.read_text(encoding="utf-8")
    updated_content = f"{current_content}{new_section}"
    validate_report_markdown(updated_content, report_path)
    report_path.write_text(updated_content, encoding="utf-8")

    logger.info("Relatório atualizado: %s", report_path)
    _append_audit(team["name"], sprint_label, snapshot_path, str(report_path), now)
    return str(report_path)


def _append_audit(team_name: str, sprint_label: str, snapshot: str, report: str, timestamp: str) -> None:
    """Regista uma entrada no log de auditoria."""
    audit_log = os.getenv("AUDIT_LOG", AUDIT_LOG_DEFAULT)
    audit_path = Path(audit_log)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    entry = f"{timestamp} | {team_name} | {sprint_label} | snapshot={snapshot} | report={report}\n"
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(entry)
