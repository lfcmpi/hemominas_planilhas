## Feature: Extração de Dados do PDF

**Phase:** 1
**Consolidates roadmap features:** #2 (Extração de Dados), #6 (Data de Entrada), #7 (Data de Validade), #8 (Nº da Bolsa), #9 (Volume)

### Problem Statement
O PDF da Hemominas contém uma tabela estruturada de hemocomponentes com campos específicos. O profissional hoje digita esses dados manualmente na planilha — processo lento, repetitivo e propenso a erros. A extração automática elimina esta etapa.

### User Stories
- Como profissional do banco de sangue, eu quero que o sistema extraia automaticamente todos os dados da tabela de hemocomponentes do PDF, para que eu não precise digitar cada campo manualmente
- Como profissional do banco de sangue, eu quero que a data de recebimento do comprovante seja extraída automaticamente, para que a DATA ENTRADA da planilha seja preenchida corretamente

### Acceptance Criteria
- [ ] Extrai corretamente a tabela de produtos do PDF com todos os campos: Inst. Coleta, Nº Doação, Componente, Cod. ISBT 128, Seq., Vol., ABO, Rh, Validade
- [ ] Extrai a data de emissão/recebimento do cabeçalho do comprovante (campo "em: DD/MM/YYYY")
- [ ] Extrai o Nº do comprovante de expedição
- [ ] Trata corretamente datas no formato DD/MM/YYYY do PDF
- [ ] Trata volumes como números inteiros (ex: "292" → 292)
- [ ] Extrai o "Total de bolsa(s) expedida(s)" e valida contra o número de linhas extraídas
- [ ] Retorna erro claro se o PDF não estiver no formato esperado de "Comprovante de Expedição"

### Scope Boundaries
**In Scope:** Extração de todos os campos da tabela de produtos, data de emissão, nº comprovante, totalizadores
**Out of Scope:** Extração de campos manuscritos (Recebido por, temperaturas — ver Feature 09), OCR de imagens (o PDF é texto selecionável)

### Risks & Dependencies
- **Depende de:** Feature 01 (Upload de PDF)
- O PDF da Hemominas é gerado por sistema (texto selecionável), não é imagem escaneada — isso simplifica a extração
- Se a Hemominas alterar o layout do PDF, a extração pode quebrar — necessário tratamento de erro robusto
- Variações no nome do componente (ex: "Deleucocitado" vs "Desleucocitado") precisam ser mapeadas
