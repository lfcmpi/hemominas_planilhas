## Feature: Integração Google Sheets

**Phase:** 1
**Consolidates roadmap features:** #11 (Integração Google Sheets)

### Problem Statement
Sem a escrita automática na planilha, o resultado da extração seria apenas uma tela de dados que o profissional ainda teria que copiar manualmente para o Google Sheets. A integração direta fecha o ciclo de automação completo.

### User Stories
- Como profissional do banco de sangue, eu quero que os dados extraídos do PDF sejam escritos diretamente na planilha "MAPA DE TRANSFUSÃO" no Google Sheets, para que eu não precise copiar nada manualmente
- Como profissional do banco de sangue, eu quero que as novas linhas sejam adicionadas após a última linha existente, para que os dados anteriores não sejam sobrescritos

### Acceptance Criteria
- [ ] Conecta à planilha Google Sheets específica do HMOB via Google Sheets API
- [ ] Escreve dados na aba "MAPA DE TRANSFUSÃO" nas colunas corretas (C, D, H, I, J, K, M)
- [ ] Insere novas linhas após a última linha com dados (append, nunca sobrescreve)
- [ ] Colunas não preenchidas pela extração (A, B, E, F, G, L, N-S) são deixadas em branco
- [ ] Exibe confirmação com número de linhas inseridas e link para a planilha
- [ ] Em caso de erro de escrita, nenhuma linha parcial é inserida (operação atômica)
- [ ] Autenticação via service account ou OAuth2 com permissão de escrita

### Scope Boundaries
**In Scope:** Escrita na aba MAPA DE TRANSFUSÃO, append de linhas, autenticação Google Sheets API
**Out of Scope:** Leitura da planilha para validação (Feature 07), criação de novas planilhas, escrita em outras abas

### Risks & Dependencies
- **Depende de:** Feature 04 (Mapeamento e Conversão de Campos)
- Necessário acesso à Google Sheets API — configuração de credenciais (service account ou OAuth)
- A planilha precisa ser compartilhada com a service account ou o usuário precisa autorizar acesso
- Se a estrutura da planilha mudar (colunas reordenadas/renomeadas), a escrita vai falhar
- Quota da Google Sheets API: 300 requests/min — suficiente para o volume esperado
