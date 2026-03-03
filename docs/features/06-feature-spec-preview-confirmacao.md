## Feature: Preview e Confirmação

**Phase:** 2
**Consolidates roadmap features:** #15 (Preview e Confirmação)

### Problem Statement
Erros de extração (campo lido errado, mapeamento incorreto) só seriam descobertos depois de já estarem na planilha, exigindo correção manual. Uma tela de revisão permite ao profissional detectar e corrigir problemas antes da escrita definitiva.

### User Stories
- Como profissional do banco de sangue, eu quero revisar os dados extraídos antes que sejam enviados para a planilha, para que eu possa corrigir erros de extração
- Como profissional do banco de sangue, eu quero poder editar campos individuais na tela de revisão, para que eu corrija dados sem precisar refazer o upload
- Como profissional do banco de sangue, eu quero poder cancelar a importação na tela de revisão, para que dados incorretos não entrem na planilha

### Acceptance Criteria
- [ ] Após extração, exibe tabela com todos os dados mapeados por coluna da planilha
- [ ] Cada campo é editável inline (click para editar)
- [ ] Campos com erro de mapeamento são destacados visualmente (ex: hemocomponente sem correspondência)
- [ ] Botão "Confirmar e Enviar" escreve na planilha; botão "Cancelar" descarta
- [ ] Exibe resumo: "X bolsas de Y comprovantes prontas para importação"

### Scope Boundaries
**In Scope:** Tabela de preview, edição inline, destaque de erros, confirmação/cancelamento
**Out of Scope:** Salvamento de rascunho para continuar depois, comparação lado-a-lado com PDF original

### Risks & Dependencies
- **Depende de:** Feature 04 (Mapeamento — dados para exibir), Feature 05 (Integração Google Sheets — destino da confirmação)
- Campos editáveis precisam de validação (ex: GS/RH aceita apenas valores da lista, volume deve ser numérico)
