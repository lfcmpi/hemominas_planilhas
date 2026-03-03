## Feature: Processamento em Lote

**Phase:** 3
**Consolidates roadmap features:** #17 (Processamento em Lote)

### Problem Statement
Em dias de alto volume ou após ausências, o profissional pode acumular vários PDFs de comprovantes para registrar. Processar um por um é ineficiente quando o fluxo individual já está validado.

### User Stories
- Como profissional do banco de sangue, eu quero fazer upload de múltiplos PDFs de uma vez, para que eu processe um acúmulo de comprovantes sem repetir o fluxo para cada arquivo
- Como profissional do banco de sangue, eu quero ver o status de processamento de cada PDF no lote, para que eu saiba quais foram processados com sucesso e quais tiveram problemas

### Acceptance Criteria
- [ ] Interface aceita seleção de múltiplos arquivos PDF simultâneos
- [ ] Cada PDF é processado independentemente (erro em um não bloqueia os demais)
- [ ] Exibe lista de arquivos com status individual: processando, sucesso, erro
- [ ] Tela de preview consolida dados de todos os PDFs antes da escrita
- [ ] Exibe resumo final: "X arquivos processados, Y bolsas importadas, Z erros"

### Scope Boundaries
**In Scope:** Upload múltiplo, processamento independente, status por arquivo, preview consolidado
**Out of Scope:** Agendamento de processamento, monitoramento de pasta/diretório automático

### Risks & Dependencies
- **Depende de:** Features 01-05 (pipeline completo de PDF único funcionando)
- Volume grande de bolsas pode exceder quota da Google Sheets API — considerar batching
