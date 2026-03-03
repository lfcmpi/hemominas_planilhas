## Feature: Extração de Responsável

**Phase:** 2
**Consolidates roadmap features:** #14 (Extração de Responsável)

### Problem Statement
O campo RESPONSÁVEL RECEPÇÃO (coluna K) da planilha identifica quem recebeu as bolsas. No PDF, o nome de quem expediu é digitado ("Expedido por: NILMARA TANIA VELOSO MATOS"), mas o campo "Recebido por" frequentemente é assinatura manuscrita. Extrair ao menos o nome do expedidor já preenche parcialmente o campo.

### User Stories
- Como profissional do banco de sangue, eu quero que o nome do expedidor seja extraído automaticamente do PDF, para que a coluna RESPONSÁVEL RECEPÇÃO tenha pelo menos o nome de quem enviou as bolsas

### Acceptance Criteria
- [ ] Extrai o nome após "Expedido por :" do PDF (campo texto, não manuscrito)
- [ ] Preenche a coluna K (RESPONSÁVEL RECEPÇÃO) com o nome extraído
- [ ] Se o campo não for encontrado, deixa a coluna K em branco (não bloqueia importação)
- [ ] Remove espaços extras e normaliza capitalização do nome

### Scope Boundaries
**In Scope:** Extração do campo "Expedido por" (texto digital) do PDF
**Out of Scope:** OCR de assinatura manuscrita do campo "Recebido por", extração de temperatura

### Risks & Dependencies
- **Depende de:** Feature 02 (Extração de Dados do PDF)
- O campo "Expedido por" é texto digital no PDF — extração confiável
- O campo "Recebido por" é manuscrito — OCR seria impreciso e não vale o risco para MVP/Phase 2
