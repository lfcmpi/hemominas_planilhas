## Feature: Suporte Multi-Página

**Phase:** 1
**Consolidates roadmap features:** #10 (Suporte Multi-Página)

### Problem Statement
Um único PDF da Hemominas pode conter múltiplas páginas, cada uma representando um comprovante de expedição diferente (com seu próprio nº, tabela de bolsas e totalizadores). Processar apenas a primeira página significaria perder dados.

### User Stories
- Como profissional do banco de sangue, eu quero que o sistema processe todas as páginas de um PDF com múltiplos comprovantes, para que eu não precise separar o arquivo manualmente
- Como profissional do banco de sangue, eu quero ver quantos comprovantes foram encontrados no PDF, para confirmar que nenhum foi perdido

### Acceptance Criteria
- [ ] Detecta e separa múltiplos comprovantes de expedição dentro de um único PDF
- [ ] Cada comprovante é identificado pelo seu Nº (ex: 1292305, 1292307)
- [ ] Todos os comprovantes são processados — nenhuma página é ignorada
- [ ] Exibe contagem: "X comprovantes encontrados, Y bolsas no total"
- [ ] Valida total de bolsas de cada comprovante contra seu totalizador individual

### Scope Boundaries
**In Scope:** Detecção de múltiplos comprovantes por PDF, processamento sequencial de todas as páginas
**Out of Scope:** Processamento de múltiplos arquivos PDF (Phase 3 — Lote)

### Risks & Dependencies
- **Depende de:** Feature 02 (Extração de Dados do PDF)
- Necessário identificar o delimitador entre comprovantes (cabeçalho "Comprovante de Expedição" + Nº)
- PDFs com comprovantes que ocupam mais de uma página (muitas bolsas) precisam ser tratados
