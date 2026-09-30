# Sprint Reporting – Azure DevOps

> Preparação local de rascunhos de sprint review com Copilot CLI e evidências do Azure DevOps.
           A automação cumulativa anterior continua disponível separadamente.

---

## Uso diário no Windows (recomendado)

1. Abre esta pasta no Explorador do Windows e inicia o PowerShell na pasta. Liga a VPN e garante acesso ao dashboard Azure DevOps.
2. Instala as dependências: `python -m pip install -r requirements.txt` e `python -m playwright install chromium`. Instala o [GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli) e autentica-te localmente.
3. Define `ADO_PAT` e `ADO_BASE_URL` **apenas no ambiente** (não os incluas em prompts, ficheiros ou comandos partilhados). Para a configuração atual, `ADO_BASE_URL` é a URL base da coleção, sem o projeto. O projeto é resolvido a partir do dashboard se `global.project` ainda for um placeholder. O PAT precisa de acesso de leitura à API e ao dashboard; a autenticação browser via PAT pode não funcionar em instalações com SSO/NTLM — confirma a sessão local antes de confiar na recolha.
4. Executa `copilot` e pede, por exemplo:

   > Prepara o report da Equipa Delta para a sprint 290. Consulta o dashboard, mostra o rascunho no terminal e não publiques.

   Ou:

   > Prepara o report da Equipa Delta para a sprint 290 e guarda o rascunho em `.\report-equipa-delta.md` na pasta atual. Não faças commit nem push.

O agente `sprint-report-coordinator` segue `AGENTS.md`, recolhe dados com `dashboard-collector`, pede ao `report-writer` um resumo PT-PT e usa `report-validator` para rever estrutura e afirmações. Se o modo de saída ou a sprint não forem conhecidos, confirma-os. O dashboard configurado é lido no browser; os textos de widgets identificáveis e o total WIQL são guardados como evidência em `workspace/` (ignorado pelo Git). **O total WIQL abrange iterações sob o projeto, não é automaticamente o total desta sprint.** A imagem é opcional e nunca substitui dados estruturados. Se a VPN, a autenticação ou os widgets falharem, revê os avisos antes de redigir.

Também podes executar os passos manualmente, em PowerShell, na raiz do repositório:

```powershell
python src/report_cli.py collect --team "Equipa Delta" --sprint "290" --snapshot
python src/report_cli.py render --input workspace/equipa-delta/dashboard.json
python src/report_cli.py render --input workspace/equipa-delta/dashboard.json --output report-equipa-delta.md
python src/report_cli.py validate --input workspace/equipa-delta/dashboard.json --draft report-equipa-delta.md
```

`render` aceita `--summary-file workspace/resumo.md` para texto elaborado pelo agente a partir das evidências. Sem `--output`, mostra só no terminal; com `--output`, cria um ficheiro local e copia a imagem para `snapshots/` junto ao rascunho se existir. A validação Python verifica estrutura, imagem e números, mas as afirmações qualitativas exigem revisão humana/do agente. `workspace/` pode conter informação interna: mantém-no fora do Git.

**Rascunho ≠ validado ≠ publicado.** Só após confirmação explícita para atualizar o histórico cumulativo, e com um snapshot disponível, usa:

```powershell
python src/report_cli.py publish --input workspace/equipa-delta/dashboard.json --draft report-equipa-delta.md --confirm
```

Este comando atualiza `reports/` e o log de auditoria; **não** faz commit nem push. `collect`, `render` e `validate` não publicam. O antigo `python src/run_report.py` executa imediatamente captura, resumo e publicação: reserva-o exclusivamente para a automação opcional, não para pedidos interativos.

---

## Índice

