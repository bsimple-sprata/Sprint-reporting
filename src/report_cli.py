"""Interface local: recolher, redigir, validar e publicar separadamente."""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from report_flow import (
    collect, ensure_not_published_output, load_config, publish_draft, read_collection, render,
    resolve_team, validate_draft,
)

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preparação local de reports de sprint")
    parser.add_argument("--config", type=Path, default=ROOT / "config/config.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    gathering = commands.add_parser("collect", help="Recolher JSON sem publicar")
    gathering.add_argument("--team", required=True)
    gathering.add_argument("--sprint", default=None)
    gathering.add_argument("--output", type=Path)
    gathering.add_argument("--snapshot", action="store_true")
    writing = commands.add_parser("render", help="Mostrar ou guardar um rascunho")
    writing.add_argument("--input", type=Path, required=True)
    writing.add_argument("--output", type=Path, help="Ficheiro Markdown (omissão: stdout)")
    writing.add_argument("--summary-file", type=Path, help="Resumo redigido pelo agente")
    checking = commands.add_parser("validate", help="Validar rascunho e evidências")
    checking.add_argument("--input", type=Path, required=True)
    checking.add_argument("--draft", type=Path, required=True)
    publishing = commands.add_parser("publish", help="Atualizar o histórico cumulativo")
    publishing.add_argument("--input", type=Path, required=True)
    publishing.add_argument("--draft", type=Path, required=True)
    publishing.add_argument("--confirm", action="store_true", help="Autorização explícita para publicar")
    args = parser.parse_args(argv)

    try:
        if args.command == "collect":
            config = load_config(args.config)
            team = resolve_team(config, args.team)
            slug = team["name"].lower().replace(" ", "-")
            sprint = args.sprint or datetime.now(timezone.utc).strftime("%Y-W%V")
            output = args.output or ROOT / "workspace" / slug / "dashboard.json"
            pat = os.getenv("ADO_PAT", "")
            if not pat:
                raise ValueError("Define ADO_PAT no ambiente para recolher dados.")
            collect(config, args.team, sprint, output, pat, args.snapshot)
            print(f"Recolha guardada em {output}")
        elif args.command == "render":
            if args.output:
                ensure_not_published_output(args.output)
            data = read_collection(args.input)
            summary = args.summary_file.read_text(encoding="utf-8") if args.summary_file else None
            image = None
            if args.output and data.get("snapshot"):
                source = Path(data["snapshot"])
                if not source.is_file():
                    raise ValueError("Snapshot da recolha não encontrado.")
                image = f"snapshots/{source.name}"
            text = render(data, summary, image)
            if args.output:
                if image:
                    import shutil
                    dest = args.output.parent / image
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                validate_draft(text, data, args.output)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(text, encoding="utf-8")
                print(f"Rascunho guardado em {args.output}")
            else:
                validate_draft(text, data, Path("draft.md"))
                print(text, end="")
        elif args.command == "validate":
            data = read_collection(args.input)
            validate_draft(args.draft.read_text(encoding="utf-8"), data, args.draft)
            print("Rascunho validado (verificação de afirmações qualitativas pelo agente ainda necessária).")
        else:
            data = read_collection(args.input)
            if not args.confirm:
                raise ValueError("Publicação exige --confirm após autorização explícita do utilizador.")
            config = load_config(args.config)
            print(publish_draft(data, args.draft, config, args.confirm))
    except (ValueError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
