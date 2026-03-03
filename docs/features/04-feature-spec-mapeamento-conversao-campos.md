## Feature: Mapeamento e Conversão de Campos

**Phase:** 1
**Consolidates roadmap features:** #3 (Mapeamento de Campos), #4 (Conversão GS/RH), #5 (Mapeamento de Hemocomponentes)

### Problem Statement
Os campos do PDF usam formatos e nomes diferentes da planilha. O tipo sanguíneo aparece como "O" + "P" no PDF mas deve ser "O/POS" na planilha. O componente aparece como texto descritivo no PDF mas a planilha usa siglas padronizadas da aba BASE. Sem conversão, os dados não são utilizáveis.

### User Stories
- Como profissional do banco de sangue, eu quero que o tipo sanguíneo seja convertido automaticamente do formato do PDF (ABO + Rh separados) para o formato da planilha (GS/RH combinado), para que os dados fiquem consistentes com o padrão existente
- Como profissional do banco de sangue, eu quero que o nome do hemocomponente do PDF seja mapeado para o nome padronizado da planilha, para que os dados sejam compatíveis com os filtros e relatórios existentes

### Acceptance Criteria
- [ ] Converte ABO + Rh para GS/RH: "O"+"P" → "O/POS", "A"+"N" → "A/NEG", etc. (8 combinações)
- [ ] Mapeia o componente do PDF para o nome padronizado da aba BASE (ex: "CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado" → "CHD - Concentrado de Hemácias Desleucocitado")
- [ ] Produz os dados no formato final das colunas: C (DATA ENTRADA), D (DATA VALIDADE), H (TIPO HEMOCOMPONENTE), I (GS/RH), J (VOLUME), M (Nº DA BOLSA)
- [ ] Sinaliza erro claro quando um componente do PDF não tem correspondência na tabela de mapeamento
- [ ] Sinaliza erro claro quando ABO ou Rh contém valor inesperado

### Scope Boundaries
**In Scope:** Conversão GS/RH (8 combinações), mapeamento de nomes de hemocomponentes usando tabela da aba BASE, formatação de datas, organização dos dados por coluna de destino
**Out of Scope:** Validação completa contra a aba BASE ao vivo (Feature 07), preenchimento de colunas manuais (E-G, L-S)

### Risks & Dependencies
- **Depende de:** Feature 02 (Extração de Dados do PDF)
- A tabela de mapeamento de hemocomponentes precisa ser mantida atualizada — se a Hemominas adicionar novos tipos, o mapeamento deve ser ampliado
- Variações de grafia no PDF (acentuação, abreviações) podem causar falhas no mapeamento fuzzy
- A aba BASE do Excel contém ~30 tipos de hemocomponentes — todos precisam ser mapeáveis
