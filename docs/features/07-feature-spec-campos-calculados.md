## Feature: Campos Calculados (Status/Vencimento)

**Phase:** 2
**Consolidates roadmap features:** #12 (Campos Calculados)

### Problem Statement
As colunas A (DIAS ANTES DO VENCIMENTO) e B (STATUS) da planilha são calculadas com base na data de validade. Na planilha original, são fórmulas do Excel. Ao inserir novas linhas via API, essas fórmulas podem não se propagar automaticamente, deixando as colunas vazias.

### User Stories
- Como profissional do banco de sangue, eu quero que as novas linhas já tenham os campos DIAS ANTES DO VENCIMENTO e STATUS preenchidos, para que eu não precise inserir fórmulas manualmente em cada linha nova

### Acceptance Criteria
- [ ] Coluna A recebe fórmula ou valor calculado: DATA VALIDADE - DATA ATUAL
- [ ] Coluna B recebe STATUS baseado no valor de A (ex: "VENCIDO", "VENCE EM X DIAS")
- [ ] O formato do STATUS segue o padrão existente na planilha (verificar padrão exato)
- [ ] Se a planilha usa fórmulas, insere a fórmula; se usa valores estáticos, calcula e insere o valor

### Scope Boundaries
**In Scope:** Preenchimento de colunas A e B com fórmula ou valor calculado para novas linhas
**Out of Scope:** Recalcular colunas A e B de linhas existentes, alertas baseados no status

### Risks & Dependencies
- **Depende de:** Feature 05 (Integração Google Sheets)
- Necessário investigar se a planilha atual usa fórmulas (=D11-HOJE()) ou valores estáticos — isso define a abordagem
- Google Sheets API permite inserir fórmulas diretamente via `valueInputOption: USER_ENTERED`
