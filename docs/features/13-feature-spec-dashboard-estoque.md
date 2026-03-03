## Feature: Dashboard de Estoque

**Phase:** 3
**Consolidates roadmap features:** #19 (Dashboard de Estoque)

### Problem Statement
A planilha contém os dados brutos, mas visualizar rapidamente o estado atual do estoque (quantas bolsas por tipo, quais vencem em breve) exige filtros manuais. Um dashboard dá visão instantânea para decisões operacionais.

### User Stories
- Como profissional do banco de sangue, eu quero ver um painel com o estoque atual de bolsas por tipo sanguíneo e hemocomponente, para que eu tenha visão rápida da disponibilidade
- Como profissional do banco de sangue, eu quero ver quais bolsas estão próximas do vencimento, para que eu priorize seu uso e evite desperdício

### Acceptance Criteria
- [ ] Lê dados atuais da aba MAPA DE TRANSFUSÃO via Google Sheets API
- [ ] Exibe contagem de bolsas em estoque por GS/RH (8 tipos sanguíneos)
- [ ] Exibe contagem de bolsas por tipo de hemocomponente
- [ ] Destaca bolsas com vencimento nos próximos 7, 14, 30 dias
- [ ] Atualização manual (botão refresh) — não precisa ser real-time

### Scope Boundaries
**In Scope:** Visualização de estoque atual, agrupamento por tipo/GS, indicador de vencimento próximo
**Out of Scope:** Gráficos históricos de consumo, previsão de demanda, integração com sistemas de estoque

### Risks & Dependencies
- **Depende de:** Feature 05 (Integração Google Sheets — leitura dos dados)
- Necessário filtrar apenas bolsas "em estoque" (sem destino atribuído na coluna F) vs. já transfundidas
- A planilha já tem gráficos (abas Gráf1-3) — o dashboard pode complementar, não duplicar
