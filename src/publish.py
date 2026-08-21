"""
publish.py
Publica o relatório de forma cumulativa em ficheiro Markdown.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

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

    # Caminho relativo da imagem para o Markdown
    try:
        rel_image = os.path.relpath(snapshot_path, str(report_dir))
    except ValueError:
        # Windows: relpath pode falhar entre drives
        rel_image = snapshot_path

    new_section = (
        f"## Sprint {sprint_label}\n\n"
        f"**Capturado em:** {now}\n\n"
        f"### Snapshot do Dashboard\n\n"
        f"![Dashboard {team['name']}]({rel_image})\n\n"
        f"### Resumo Executivo\n\n"
        f"{summary}\n\n"
        f"---\n\n"
    )

    with report_path.open("a", encoding="utf-8") as fh:
        fh.write(new_section)

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
