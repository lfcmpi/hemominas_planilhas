## Feature: Detecção de Duplicatas

**Phase:** 2
**Consolidates roadmap features:** #16 (Detecção de Duplicatas)

### Problem Statement
Se o mesmo PDF for processado duas vezes (por engano ou esquecimento), as mesmas bolsas seriam inseridas novamente na planilha, criando registros duplicados que distorcem contagens, relatórios e controle de estoque.

### User Stories
- Como profissional do banco de sangue, eu quero que o sistema avise quando uma bolsa já existe na planilha, para que eu não crie registros duplicados por acidente
- Como profissional do banco de sangue, eu quero poder decidir se importo mesmo assim (override), para cobrir casos legítimos de re-processamento

### Acceptance Criteria
- [ ] Antes de inserir, lê a coluna M (Nº DA BOLSA) da planilha para obter bolsas existentes
- [ ] Compara cada bolsa extraída do PDF contra a lista existente
- [ ] Bolsas duplicadas são sinalizadas na tela de preview com indicação clara
- [ ] Usuário pode excluir duplicatas da importação ou forçar inclusão com override
- [ ] Exibe contagem: "X de Y bolsas já existem na planilha"

### Scope Boundaries
**In Scope:** Detecção por Nº DA BOLSA exato, sinalização visual, exclusão/override individual
**Out of Scope:** Detecção por similaridade (fuzzy matching), detecção de duplicatas já existentes na planilha (limpeza)

### Risks & Dependencies
- **Depende de:** Feature 05 (Integração Google Sheets — para ler coluna M)
- Planilha com muitas linhas pode tornar a leitura lenta — considerar cache da coluna M
- O Nº DA BOLSA (Nº Doação do PDF) é o identificador único confiável para comparação
