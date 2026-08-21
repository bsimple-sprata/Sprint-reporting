# Sprint Reporting – Azure DevOps

> Automação de reporting executivo de sprints para 6 equipas, com publicação cumulativa a cada 2 semanas.

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

---

## Objetivo

Recolher automaticamente os dashboards do Azure DevOps de 6 equipas a cada 2 semanas, gerar um resumo executivo de 5 a 10 linhas por equipa e publicar os resultados de forma cumulativa neste repositório para revisão durante a sprint review.

---

## Arquitetura

```
Azure DevOps
    │
    │  (PAT – via GitHub Secret)
    ▼
[snapshot.py]  ──────────────────────────────────────────────►  PNG (reports/<equipa>/snapshots/)
    │
    ▼
[summarize.py]  (REST API Azure DevOps + OpenAI opcional)
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
| Geração de resumo | `src/summarize.py` | Template ou LLM (OpenAI opcional) |
| Publicação cumulativa | `src/publish.py` | Markdown por equipa + audit log |
| Orquestrador | `src/run_report.py` | CLI principal |
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

- Python 3.12+
- [Playwright](https://playwright.dev/python/) (browser headless)
- Acesso ao Azure DevOps com um Personal Access Token (PAT) com permissões de leitura nos dashboards
- (Opcional) Chave OpenAI para geração de resumos com LLM

---

## Como configurar

### 1. Clonar o repositório

```bash
git clone https://github.com/<org>/Sprint-reporting.git
cd Sprint-reporting
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
playwright install chromium --with-deps
```

### 3. Configurar variáveis de ambiente

Cria um ficheiro `.env` local (nunca commitar):

```dotenv
ADO_PAT=<o_teu_personal_access_token>
ADO_ORGANIZATION=<nome_da_organização>
ADO_PROJECT=<nome_do_projeto>
OPENAI_API_KEY=<chave_openai_opcional>
```

Ou exporta diretamente:

```bash
export ADO_PAT="..."
export ADO_ORGANIZATION="..."
export ADO_PROJECT="..."
```

### 4. Atualizar `config/config.yaml`

Substitui os placeholders `{organization}`, `{project}` e `{dashboard_id_*}` pelos valores reais de cada equipa.

### 5. Configurar GitHub Secrets (para automação)

No repositório GitHub → **Settings → Secrets and variables → Actions**, criar:

| Secret | Descrição |
|---|---|
| `ADO_PAT` | Personal Access Token do Azure DevOps |
| `ADO_ORGANIZATION` | Nome da organização Azure DevOps |
| `ADO_PROJECT` | Nome do projeto Azure DevOps |
| `OPENAI_API_KEY` | (Opcional) Chave da API OpenAI |

---

## Como executar

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
        │     └─ publish.py → atualiza Markdown cumulativo + audit.log
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
| **OpenAI opcional** para resumos | Permite enriquecer os resumos sem obrigar a uma dependência externa; funciona sem chave via template |
| **Semanas ímpares** como trigger biweekly | Simples de implementar no cron, sem necessidade de estado externo |
| **Relatório por equipa** (ficheiro separado) | Isolamento; falha numa equipa não afeta as outras |
