# Instruções do projeto

- Comunica e redige reports em português de Portugal.
- Nunca mostres, registes ou guardes PATs, cookies, tokens ou segredos no report, no JSON ou no Git.
- Não inventes métricas nem transformes ausência de dados em conclusões. Indica sempre a fonte e limitações da recolha.
- Prefere dados estruturados da API/DOM a inferências baseadas apenas num screenshot.
- Distingue **rascunho** (local, não verificado), **report validado** (verificações objetivas e revisão de afirmações concluídas) e **report publicado** (histórico cumulativo atualizado).
- Nunca publiques, faças commit de reports gerados nem push sem confirmação explícita do utilizador. `collect`, `render` e `validate` nunca devem alterar `reports/`.
- Confirma o modo de saída (terminal ou ficheiro na pasta atual) se não for indicado. Se faltarem VPN, autenticação ou evidências, informa o utilizador em vez de improvisar.
