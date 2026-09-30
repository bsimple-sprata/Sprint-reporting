# Protocolo para preparar reports

1. Interpreta o pedido e resolve a equipa em `config/config.yaml`; confirma a sprint se o identificador atual não for conhecido. Nunca suponhas que a semana ISO corresponde à sprint Azure DevOps.
2. Pergunta se o resultado deve aparecer na CLI ou num ficheiro na pasta atual quando isso não estiver claro.
3. Executa `python src/report_cli.py collect --team "Equipa Delta" --sprint "290"` com `ADO_PAT` e `ADO_BASE_URL` definidos apenas no ambiente. `--snapshot` é opcional. O JSON local fica em `workspace/`; não mostres credenciais em comandos, logs ou texto.
4. Lê o JSON. O total WIQL inclui iterações sob o projeto e **não** representa automaticamente trabalho da sprint selecionada. Identifica widgets/dados em falta; não uses apenas a imagem para justificar valores numéricos.
5. Redige só com evidências disponíveis. Guarda o resumo em `workspace/` e usa `render --input workspace/equipa-delta/dashboard.json --summary-file <ficheiro>`; sem `--output`, apresenta no terminal; com `--output <ficheiro.md>`, guarda-o na pasta escolhida. Se houver screenshot, o render para ficheiro copia-o para `snapshots/` ao lado do rascunho.
6. Executa `validate --input <dashboard.json> --draft <ficheiro.md>` para ficheiros, revê as afirmações qualitativas e as fontes manualmente e assinala qualquer limitação. Um rascunho no terminal não é um report publicado.
7. Só depois de uma autorização explícita para **publicar no histórico** podes executar `publish --input <dashboard.json> --draft <ficheiro.md> --confirm`. A publicação requer screenshot; nunca faças commit ou push automaticamente.

`python src/run_report.py` pertence à automação legada, que publica imediatamente; não o uses no fluxo conversacional.
