"""
snapshot.py
Captura o snapshot visual do dashboard Azure DevOps usando Playwright.
"""

import os
import logging
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


def capture_dashboard_snapshot(team: dict, output_dir: str, ado_pat: str) -> str:
    """
    Faz login no Azure DevOps e captura um screenshot do dashboard da equipa.

    Args:
        team: dicionário com os dados da equipa (config.yaml)
        output_dir: diretório onde guardar a imagem
        ado_pat: Personal Access Token do Azure DevOps

    Returns:
        Caminho absoluto para o ficheiro de imagem gerado
    """
    team_slug = team["name"].lower().replace(" ", "-")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot_path = Path(output_dir) / f"{team_slug}_{timestamp}.png"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    url = team["dashboard_url"]
    logger.info("A capturar dashboard '%s' em %s", team["name"], url)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            http_credentials={"username": "user", "password": ado_pat}
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=60_000)
        # Aguardar que os widgets carreguem (heurística)
        page.wait_for_timeout(5_000)
        page.screenshot(path=str(snapshot_path), full_page=True)
        browser.close()

    logger.info("Snapshot guardado em %s", snapshot_path)
    return str(snapshot_path)


def collect_dashboard_widgets(team: dict, ado_pat: str, snapshot_dir: str | None = None) -> tuple[list[dict], str | None]:
    """Lê texto visível dos widgets do dashboard; guarda imagem apenas se pedida."""
    widgets = []
    image = None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(http_credentials={"username": "user", "password": ado_pat})
            page = context.new_page()
            response = page.goto(team["dashboard_url"], wait_until="networkidle", timeout=60_000)
            if response is None or response.status >= 400:
                raise ValueError("Dashboard indisponível ou autenticação recusada.")
            page.wait_for_timeout(5_000)
            for index, widget in enumerate(page.locator("[data-widget-id], .widget").all()):
                text = widget.inner_text().strip().replace(ado_pat, "[REDACTED]")
                if text:
                    widgets.append({"id": index, "text": text[:2000]})
            if snapshot_dir:
                slug = team["name"].lower().replace(" ", "-")
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                path = Path(snapshot_dir) / f"{slug}_{timestamp}.png"
                path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(path), full_page=True)
                image = str(path.resolve())
        finally:
            browser.close()
    return widgets, image
