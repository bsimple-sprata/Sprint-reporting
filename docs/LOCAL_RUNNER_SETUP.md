# Guia de Instalação – Self-Hosted Runner Local (Windows)

> Guia prático para configurar a tua máquina Windows como runner local do GitHub Actions para o projeto Sprint Reporting.  
> Sistema operativo: **Windows 10/11 (64-bit)**. Python **3.13**. Todos os comandos são em **PowerShell**.

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Instalação do self-hosted runner](#2-instalação-do-self-hosted-runner)
3. [Configuração como serviço (auto-start)](#3-configuração-como-serviço-auto-start)
4. [Configuração de labels recomendadas](#4-configuração-de-labels-recomendadas)
5. [Configuração de secrets no GitHub](#5-configuração-de-secrets-no-github)
6. [Teste de conectividade à VPN e Azure DevOps](#6-teste-de-conectividade-à-vpn-e-azure-devops)
7. [Primeiro run manual](#7-primeiro-run-manual)
8. [Validação dos outputs em `reports/`](#8-validação-dos-outputs-em-reports)
9. [Problemas comuns e resolução rápida](#9-problemas-comuns-e-resolução-rápida)
10. [Checklist operacional diário](#10-checklist-operacional-diário)

---

## 1. Pré-requisitos

Confirma que tens instalado na máquina:

| Requisito | Versão mínima | Verificação (PowerShell) |
|---|---|---|
| Git | 2.x | `git --version` |
| Python | 3.13+ | `python --version` |
| PowerShell | 5.1+ (incluso no Windows 10/11) | `$PSVersionTable.PSVersion` |
| VPN corporativa | — | acesso a `dev.azure.com` |

Adicionalmente:
- Conta GitHub com acesso de administrador ao repositório `bsimple-sprata/Sprint-reporting`.
- Personal Access Token (PAT) do Azure DevOps com permissão **Read** em Dashboards e Work Items.

> **Python 3.13:** instala a partir de [python.org](https://www.python.org/downloads/). Durante a instalação, assinala a opção **"Add Python to PATH"**.  
> **Git:** instala o Git for Windows a partir de [git-scm.com](https://git-scm.com/download/win).

---

## 2. Instalação do self-hosted runner

### 2.1 Obter o instalador no GitHub

1. Vai ao repositório no GitHub.
2. Clica em **Settings → Actions → Runners → New self-hosted runner**.
3. Seleciona o sistema operativo: **Windows**.
4. Copia e executa os comandos apresentados. Exemplo típico para Windows x64:

```powershell
# Criar pasta dedicada
New-Item -ItemType Directory -Path "$HOME\actions-runner" -Force
Set-Location "$HOME\actions-runner"

# Descarregar o runner (versão apresentada no GitHub)
Invoke-WebRequest `
  -Uri "https://github.com/actions/runner/releases/download/v<VERSION>/actions-runner-win-x64-<VERSION>.zip" `
  -OutFile "actions-runner-win-x64.zip"

# Verificar integridade (hash apresentado no GitHub)
if ((Get-FileHash -Algorithm SHA256 "actions-runner-win-x64.zip").Hash.ToUpper() -ne "<HASH>".ToUpper()) {
    throw "Hash inválido – ficheiro corrompido."
}

# Extrair
Expand-Archive -Path "actions-runner-win-x64.zip" -DestinationPath . -Force
```

> Substitui `<VERSION>` e `<HASH>` pelos valores exatos que o GitHub apresenta no passo anterior.

### 2.2 Configurar o runner

```powershell
Set-Location "$HOME\actions-runner"

# Configurar (substitui <TOKEN> pelo token gerado pelo GitHub)
.\config.cmd `
  --url https://github.com/bsimple-sprata/Sprint-reporting `
  --token <TOKEN> `
  --name "runner-local-$env:COMPUTERNAME" `
  --labels "self-hosted,windows,corp-network,reporting" `
  --work "_work" `
  --unattended
```

O script apenas faz perguntas interativas se `--unattended` não for passado. Com `--unattended`, usa os valores indicados.

### 2.3 Iniciar o runner (modo interativo – teste inicial)

```powershell
Set-Location "$HOME\actions-runner"
.\run.cmd
```

Deves ver uma mensagem como:
```
√ Connected to GitHub
Listening for Jobs
```

---

## 3. Configuração como serviço (auto-start)

Para que o runner inicie automaticamente com o sistema (requer PowerShell como **Administrador**):

```powershell
Set-Location "$HOME\actions-runner"
.\svc.cmd install
.\svc.cmd start
```

Verificar estado:
```powershell
.\svc.cmd status
# ou
Get-Service -Name "actions.runner.*"
```

Para parar ou desinstalar o serviço:
```powershell
.\svc.cmd stop
.\svc.cmd uninstall
```

> O serviço Windows criado pelo runner chama-se `actions.runner.bsimple-sprata-Sprint-reporting.<runner-name>` e pode ser gerido através da consola de Serviços do Windows (`services.msc`) ou com `Get-Service` / `Restart-Service` em PowerShell.

---

## 4. Configuração de labels recomendadas

Durante a configuração (passo 2.2), as labels atribuídas ao runner devem ser:

```
self-hosted,windows,corp-network,reporting
```

Estas labels correspondem exatamente ao `runs-on` definido no workflow:

```yaml
runs-on: [self-hosted, windows, corp-network, reporting]
```

> Se quiseres usar um nome de label diferente, atualiza também o `runs-on` no ficheiro `.github/workflows/sprint-report.yml`.

---

## 5. Configuração de secrets no GitHub

Os secrets são usados pelo workflow para autenticar no Azure DevOps e, opcionalmente, no OpenAI.

1. Vai ao repositório → **Settings → Secrets and variables → Actions → New repository secret**.
2. Cria os seguintes secrets:

| Secret | Descrição | Obrigatório |
|---|---|---|
| `ADO_PAT` | Personal Access Token do Azure DevOps | ✅ Sim |
| `ADO_ORGANIZATION` | Nome da organização Azure DevOps (ex: `minha-org`) | ✅ Sim |
| `ADO_PROJECT` | Nome do projeto Azure DevOps | ✅ Sim |
| `OPENAI_API_KEY` | Chave da API OpenAI para resumos com LLM | ❌ Opcional |

> **Como criar o PAT no Azure DevOps:**
> 1. Acede ao Azure DevOps → clica no teu avatar → **Personal Access Tokens**.
> 2. Clica em **New Token**.
> 3. Define nome, organização e data de expiração.
> 4. Em Scopes, seleciona: **Work Items → Read** e **Dashboards → Read**.
> 5. Clica em **Create** e copia o token (não volta a ser apresentado).

---

## 6. Teste de conectividade à VPN e Azure DevOps

Antes do primeiro run, confirma que a VPN está ativa e as credenciais estão corretas.

### 6.1 Verificar conectividade básica

```powershell
$base64Pat = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$env:ADO_PAT"))
$response = Invoke-WebRequest `
  -Uri "https://dev.azure.com/$env:ADO_ORGANIZATION/_apis/projects?api-version=7.1" `
  -Headers @{ Authorization = "Basic $base64Pat" } `
  -UseBasicParsing
$response.StatusCode
```

Resultado esperado: `200`

| Código | Significado |
|---|---|
| `200` | Tudo certo – VPN e PAT válidos |
| `401` | PAT inválido ou expirado |
| `403` | PAT sem permissões suficientes |
| erro de ligação | Sem conectividade – VPN desligada ou host inacessível |

### 6.2 Definir variáveis de ambiente para teste local

```powershell
$env:ADO_PAT = "<o_teu_pat>"
$env:ADO_ORGANIZATION = "<nome_org>"
$env:ADO_PROJECT = "<nome_projeto>"
```

> Nunca coloques estes valores em ficheiros que sejam committed. Usa sempre variáveis de ambiente ou o ficheiro `.env` (que está no `.gitignore`).

---

## 7. Primeiro run manual

Com o runner online e os secrets configurados:

1. Vai ao repositório no GitHub → separador **Actions**.
2. Seleciona o workflow **"Sprint Report – Geração Automática"** na barra lateral esquerda.
3. Clica em **"Run workflow"** (botão no canto direito).
4. Preenche opcionalmente:
   - **sprint_label**: ex. `2024-W01` (se vazio, é gerado automaticamente)
   - **team**: ex. `Equipa Alpha` (se vazio, processa todas as equipas)
5. Clica em **"Run workflow"** para confirmar.
6. Acompanha a execução em tempo real no separador **Actions**.

---

## 8. Validação dos outputs em `reports/`

Após o run com sucesso, verifica os artefactos gerados:

```powershell
# Navega até ao repositório local (ou faz pull das alterações)
Set-Location "$HOME\Sprint-reporting"
git pull

# Verifica os ficheiros gerados
Get-ChildItem reports/
# Deverás ver pastas por equipa, ex: equipa-alpha\, equipa-beta\

# Abre um relatório para verificar o conteúdo
Get-Content reports\equipa-alpha\equipa-alpha.md

# Verifica o log de auditoria
Get-Content reports\audit.log
```

O ficheiro `audit.log` deve ter uma nova linha com o timestamp da execução, por exemplo:
```
2024-01-08 07:35:10 UTC | Equipa Alpha | 2024-W01 | snapshot=... | report=...
```

Os relatórios também ficam disponíveis como **artefactos** no separador Actions (retenção 90 dias).

---

## 9. Problemas comuns e resolução rápida

### Runner não aparece online no GitHub

- Verifica se o serviço está ativo:
  ```powershell
  Get-Service -Name "actions.runner.*"
  ```
- Reinicia o serviço:
  ```powershell
  Restart-Service -Name "actions.runner.*"
  ```
- Confirma que o token de registo não expirou (tokens de configuração expiram após 1 hora; gera um novo em Settings → Runners se necessário).

### Workflow fica em fila e não inicia

- O runner pode estar offline ou as labels não correspondem.
- Confirma em **Settings → Actions → Runners** que o runner tem estado **Online** e as labels corretas: `self-hosted`, `windows`, `corp-network`, `reporting`.

### Healthcheck falha – sem conectividade

- A VPN não está ativa. Liga a VPN corporativa e reinicia o run.
- Testa manualmente:
  ```powershell
  Invoke-WebRequest -Uri "https://dev.azure.com" -UseBasicParsing | Select-Object StatusCode
  ```
  Deve responder com código `200` ou redireccionamento.

### Healthcheck falha – HTTP 401 ou 403

- O `ADO_PAT` está inválido, expirado ou sem permissões.
- Vai ao Azure DevOps → User Settings → Personal Access Tokens e verifica/renova o token.
- Atualiza o secret `ADO_PAT` no GitHub: Settings → Secrets → Actions → editar `ADO_PAT`.

### Erro de instalação Playwright

```powershell
playwright install chromium
```

- No Windows, o `--with-deps` não é necessário nem suportado; usa sempre apenas `playwright install chromium`.
- Se surgir erro de permissões, executa o PowerShell como Administrador.

### Erro de permissões no git push

- O workflow está configurado com `permissions: contents: write`.
- Se o push falhar, verifica se o token do runner tem permissões de escrita no repositório.

---

## 10. Checklist operacional diário

Nos dias de execução agendada (segunda-feira de semana ímpar, 07:30 UTC), confirma antes das 07:00 UTC:

- [ ] Computador ligado
- [ ] VPN corporativa ativa
- [ ] Runner online em Settings → Actions → Runners
- [ ] Sem alertas de PAT expirado no Azure DevOps

Após a execução (verificar no separador Actions):

- [ ] Workflow concluído com sucesso (ícone verde ✅)
- [ ] Novo commit visível em `reports/` no branch `main`
- [ ] `reports/audit.log` atualizado com a nova execução
- [ ] Artefacto publicado em Actions → sprint-reports-\<run_id\>
