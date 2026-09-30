"""
Regras obrigatórias de reporting e validações reutilizáveis.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

GUIDELINES_PATH = (
    Path(__file__).resolve().parent.parent / "docs" / "docs" / "reporting-guidelines.md"
)
IMAGE_LINK_RE = re.compile(r"!\[[^\]]*]\(([^)]+)\)")


def _load_guidelines_sections() -> dict[str, list[str]]:
    text = GUIDELINES_PATH.read_text(encoding="utf-8")
    sections: dict[str, list[str]] = {}
    current_section: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            current_section = line.lstrip("#").strip().lower()
            sections[current_section] = []
            continue
        if current_section:
            sections[current_section].append(line)

    return sections


def build_report_section(
    team_name: str,
    sprint_label: str,
    timestamp: str,
    summary: str,
    relative_snapshot_path: str,
) -> str:
    return (
        f"## Sprint {sprint_label}\n\n"
        f"**Capturado em:** {timestamp}\n\n"
        f"### Snapshot do Dashboard\n\n"
        f"![Dashboard {team_name}]({relative_snapshot_path})\n\n"
        f"### Resumo Executivo\n\n"
        f"{summary}\n\n"
        f"---\n\n"
    )


def normalize_snapshot_markdown_path(snapshot_path: str, report_dir: Path) -> str:
    snapshot = Path(snapshot_path)
    if snapshot.is_absolute():
        rel = os.path.relpath(str(snapshot), str(report_dir))
    else:
        rel = str(snapshot)
    return Path(rel).as_posix()


def validate_report_markdown(
    report_markdown: str, report_path: Path, require_snapshot: bool = True
) -> None:
    sections = _load_guidelines_sections()
    required_items = sections.get("estrutura obrigatória do report", [])
    if not required_items:
        raise ValueError(
            "As guidelines não definem a 'estrutura obrigatória do report'. "
            f"Verifica: {GUIDELINES_PATH}"
        )

    required_text = " ".join(required_items).lower()
    errors: list[str] = []

    if "sprint" in required_text and not re.search(r"^##\s+Sprint\s+.+$", report_markdown, re.MULTILINE):
        errors.append("Estrutura obrigatória inválida: secção '## Sprint <label>' em falta.")

    image_paths = [path.strip() for path in IMAGE_LINK_RE.findall(report_markdown)]
    if require_snapshot and "imagem" in required_text and not image_paths:
        errors.append("Estrutura obrigatória inválida: imagem do dashboard em falta.")

    if "resumo" in required_text and "### Resumo Executivo" not in report_markdown:
        errors.append("Estrutura obrigatória inválida: secção '### Resumo Executivo' em falta.")

    expected_snapshots_dir = (report_path.parent / "snapshots").resolve()
    for image_path in image_paths:
        if "\\" in image_path:
            errors.append(
                f"Link de imagem inválido '{image_path}': usa '/' em vez de '\\'."
            )
            continue

        path_obj = Path(image_path)
        if path_obj.is_absolute() or ".." in path_obj.parts:
            errors.append(
                f"Link de imagem inválido '{image_path}': usa caminho relativo em snapshots/."
            )
            continue

        if not image_path.startswith("snapshots/"):
            errors.append(
                f"Link de imagem inválido '{image_path}': deve começar por 'snapshots/'."
            )
            continue

        image_full_path = (report_path.parent / path_obj).resolve()
        if not image_full_path.exists():
            errors.append(
                f"Imagem referenciada não existe: '{image_path}' (esperado em {image_full_path})."
            )
            continue

        if not image_full_path.is_relative_to(expected_snapshots_dir):
            errors.append(
                f"Imagem referenciada fora de snapshots/: '{image_path}'."
            )

    if errors:
        raise ValueError("Validação do relatório falhou:\n- " + "\n- ".join(errors))
