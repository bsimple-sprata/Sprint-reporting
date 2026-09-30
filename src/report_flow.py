"""Passos locais e independentes para preparar rascunhos de sprint."""

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

from publish import publish_report
from report_guidelines import build_report_section, validate_report_markdown
from snapshot import capture_dashboard_snapshot
from summarize import fetch_ado_metrics

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("teams"), list):
        raise ValueError("A configuração deve conter uma lista 'teams'.")
    return config


def resolve_team(config: dict, name: str) -> dict:
    matches = [t for t in config["teams"] if isinstance(t, dict)
               and isinstance(t.get("name"), str)
               and t["name"].strip().casefold() == name.strip().casefold()]
    if len(matches) != 1:
        raise ValueError(f"Equipa '{name}' não encontrada ou ambígua em config/config.yaml.")
    if not matches[0].get("dashboard_url"):
        raise ValueError(f"Dashboard não configurado para '{name}'.")
    return matches[0]


def project_for_team(config: dict, team: dict) -> str:
    project = config.get("global", {}).get("project", "")
    if project and not (project.startswith("{") and project.endswith("}")):
        return project
    parts = urlsplit(team["dashboard_url"]).path.split("/")
    if "_dashboards" not in parts or parts.index("_dashboards") < 1:
        raise ValueError("Define 'global.project' na configuração para recolher métricas.")
    return unquote(parts[parts.index("_dashboards") - 1])


def collect(config: dict, team_name: str, sprint: str, output: Path,
            pat: str, snapshot: bool = False) -> dict:
    team = resolve_team(config, team_name)
    project = project_for_team(config, team)
    metrics = fetch_ado_metrics(team, pat, project)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    data = {
        "kind": "collection",
        "team": team["name"],
        "sprint": sprint,
        "captured_at": now,
        "dashboard_url": team["dashboard_url"],
        "metrics": {},
        "warnings": [],
        "snapshot": None,
    }
    total = metrics.get("total_work_items")
    if isinstance(total, int) and not isinstance(total, bool):
        data["metrics"]["total_work_items"] = {
            "value": total,
            "source": f"Azure DevOps WIQL ({project}, iteration under project)",
            "captured_at": now,
        }
    else:
        data["warnings"].append("Total de work items indisponível; não inferir métricas a partir da imagem.")
    if snapshot:
        image = capture_dashboard_snapshot(team, str(output.parent / "snapshots"), pat)
        data["snapshot"] = str(Path(image).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def read_collection(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("kind") != "collection":
        raise ValueError("Ficheiro de recolha inválido.")
    for key in ("team", "sprint", "captured_at", "metrics"):
        if not data.get(key):
            if key != "metrics" or not isinstance(data.get(key), dict):
                raise ValueError(f"Ficheiro de recolha sem '{key}'.")
    return data


def summary_from_collection(data: dict) -> str:
    total = data["metrics"].get("total_work_items")
    lines = [
        f"- Equipa: {data['team']}.",
        f"- Sprint: {data['sprint']}.",
        f"- Recolha efetuada em {data['captured_at']}.",
    ]
    if isinstance(total, dict) and type(total.get("value")) is int:
        lines.append(f"- {total['value']} work items identificados na consulta WIQL (iteração do projeto).")
    else:
        lines.append("- Total de work items indisponível.")
    lines.append("- Estado, riscos e evolução não determinados pelos dados disponíveis.")
    for warning in data.get("warnings", []):
        lines.append(f"- Dados incompletos: {warning}")
    return "\n".join(lines)


def render(data: dict, summary: str | None = None, image: str | None = None) -> str:
    summary = (summary or summary_from_collection(data)).strip()
    if not summary:
        raise ValueError("O resumo não pode estar vazio.")
    if image:
        section = build_report_section(data["team"], data["sprint"], data["captured_at"], summary, image)
    else:
        section = (
            f"## Sprint {data['sprint']}\n\n"
            f"**Capturado em:** {data['captured_at']}\n\n"
            f"### Resumo Executivo\n\n{summary}\n\n---\n\n"
        )
    return f"# Rascunho de Sprint – {data['team']}\n\n{section}"


def validate_draft(markdown: str, data: dict, report_path: Path) -> None:
    if not markdown.startswith(f"# Rascunho de Sprint – {data['team']}\n"):
        raise ValueError("O rascunho não corresponde à equipa recolhida.")
    if f"## Sprint {data['sprint']}\n" not in markdown:
        raise ValueError("O rascunho não corresponde à sprint recolhida.")
    if f"**Capturado em:** {data['captured_at']}" not in markdown:
        raise ValueError("A data de recolha não corresponde aos dados.")
    validate_report_markdown(markdown, report_path, require_snapshot=False)
    summary = markdown.split("### Resumo Executivo\n", 1)[1].split("\n---", 1)[0].strip()
    if not summary:
        raise ValueError("Resumo Executivo vazio.")
    for match in re.findall(r"(?<![\w])\d+(?:[.,]\d+)?%?", summary):
        if match not in (data["sprint"] + " " + data["captured_at"]):
            values = [str(metric.get("value")) for metric in data["metrics"].values()
                      if isinstance(metric, dict)]
            if match not in values:
                raise ValueError(f"Número sem evidência no resumo: {match}.")


def publish_draft(data: dict, draft_path: Path, config: dict, pat_confirmed: bool) -> str:
    if not pat_confirmed:
        raise ValueError("Publicação exige --confirm após autorização explícita do utilizador.")
    draft = draft_path.read_text(encoding="utf-8")
    validate_draft(draft, data, draft_path)
    source = data.get("snapshot")
    if not source or not Path(source).is_file():
        raise ValueError("Publicação exige snapshot existente na recolha.")
    team = resolve_team(config, data["team"])
    output_dir = ROOT / team["publish_to"]
    dest = output_dir / "snapshots" / Path(source).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    summary = draft.split("### Resumo Executivo\n", 1)[1].split("\n---", 1)[0].strip()
    return publish_report(team, summary, str(dest), str(output_dir), data["sprint"])
