## Feature: Histórico de Importações

**Phase:** 3
**Consolidates roadmap features:** #18 (Histórico de Importações)

### Problem Statement
Sem um registro das importações realizadas, não há como auditar quando e quais bolsas foram registradas, quem fez a importação, ou investigar discrepâncias entre os comprovantes e a planilha.

### User Stories
- Como profissional do banco de sangue, eu quero ver um histórico de todas as importações realizadas, para que eu possa rastrear quando cada conjunto de bolsas foi registrado
- Como gestor do banco de sangue, eu quero poder auditar as importações por período, para fins de controle de qualidade e compliance

### Acceptance Criteria
- [ ] Registra cada importação com: data/hora, nome do arquivo PDF, nº do comprovante, quantidade de bolsas, status (sucesso/parcial/erro)
- [ ] Lista de importações ordenada por data (mais recente primeiro)
- [ ] Filtro por período (data início / data fim)
- [ ] Detalhes da importação exibem as bolsas individuais importadas
- [ ] Histórico persiste entre sessões

### Scope Boundaries
**In Scope:** Log de importações, consulta por período, detalhes por importação
**Out of Scope:** Desfazer importação (rollback), exportação do histórico

### Risks & Dependencies
- **Depende de:** Feature 05 (Integração Google Sheets — evento de escrita gera registro)
- Necessário definir onde armazenar o histórico (aba dedicada na própria planilha? banco local?)
