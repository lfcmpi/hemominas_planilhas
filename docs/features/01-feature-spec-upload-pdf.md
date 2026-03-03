## Feature: Upload de PDF

**Phase:** 1
**Consolidates roadmap features:** #1 (Upload de PDF)

### Problem Statement
O profissional do banco de sangue recebe comprovantes de expedição em PDF da Hemominas e precisa de um ponto de entrada simples para iniciar o processamento. Sem um mecanismo de upload, não há como alimentar o sistema.

### User Stories
- Como profissional do banco de sangue, eu quero fazer upload de um PDF de comprovante de expedição da Hemominas, para que o sistema extraia os dados automaticamente
- Como profissional do banco de sangue, eu quero receber feedback imediato se o arquivo não for um PDF válido, para que eu não perca tempo esperando um processamento que vai falhar

### Acceptance Criteria
- [ ] Interface exibe área de upload com drag-and-drop e botão de seleção de arquivo
- [ ] Aceita apenas arquivos .pdf (rejeita outros formatos com mensagem clara)
- [ ] Limite de tamanho de arquivo: 10MB (suficiente para PDFs de comprovantes com múltiplas páginas)
- [ ] Exibe nome do arquivo selecionado e tamanho antes de processar
- [ ] Botão "Processar" inicia a extração após upload

### Scope Boundaries
**In Scope:** Upload de arquivo único PDF, validação de formato, feedback visual de progresso
**Out of Scope:** Upload de múltiplos PDFs simultâneos (Phase 3 — Processamento em Lote), upload via URL, integração com email

### Risks & Dependencies
- Nenhuma dependência técnica — é o ponto de partida do sistema
- Decisão de plataforma (web app vs. desktop) impacta a implementação do upload
