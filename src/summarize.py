"""
summarize.py
Gera um resumo executivo (5-10 linhas) para um dashboard Azure DevOps,
usando a API do Azure DevOps para recolher métricas e um modelo de
linguagem local via Ollama para gerar texto.
"""

import logging
import os
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

# Configuração do Ollama – pode ser sobreposta por variáveis de ambiente
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def fetch_ado_metrics(team: dict, ado_pat: str, organization: str, project: str) -> dict:
    """
    Recolhe métricas básicas do Azure DevOps via REST API para a equipa.

    Retorna um dicionário com as métricas obtidas.
    """
    headers = {}
    auth = ("", ado_pat)

    team_name = team["name"]
    base = f"https://dev.azure.com/{organization}/{project}"

    # Sanitize project name: allow only alphanumeric, spaces, hyphens, underscores and dots
    import re
    safe_project = re.sub(r"[^A-Za-z0-9 \-_.]", "", project)

    metrics = {}

    # Work items por estado
    wiql_url = f"{base}/_apis/wit/wiql?api-version=7.0"
    query = {
        "query": (
            f"SELECT [System.Id],[System.State],[System.AssignedTo] "
            f"FROM WorkItems WHERE [System.TeamProject] = '{safe_project}' "
            f"AND [System.IterationPath] UNDER '{safe_project}' "
            f"AND [System.State] <> 'Removed' "
            f"ORDER BY [System.ChangedDate] DESC"
        )
    }
    try:
        resp = requests.post(wiql_url, json=query, auth=auth, timeout=30)
        resp.raise_for_status()
        items = resp.json().get("workItems", [])
        metrics["total_work_items"] = len(items)
        logger.info("[%s] Work items obtidos: %d", team_name, len(items))
    except Exception as exc:
        logger.warning("[%s] Não foi possível obter work items: %s", team_name, exc)
        metrics["total_work_items"] = "N/A"

    return metrics


def generate_executive_summary(team: dict, metrics: dict, snapshot_path: str) -> str:
    """
    Gera um resumo executivo de 5 a 10 linhas com base nas métricas recolhidas.

    Se o serviço Ollama estiver disponível, usa o modelo configurado para gerar
    texto mais rico. Caso contrário, produz um resumo baseado em template.
    """
    team_name = team["name"]
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return _generate_with_ollama(team_name, metrics, now, snapshot_path)


def _generate_from_template(team_name: str, metrics: dict, timestamp: str, snapshot_path: str) -> str:
    total = metrics.get("total_work_items", "N/A")
    return (
        f"**Resumo Executivo – {team_name}**\n\n"
        f"- Snapshot capturado em: {timestamp}\n"
        f"- Total de work items em acompanhamento: {total}\n"
        f"- Dashboard disponível para consulta detalhada.\n"
        f"- Snapshot visual guardado em: `{snapshot_path}`\n"
        f"- Revisão recomendada na Sprint Review.\n"
    )


def _generate_with_ollama(team_name: str, metrics: dict, timestamp: str, snapshot_path: str) -> str:
    """Usa o Ollama local para gerar o resumo via API de chat."""
    base_url = OLLAMA_BASE_URL.rstrip("/")
    model = OLLAMA_MODEL
    prompt = (
        f"És um assistente de gestão ágil. Com base nas seguintes métricas da "
        f"equipa '{team_name}' recolhidas em {timestamp}:\n"
        f"{metrics}\n\n"
        f"Escreve um resumo executivo em português europeu de 5 a 10 linhas, "
        f"adequado para uma sprint review, destacando estado geral, riscos e recomendações."
    )
    try:
        resp = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "").strip()
        if text:
            logger.info("[%s] Resumo gerado via Ollama (modelo: %s).", team_name, model)
            return text
        logger.warning("[%s] Ollama devolveu resposta vazia; a usar template.", team_name)
    except Exception as exc:
        logger.warning(
            "[%s] Ollama indisponível (base_url=%s, model=%s): %s – a usar template.",
            team_name, base_url, model, exc,
        )
    return _generate_from_template(team_name, metrics, timestamp, snapshot_path)