1. [Objetivo](#objetivo)
2. [Arquitetura](#arquitetura)
3. [Estrutura de pastas](#estrutura-de-pastas)
4. [Pré-requisitos](#pré-requisitos)
5. [Como configurar](#como-configurar)
6. [Como executar](#como-executar)
7. [Como adicionar uma nova equipa](#como-adicionar-uma-nova-equipa)
8. [Fluxo automatizado](#fluxo-automatizado)
9. [Publicação e histórico cumulativo](#publicação-e-histórico-cumulativo)
10. [Segurança e credenciais](#segurança-e-credenciais)
11. [Auditoria](#auditoria)
12. [Decisões técnicas](#decisões-técnicas)
13. [Self-hosted runner local](#self-hosted-runner-local)
14. [Troubleshooting](#troubleshooting)

---

## Objetivo

Preparar, rever e apresentar reports de sprint a pedido, no terminal ou em ficheiro local, com recolha auditável do dashboard. A publicação cumulativa e agendada descrita abaixo é um fluxo **legado e opcional**.

---

## Arquitetura (automação opcional legada)

```
Azure DevOps
    │
    │  (PAT – via GitHub Secret)
    ▼
[snapshot.py]  ──────────────────────────────────────────────►  PNG (reports/<equipa>/snapshots/)
    │
    ▼
[summarize.py]  (REST API Azure DevOps + LLM local via Ollama)
    │
    ▼
[publish.py]   ──────────────────────────────────────────────►  Markdown cumulativo (reports/<equipa>/<equipa>.md)
    │
    ▼
[GitHub Actions]  ──► commit automático ──► branch main ──► auditoria (reports/audit.log)
```

**Componentes principais:**

| Componente | Ficheiro | Responsabilidade |
|---|---|---|
| Captura de screenshot | `src/snapshot.py` | Playwright headless → PNG |
| Recolha de métricas | `src/summarize.py` | Azure DevOps REST API |
| Geração de resumo | `src/summarize.py` | LLM local via Ollama (fallback: template) |
| Publicação cumulativa | `src/publish.py` | Markdown por equipa + audit log |
| Regras obrigatórias de report | `src/report_guidelines.py` | Validação automática das guidelines antes de publicar |
| Orquestrador legado | `src/run_report.py` | Pipeline automático que publica |
| Passos locais | `src/report_cli.py` | Recolha, rascunho, validação e publicação explícita |
| Automação | `.github/workflows/sprint-report.yml` | Agendamento GitHub Actions |

---

## Estrutura de pastas

```
Sprint-reporting/
├── .github/
│   └── workflows/
│       └── sprint-report.yml       # Workflow GitHub Actions (agendado a cada 2 semanas)
├── config/
│   └── config.yaml                 # Configuração das 6 equipas
├── reports/                        # Relatórios gerados (committed automaticamente)
│   ├── equipa-alpha/
│   │   ├── equipa-alpha.md         # Relatório cumulativo Markdown
│   │   └── snapshots/              # PNGs (excluídos do git via .gitignore)
│   ├── equipa-beta/
│   │   └── ...
│   └── audit.log                   # Log de auditoria de todas as execuções
├── src/
│   ├── run_report.py               # Ponto de entrada (CLI)
│   ├── snapshot.py                 # Captura de screenshots
│   ├── summarize.py                # Métricas + geração de resumo
│   └── publish.py                  # Publicação cumulativa Markdown
├── templates/
│   └── report_section.md           # Template de referência (documentação)
├── tests/
│   └── test_report.py              # Testes unitários
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Pré-requisitos

- Python 3.13+
- [Playwright](https://playwright.dev/python/) (browser headless)
- Acesso ao Azure DevOps com um Personal Access Token (PAT) com permissões de leitura nos dashboards
- [Ollama](https://ollama.com/) instalado e em execução na máquina runner Windows (porta 11434), com o modelo desejado carregado (ex: `llama3.2`)

---

## Como configurar

### 1. Clonar o repositório

```bash
git clone https://github.com/<org>/Sprint-reporting.git
cd Sprint-reporting
```

### 2. Instalar dependências

```powershell
pip install -r requirements.txt
playwright install chromium
```

### 3. Configurar variáveis de ambiente

Cria um ficheiro `.env` local (nunca commitar):

```dotenv
ADO_PAT=<o_teu_personal_access_token>
ADO_ORGANIZATION=<nome_da_organização>
ADO_PROJECT=<nome_do_projeto>
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
```

Ou define diretamente em PowerShell:

```powershell
$env:ADO_PAT = "..."
$env:ADO_ORGANIZATION = "..."
$env:ADO_PROJECT = "..."
```

### 4. Atualizar `config/config.yaml`

Substitui os placeholders `{organization}`, `{project}` e `{dashboard_id_*}` pelos valores reais de cada equipa.

### 5. Configurar GitHub Secrets e Variables (para automação)

No repositório GitHub → **Settings → Secrets and variables → Actions**, criar:

**Secrets** (dados sensíveis):

| Secret | Descrição |
|---|---|
| `ADO_PAT` | Personal Access Token do Azure DevOps |
| `ADO_ORGANIZATION` | Nome da organização Azure DevOps |
| `ADO_PROJECT` | Nome do projeto Azure DevOps |

**Variables** (configuração não sensível):

| Variable | Descrição | Valor por omissão |
|---|---|---|
| `OLLAMA_BASE_URL` | URL base do serviço Ollama local | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Modelo Ollama a usar para gerar resumos | `llama3.2` |

> Se `OLLAMA_BASE_URL` e `OLLAMA_MODEL` não estiverem definidas, o código usa os valores por omissão acima.

---

## Como executar a automação opcional (publica imediatamente)

### Execução manual (todas as equipas)

```bash
python src/run_report.py
```

### Execução para uma equipa específica

```bash
python src/run_report.py --team "Equipa Alpha"
```

### Especificar sprint label manualmente

```bash
python src/run_report.py --sprint-label "2024-W01-W02"
```

### Usar um ficheiro de configuração alternativo

```bash
python src/run_report.py --config config/config_staging.yaml
```

### Executar testes

```bash
pytest tests/ -v
```

---

## Como adicionar uma nova equipa

1. Abre `config/config.yaml`.
2. Adiciona uma nova entrada na lista `teams`:

```yaml
  - name: "Nova Equipa"
    dashboard_url: "https://dev.azure.com/{org}/{proj}/_dashboards/dashboard/{id}"
    snapshot_time: "09:30"
    timezone: "Europe/Lisbon"
    frequency: "biweekly"
    publish_to: "reports/nova-equipa"
    notes: "Descrição da nova equipa"
```

3. Faz commit e push. Na próxima execução agendada (ou manual), a nova equipa será processada automaticamente.

---

## Fluxo automatizado

```
[Cron: segunda-feira semanas ímpares, 07:30 UTC]
        │
        ▼
[GitHub Actions: sprint-report.yml]
        │
        ├─ checkout + setup Python + install deps
        │
        ├─ verifica se é semana de execução (semanas ímpares)
        │
        ├─ para cada equipa em config.yaml:
        │     ├─ snapshot.py → captura PNG do dashboard
        │     ├─ summarize.py → recolhe métricas + gera resumo
        │     └─ publish.py → valida guidelines + atualiza Markdown cumulativo + audit.log
        │
        ├─ git commit + git push dos relatórios
        │
        └─ upload artefactos (90 dias de retenção)
```

**Execução manual:** disponível via `workflow_dispatch` com parâmetros opcionais (`sprint_label`, `team`).

---

## Publicação e histórico cumulativo

Cada equipa tem o seu próprio ficheiro Markdown em `reports/<equipa-slug>/<equipa-slug>.md`.

A cada ciclo de 2 semanas, é acrescentada uma nova secção ao ficheiro (nunca substituída), com:

- Identificador da sprint
- Timestamp de captura
- Imagem do snapshot (link relativo)
- Resumo executivo (5–10 linhas)

Antes de gravar/publicar, o pipeline valida automaticamente as regras definidas em `docs/docs/reporting-guidelines.md` e falha com erro explícito quando:

- existir um link de imagem com `\` (obrigatório usar `/`);
- uma imagem referenciada não existir em `reports/<equipa>/snapshots/`;
- a estrutura mínima obrigatória do report não for respeitada.

**Exemplo de estrutura do relatório:**

```markdown
# Relatório de Sprint – Equipa Alpha

---

## Sprint 2024-W01

**Capturado em:** 2024-01-08 07:35 UTC

### Snapshot do Dashboard

![Dashboard Equipa Alpha](snapshots/equipa-alpha_20240108_073500.png)

### Resumo Executivo

- Velocidade da equipa mantém-se estável (42 pontos).
- 3 itens em risco de não serem concluídos nesta sprint.
- Taxa de bugs resolvidos: 87%.
- ...

---

## Sprint 2024-W03

...
```

---

## Segurança e credenciais

- **Nunca** commitar o ficheiro `.env` ou qualquer token/credencial.
- O PAT do Azure DevOps deve ter permissão mínima: **Read** em Dashboards e Work Items.
- Todas as credenciais são passadas exclusivamente via variáveis de ambiente ou GitHub Secrets.
- O `.gitignore` está configurado para excluir `.env` e `secrets.yaml`.

---

## Auditoria

Cada execução regista uma linha no ficheiro `reports/audit.log`:

```
2024-01-08 07:35:10 UTC | Equipa Alpha | 2024-W01 | snapshot=reports/equipa-alpha/snapshots/equipa-alpha_20240108_073510.png | report=reports/equipa-alpha/equipa-alpha.md
```

Este ficheiro permite auditar quando cada snapshot foi capturado e qual o relatório correspondente.

---

## Decisões técnicas

| Decisão | Justificação |
|---|---|
| **Playwright** para screenshots | Renderiza corretamente dashboards com JavaScript (Azure DevOps usa SPA) |
| **Markdown + Git** como formato de publicação | Simples, sem dependências externas, histórico nativo via git, legível no GitHub |
| **GitHub Actions** para automação | Integrado com o repositório, sem infraestrutura adicional, suporte a `workflow_dispatch` para execuções manuais |
| **YAML** para configuração | Legível, suportado nativamente em Python, fácil de versionar |
| **Ollama local** para resumos | LLM local sem dependências externas nem custos de API; funciona sem conectividade à internet; fallback automático para template se o serviço estiver indisponível |
| **Semanas ímpares** como trigger biweekly | Simples de implementar no cron, sem necessidade de estado externo |
| **Relatório por equipa** (ficheiro separado) | Isolamento; falha numa equipa não afeta as outras |

---

## Self-hosted runner local

Esta solução está configurada para correr num **self-hosted runner local** — o teu computador liga ao GitHub Actions e executa os workflows com acesso à rede corporativa (via VPN).

### Pré-requisitos da máquina

| Requisito | Versão mínima |
|---|---|
| Sistema operativo | Windows 10/11 (64-bit) |
| Git | 2.x |
| Python | 3.13+ |
| PowerShell | 5.1+ (incluso no Windows 10/11) |
| VPN corporativa | ativa antes de iniciar o runner |
| Acesso ao Azure DevOps | requer PAT válido com permissão Read |
| Ollama | instalado e em execução (porta 11434), modelo carregado |

> Para instruções detalhadas de instalação e configuração no Windows, consulta [`docs/LOCAL_RUNNER_SETUP.md`](docs/LOCAL_RUNNER_SETUP.md).

### Como registar o runner no GitHub

1. Vai ao repositório no GitHub → **Settings → Actions → Runners → New self-hosted runner**.
2. Segue as instruções apresentadas para o teu sistema operativo (download + configuração).
3. Durante a configuração, define as labels: `self-hosted,windows,corp-network,reporting`.
4. Inicia o runner. O workflow irá detetar automaticamente o runner com essas labels.

> Para guia completo passo a passo, consulta [`docs/LOCAL_RUNNER_SETUP.md`](docs/LOCAL_RUNNER_SETUP.md).

### Requisitos operacionais

Para que a execução automática (agendada) funcione:

- ✅ Computador **ligado** no momento agendado (segunda-feira de semana ímpar, 07:30 UTC)
- ✅ Runner **online** (serviço a correr)
- ✅ VPN **ativa** com acesso ao Azure DevOps
- ✅ Serviço **Ollama** ativo na máquina (porta 11434) com modelo carregado

### Como executar snapshot manual

1. Vai ao separador **Actions** no GitHub.
2. Seleciona o workflow **"Sprint Report – Geração Automática"**.
3. Clica em **"Run workflow"**.
4. Preenche opcionalmente o `sprint_label` e/ou `team`.
5. Clica em **"Run workflow"** para confirmar.

---

## Troubleshooting

### Runner offline

**Sintoma:** O workflow fica em fila de espera e não inicia.

**Resolução:**
- Verifica se o serviço do runner está ativo na máquina local:
  ```powershell
  Get-Service -Name "actions.runner.*"
  # ou, se não configurado como serviço:
  Set-Location "$HOME\actions-runner"; .\run.cmd
  ```
- Confirma que o runner aparece como **Online** em Settings → Actions → Runners.

### VPN desligada

**Sintoma:** O healthcheck falha com erro `HTTP 000` ou timeout.

**Resolução:**
- Liga a VPN corporativa antes de iniciar o runner.
- Verifica conectividade em PowerShell:
  ```powershell
  $b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$env:ADO_PAT"))
  (Invoke-WebRequest -Uri "https://dev.azure.com/$env:ADO_ORGANIZATION/_apis/projects?api-version=7.1" -Headers @{ Authorization = "Basic $b64" } -UseBasicParsing).StatusCode
  ```
- Se a resposta for `200`, a VPN e as credenciais estão corretas.

### Falha de autenticação `ADO_PAT`

**Sintoma:** O healthcheck falha com erro `HTTP 401` ou `HTTP 403`.

**Resolução:**
- Verifica se o secret `ADO_PAT` está corretamente configurado em Settings → Secrets → Actions.
- Confirma que o PAT não expirou (Azure DevOps → User Settings → Personal Access Tokens).
- Garante que o PAT tem permissão **Read** em Dashboards e Work Items.
- Após atualizar o secret, lança novo run manual para confirmar.

### Serviço Ollama não acessível

**Sintoma:** O healthcheck Ollama falha ou o resumo é gerado por template com aviso `Ollama indisponível`.

**Resolução:**
- Confirma que o Ollama está instalado e em execução na máquina runner:
  ```powershell
  Invoke-WebRequest -Uri "http://127.0.0.1:11434/" -UseBasicParsing | Select-Object StatusCode
  ```
- Se o serviço não estiver ativo, inicia-o:
  ```powershell
  Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
  ```
- Verifica se o modelo está disponível:
  ```powershell
  ollama list
  ```
- Se o modelo não estiver listado, descarrega-o:
  ```powershell
  ollama pull llama3.2
  ```
- Para testar inferência diretamente:
  ```powershell
  ollama run llama3.2 "Olá, responde em português."
  ```
