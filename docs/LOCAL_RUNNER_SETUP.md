# Guia de Instalação – Self-Hosted Runner Local (Windows)

> Guia prático para configurar a tua máquina Windows como runner local do GitHub Actions para o projeto Sprint Reporting.  
> Sistema operativo: **Windows 10/11 (64-bit)**. Python **3.13**. Todos os comandos são em **PowerShell**.

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Instalação do self-hosted runner](#2-instalação-do-self-hosted-runner)
3. [Configuração como serviço (auto-start)](#3-configuração-como-serviço-auto-start)
4. [Configuração de labels recomendadas](#4-configuração-de-labels-recomendadas)
5. [Instalação e configuração do Ollama](#5-instalação-e-configuração-do-ollama)
6. [Configuração de secrets e variables no GitHub](#6-configuração-de-secrets-e-variables-no-github)
7. [Teste de conectividade à VPN e Azure DevOps](#7-teste-de-conectividade-à-vpn-e-azure-devops)
8. [Primeiro run manual](#8-primeiro-run-manual)
9. [Validação dos outputs em `reports/`](#9-validação-dos-outputs-em-reports)
10. [Problemas comuns e resolução rápida](#10-problemas-comuns-e-resolução-rápida)
11. [Checklist operacional diário](#11-checklist-operacional-diário)

---

## 1. Pré-requisitos

Confirma que tens instalado na máquina:

| Requisito | Versão mínima | Verificação (PowerShell) |
|---|---|---|
| Git | 2.x | `git --version` |
| Python | 3.13+ | `python --version` |
| PowerShell | 5.1+ (incluso no Windows 10/11) | `$PSVersionTable.PSVersion` |
| VPN corporativa | — | acesso a `dev.azure.com` |
| Ollama | última versão | `ollama --version` |

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

## 5. Instalação e configuração do Ollama

O projeto usa o **Ollama** para gerar resumos executivos com um modelo de linguagem local, sem necessidade de chaves de API externas nem conectividade à internet para inferência.

### 5.1 Instalar o Ollama no Windows

1. Acede a [https://ollama.com/download](https://ollama.com/download).
2. Clica em **Download for Windows** e executa o instalador `.exe`.
3. Segue o assistente de instalação (sem configuração especial necessária).
4. Após a instalação, o Ollama fica disponível em PowerShell:

```powershell
ollama --version
```

### 5.2 Arrancar o serviço Ollama

O instalador do Ollama no Windows regista um serviço de sistema que inicia automaticamente. Verifica se está ativo:

```powershell
# Verificar se o serviço está a correr
Get-Service -Name "Ollama" -ErrorAction SilentlyContinue

# Alternativa: verificar se o endpoint responde
Invoke-WebRequest -Uri "http://127.0.0.1:11434/" -UseBasicParsing | Select-Object StatusCode
```

Resultado esperado: `StatusCode: 200`

Se o serviço não estiver ativo, inicia-o manualmente:

```powershell
# Iniciar como processo em segundo plano
Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden

# Aguardar uns segundos e testar novamente
Start-Sleep -Seconds 3
Invoke-WebRequest -Uri "http://127.0.0.1:11434/" -UseBasicParsing | Select-Object StatusCode
```

### 5.3 Descarregar o modelo

Descarrega o modelo que queres usar (o valor por omissão é `llama3.2`):

```powershell
# Descarregar o modelo (pode demorar alguns minutos dependendo do tamanho)
ollama pull llama3.2
```

Outros modelos recomendados para hardware com menos recursos:

```powershell
ollama pull llama3.2:1b   # Versão mais leve – 1B parâmetros
ollama pull phi3          # Microsoft Phi-3 – boa relação desempenho/tamanho
```

Verificar modelos disponíveis localmente:

```powershell
ollama list
```

### 5.4 Teste de inferência simples

Confirma que o modelo responde corretamente antes de executar o workflow:

```powershell
# Teste via CLI
ollama run llama3.2 "Responde em português: qual é a capital de Portugal?"
```

Ou via API HTTP (sem necessidade de sair do PowerShell):

```powershell
$body = @{
    model  = "llama3.2"
    prompt = "Responde em português: qual é a capital de Portugal?"
    stream = $false
} | ConvertTo-Json

$response = Invoke-WebRequest `
  -Uri "http://127.0.0.1:11434/api/generate" `
  -Method POST `
  -Body $body `
  -ContentType "application/json" `
  -UseBasicParsing

($response.Content | ConvertFrom-Json).response
```

Deves obter uma resposta em texto com a resposta do modelo.

### 5.5 Configurar o modelo no workflow

Por omissão, o código usa `llama3.2` e o endpoint `http://127.0.0.1:11434`. Para usar outro modelo ou URL, define as **Variables** no GitHub (Settings → Secrets and variables → Actions → **Variables**):

| Variable | Valor exemplo | Descrição |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | URL base do serviço Ollama |
| `OLLAMA_MODEL` | `llama3.2` | Modelo a usar para gerar resumos |

> As Variables são valores não-sensíveis visíveis nos logs; usa-as para configuração, não para credenciais.

---

## 6. Configuração de secrets e variables no GitHub

1. Vai ao repositório → **Settings → Secrets and variables → Actions**.

### Secrets (dados sensíveis)

Cria os seguintes secrets em **New repository secret**:

| Secret | Descrição | Obrigatório |
|---|---|---|
| `ADO_PAT` | Personal Access Token do Azure DevOps | ✅ Sim |
| `ADO_ORGANIZATION` | Nome da organização Azure DevOps (ex: `minha-org`) | ✅ Sim |
| `ADO_PROJECT` | Nome do projeto Azure DevOps | ✅ Sim |

### Variables (configuração não sensível)

Em **Variables → New repository variable**, cria opcionalmente:

| Variable | Valor por omissão | Descrição |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | URL base do Ollama na máquina runner |
| `OLLAMA_MODEL` | `llama3.2` | Modelo Ollama para geração de resumos |

> Se não definires estas variables, o código usa os valores por omissão listados acima.

> **Como criar o PAT no Azure DevOps:**
> 1. Acede ao Azure DevOps → clica no teu avatar → **Personal Access Tokens**.
> 2. Clica em **New Token**.
> 3. Define nome, organização e data de expiração.
> 4. Em Scopes, seleciona: **Work Items → Read** e **Dashboards → Read**.
> 5. Clica em **Create** e copia o token (não volta a ser apresentado).

---

## 7. Teste de conectividade à VPN e Azure DevOps

Antes do primeiro run, confirma que a VPN está ativa e as credenciais estão corretas.

### 7.1 Verificar conectividade básica

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

### 7.2 Definir variáveis de ambiente para teste local

```powershell
$env:ADO_PAT = "<o_teu_pat>"
$env:ADO_ORGANIZATION = "<nome_org>"
$env:ADO_PROJECT = "<nome_projeto>"
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:OLLAMA_MODEL = "llama3.2"
```

> Nunca coloques estes valores em ficheiros que sejam committed. Usa sempre variáveis de ambiente ou o ficheiro `.env` (que está no `.gitignore`).

---

## 8. Primeiro run manual

Com o runner online, o Ollama ativo e os secrets configurados:

1. Vai ao repositório no GitHub → separador **Actions**.
2. Seleciona o workflow **"Sprint Report – Geração Automática"** na barra lateral esquerda.
3. Clica em **"Run workflow"** (botão no canto direito).
4. Preenche opcionalmente:
   - **sprint_label**: ex. `2024-W01` (se vazio, é gerado automaticamente)
   - **team**: ex. `Equipa Alpha` (se vazio, processa todas as equipas)
5. Clica em **"Run workflow"** para confirmar.
6. Acompanha a execução em tempo real no separador **Actions**.

---

## 9. Validação dos outputs em `reports/`

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

## 10. Problemas comuns e resolução rápida

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

### Healthcheck Ollama falha – porta 11434 inacessível

**Sintoma:** O passo "Healthcheck – Serviço Ollama" falha com erro de ligação.

**Resolução:**
- Confirma que o Ollama está instalado: `ollama --version`
- Inicia o serviço manualmente:
  ```powershell
  Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
  Start-Sleep -Seconds 3
  Invoke-WebRequest -Uri "http://127.0.0.1:11434/" -UseBasicParsing | Select-Object StatusCode
  ```
- Verifica se alguma firewall local está a bloquear a porta 11434.

### Modelo Ollama não encontrado

**Sintoma:** Nos logs aparece `model "llama3.2" not found` ou similar; o resumo é gerado por template.

**Resolução:**
- Verifica os modelos disponíveis:
  ```powershell
  ollama list
  ```
- Descarrega o modelo em falta:
  ```powershell
  ollama pull llama3.2
  ```
- Se usares um modelo diferente, atualiza a variable `OLLAMA_MODEL` no GitHub (Settings → Variables).

### Timeout na chamada ao Ollama

**Sintoma:** Nos logs aparece `timeout` e o resumo é gerado por template.

**Resolução:**
- O timeout por omissão é de 120 segundos. Se o modelo for muito grande, pode exceder este limite.
- Considera usar um modelo mais leve:
  ```powershell
  ollama pull llama3.2:1b
  ```
  E atualiza a variable `OLLAMA_MODEL` para `llama3.2:1b`.
- Verifica recursos da máquina (CPU/RAM) – modelos grandes em hardware limitado podem ser lentos.

### Healthcheck falha – sem conectividade ao Azure DevOps

- A VPN não está ativa. Liga a VPN corporativa e reinicia o run.
- Testa manualmente:
  ```powershell
  Invoke-WebRequest -Uri "https://dev.azure.com" -UseBasicParsing | Select-Object StatusCode
  ```
  Deve responder com código `200` ou redireccionamento.

### Healthcheck falha – HTTP 401 ou 403 no Azure DevOps

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

## 11. Checklist operacional diário

Nos dias de execução agendada (segunda-feira de semana ímpar, 07:30 UTC), confirma antes das 07:00 UTC:

- [ ] Computador ligado
- [ ] VPN corporativa ativa
- [ ] Runner online em Settings → Actions → Runners
- [ ] Sem alertas de PAT expirado no Azure DevOps
- [ ] Serviço Ollama ativo: `Invoke-WebRequest -Uri "http://127.0.0.1:11434/" -UseBasicParsing | Select-Object StatusCode`
- [ ] Modelo Ollama disponível: `ollama list`

Após a execução (verificar no separador Actions):

- [ ] Workflow concluído com sucesso (ícone verde ✅)
- [ ] Novo commit visível em `reports/` no branch `main`
- [ ] `reports/audit.log` atualizado com a nova execução
- [ ] Artefacto publicado em Actions → sprint-reports-\<run_id\>
