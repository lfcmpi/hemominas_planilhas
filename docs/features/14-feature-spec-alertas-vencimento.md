## Feature: Alertas de Vencimento

**Phase:** 3
**Consolidates roadmap features:** #20 (Alertas de Vencimento)

### Problem Statement
Bolsas de sangue que vencem sem serem utilizadas representam desperdício de recursos críticos. O controle atual depende de verificação manual da planilha, que pode falhar em períodos de alta demanda.

### User Stories
- Como profissional do banco de sangue, eu quero receber alertas quando bolsas estiverem próximas do vencimento, para que eu priorize seu uso ou providencie devolução à Hemominas
- Como gestor do banco de sangue, eu quero configurar os prazos de alerta (ex: 7, 14, 30 dias), para adaptar os avisos à realidade operacional do hospital

### Acceptance Criteria
- [ ] Verifica bolsas com vencimento próximo com base na coluna D (DATA VALIDADE)
- [ ] Prazos de alerta configuráveis (padrão: 7 e 14 dias)
- [ ] Alerta exibe: tipo de hemocomponente, GS/RH, Nº da bolsa, dias até vencimento
- [ ] Canal de notificação definido (email, notificação no app, ou ambos)
- [ ] Frequência de verificação configurável (diária recomendada)

### Scope Boundaries
**In Scope:** Verificação periódica de vencimento, notificação configurável, lista de bolsas em risco
**Out of Scope:** Integração com WhatsApp/SMS, sugestão automática de pacientes para uso, automação de devolução

### Risks & Dependencies
- **Depende de:** Feature 13 (Dashboard de Estoque — compartilha a lógica de leitura e filtro)
- Necessário definir canal de notificação (email é o mais simples para MVP de Phase 3)
- Considerar que bolsas "VENCIDO" já aparecem na planilha — alertas devem ser pré-vencimento apenas
