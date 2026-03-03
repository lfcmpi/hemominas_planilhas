## Feature: Validação contra BASE

**Phase:** 2
**Consolidates roadmap features:** #13 (Validação contra BASE)

### Problem Statement
A aba BASE da planilha contém as listas oficiais de valores válidos (tipos de hemocomponente, GS/RH, destinos, reações). Dados que não correspondem a essas listas quebram filtros, gráficos e relatórios que dependem de valores exatos.

### User Stories
- Como profissional do banco de sangue, eu quero que o sistema valide os dados extraídos contra as listas da aba BASE antes de inserir na planilha, para que eu tenha certeza que os dados estão no padrão correto
- Como profissional do banco de sangue, eu quero ver claramente quais dados falharam na validação, para que eu corrija antes de enviar

### Acceptance Criteria
- [ ] Lê a aba BASE do Google Sheets para obter listas atualizadas de valores válidos
- [ ] Valida TIPO DE HEMOCOMPONENTE contra lista da BASE (linhas 48+)
- [ ] Valida GS/RH contra lista da BASE (linhas 15-24)
- [ ] Dados inválidos são sinalizados na tela de preview com mensagem específica
- [ ] Importação é bloqueada se houver erros críticos (tipo ou GS/RH inválido)
- [ ] Warnings para campos opcionais que não validam (não bloqueiam importação)

### Scope Boundaries
**In Scope:** Validação de hemocomponente e GS/RH contra BASE, leitura da aba BASE via API
**Out of Scope:** Validação de campos preenchidos manualmente (destino, setor, reação), atualização da aba BASE

### Risks & Dependencies
- **Depende de:** Feature 04 (Mapeamento), Feature 05 (Integração Google Sheets — para ler aba BASE)
- A aba BASE pode ser editada pelos usuários — a leitura deve ser feita a cada importação (não cachear indefinidamente)
- Se a lista BASE for expandida com novos hemocomponentes, o mapeamento da Feature 04 também precisa ser atualizado
