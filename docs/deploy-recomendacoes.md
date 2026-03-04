# Recomendacoes de Deploy — HOB Bolsas de Sangue

## Contexto

Aplicacao Flask (Python 3.10+) com dependencias de sistema (Tesseract OCR, Poppler).
Vercel nao eh ideal para este tipo de app — funciona melhor para frontend/Next.js.

## Opcoes Avaliadas

### 1. Render.com (Recomendado)

- Deploy gratuito e simples (similar ao Vercel)
- Conecta direto ao GitHub
- Suporta Python/Flask nativamente
- Free tier disponivel
- Precisa de Dockerfile para instalar Tesseract e Poppler

### 2. Railway.app

- Deploy via GitHub ou CLI
- Free tier com $5 de credito/mes
- Tambem precisaria de Dockerfile

### 3. Fly.io

- Mais setup, mas bom para apps com dependencias de sistema
- Requer Dockerfile + flyctl CLI

## Decisao

**Render.com** com Dockerfile customizado.

## Arquivos Necessarios

- `Dockerfile` — imagem com Python 3.10, Tesseract, Poppler, Gunicorn
- `render.yaml` — configuracao de deploy no Render
- `.dockerignore` — excluir arquivos desnecessarios

## Cuidados

- O `SECRET_KEY` deve ser configurado como variavel de ambiente no Render (nao usar o default)
- As credenciais do Google (`service-account.json`) devem ser tratadas como secret
- O SQLite eh efemero no Render (disco nao persiste entre deploys no free tier)
  - Para testes eh aceitavel; para producao considerar PostgreSQL
- Variavel `PORT` eh injetada pelo Render — o app deve respeita-la
