"""
run_report.py
Ponto de entrada principal. Lê a configuração, executa o ciclo completo
para cada equipa e publica os relatórios cumulativos.

Uso:
    python src/run_report.py [--config config/config.yaml] [--sprint-label LABEL]
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Adicionar src ao path se executado diretamente
sys.path.insert(0, str(Path(__file__).parent))

from snapshot import capture_dashboard_snapshot
from summarize import fetch_ado_metrics, generate_executive_summary
from publish import publish_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("run_report")


def load_config(config_path: str) -> dict:
    with open(config_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_sprint_label() -> str:
    """Gera um label legível para a sprint atual (ex: 2024-W01-W02)."""
    now = datetime.now(timezone.utc)
    week = now.isocalendar()[1]
    year = now.isocalendar()[0]
    return f"{year}-W{week:02d}"


def main():
    parser = argparse.ArgumentParser(description="Sprint Reporting – Azure DevOps")
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Caminho para o ficheiro de configuração (default: config/config.yaml)",
    )
    parser.add_argument(
        "--sprint-label",
        default=None,
        help="Identificador da sprint (default: gerado automaticamente)",
    )
    parser.add_argument(
        "--team",
        default=None,
        help="Executar apenas para uma equipa específica (pelo nome exato)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    global_cfg = config.get("global", {})
    ado_pat = os.environ.get("ADO_PAT", "")
    if not ado_pat:
        logger.error("A variável de ambiente ADO_PAT não está definida.")
        sys.exit(1)

    ado_base_url = os.environ.get("ADO_BASE_URL", "").rstrip("/")
    project = global_cfg.get("project", os.environ.get("ADO_PROJECT", ""))
    report_output_dir = global_cfg.get("report_output_dir", "reports")
    sprint_label = args.sprint_label or get_sprint_label()

    if not ado_base_url:
        logger.error("A variável de ambiente ADO_BASE_URL não está definida.")
        sys.exit(1)

    logger.info("Sprint label: %s", sprint_label)

    teams = config.get("teams", [])
    if args.team:
        teams = [t for t in teams if t["name"] == args.team]
        if not teams:
            logger.error("Equipa '%s' não encontrada na configuração.", args.team)
            sys.exit(1)

    errors = []
    for team in teams:
        team_name = team["name"]
        logger.info("=== A processar equipa: %s ===", team_name)

        # Diretório de imagens para a equipa
        team_slug = team_name.lower().replace(" ", "-")
        image_dir = os.path.join(report_output_dir, team_slug, "snapshots")

        try:
            snapshot_path = capture_dashboard_snapshot(team, image_dir, ado_pat)
        except Exception as exc:
            logger.error("[%s] Erro ao capturar snapshot: %s", team_name, exc)
            errors.append((team_name, "snapshot", str(exc)))
            continue

        try:
            metrics = fetch_ado_metrics(team, ado_pat, project)
        except Exception as exc:
            logger.warning("[%s] Erro ao recolher métricas: %s", team_name, exc)
            metrics = {}

        try:
            summary = generate_executive_summary(team, metrics, snapshot_path)
        except Exception as exc:
            logger.error("[%s] Erro ao gerar resumo: %s", team_name, exc)
            errors.append((team_name, "summary", str(exc)))
            continue

        try:
            report_dir = os.path.join(report_output_dir, team_slug)
            publish_report(team, summary, snapshot_path, report_dir, sprint_label)
        except Exception as exc:
            logger.error("[%s] Erro ao publicar relatório: %s", team_name, exc)
            errors.append((team_name, "publish", str(exc)))
            continue

        logger.info("[%s] Processamento concluído com sucesso.", team_name)

    if errors:
        logger.warning("Processamento terminado com %d erro(s):", len(errors))
        for team_name, stage, msg in errors:
            logger.warning("  [%s] %s: %s", team_name, stage, msg)
        sys.exit(1)
    else:
        logger.info("Todos os relatórios publicados com sucesso.")


if __name__ == "__main__":
    main()
