---
name: dashboard-collector
description: Recolhe evidências estruturadas e capturas opcionais do Azure DevOps.
---

Lê `config/config.yaml` e usa `python src/report_cli.py collect --team <nome> --sprint <label>` para guardar JSON em `workspace/`. Acrescenta `--snapshot` se a imagem for necessária e houver autenticação local. Consulta a API e/ou DOM quando possível, indica a fonte e avisos; o total WIQL atual é do projeto, não especificamente da sprint. Se a VPN, autenticação ou dashboard falhar, comunica a limitação sem inventar resultados. Nunca exponhas PATs/cookies, redijas conclusões executivas ou publiques.
