# Hemominas Sheets

Sistema web para gestao de hemocomponentes da Hemominas, com integracao bidirecional ao Google Sheets, upload de comprovantes PDF, dashboard em tempo real e controle de acesso por perfil (RBAC).

## Funcionalidades

- **Upload de PDF**: Extracao automatica de dados de comprovantes de expedicao (pdfplumber + OCR fallback com Tesseract). Suporte a upload individual e em lote (batch).
- **Sincronizacao Google Sheets**: Leitura e escrita bidirecional na planilha "MAPA DE TRANSFUSAO". Sincronizacao periodica via scheduler (APScheduler).
- **Dashboard**: KPIs em tempo real (estoque, entradas 7d/30d, alertas de vencimento), graficos de distribuicao por tipo sanguineo e hemocomponente, evolucao diaria.
- **Consulta de Dados**: Tabela paginada com busca, filtros por vencimento e edicao inline para perfis autorizados.
- **Alertas**: Monitoramento de bolsas proximas ao vencimento com notificacao por email (SMTP) e banners no dashboard.
- **Historico**: Registro completo de todas as importacoes com detalhamento por bolsa.
- **Controle de Acesso (RBAC)**: 4 perfis (admin, manager, uploader, consulta) com permissoes granulares por rota.
- **Gestao de Usuarios**: CRUD completo de usuarios (somente admin).

## Matriz de Permissoes

| Funcionalidade | admin | manager | uploader | consulta |
|---|:---:|:---:|:---:|:---:|
| Upload PDF | X | X | X | - |
| Consulta (visualizar) | X | X | - | X |
| Consulta (editar inline) | X | X | - | - |
| Dashboard | X | X | - | X |
| Historico | X | X | X | X |
| Alertas | X | X | - | - |
| Sincronizacao | X | X | - | X |
| Configuracoes | X | - | - | - |
| Gerenciar Usuarios | X | - | - | - |

## Arquitetura

```
src/
  app.py              # Flask app principal, rotas e endpoints
  auth.py             # Autenticacao, modelo User, RBAC, CRUD usuarios
  config.py           # Configuracoes via .env
  pdf_extractor.py    # Extracao de dados de PDFs
  field_mapper.py     # Mapeamento de campos extraidos
  validators.py       # Validacao de dados
  sheets_reader.py    # Leitura do Google Sheets
  sheets_writer.py    # Escrita no Google Sheets
  sync_service.py     # Sincronizacao bidirecional + consulta paginada
  history_store.py    # SQLite: historico de importacoes + planilha_data
  dashboard_service.py# Agregacao de dados para o dashboard
  alert_service.py    # Verificacao de vencimentos e alertas
  email_sender.py     # Envio de emails via SMTP
  scheduler.py        # APScheduler para tarefas periodicas
  batch_processor.py  # Upload em lote de PDFs
  config_loader.py    # Listas da aba BASE do Sheets (GS/RH, tipos, etc.)
  templates/          # Templates Jinja2 (base, dashboard, consulta, etc.)
  static/             # CSS + JavaScript (dashboard, consulta, usuarios, etc.)

tests/                # 277 testes automatizados (pytest)
data/                 # SQLite database (gitignored)
credentials/          # Service account JSON (gitignored)
```

## Pre-requisitos

- Python 3.10+
- Tesseract OCR (para fallback de OCR em PDFs)
- Conta de servico Google (para integracao com Sheets)

## Instalacao

### 1. Clonar o repositorio

```bash
git clone https://github.com/lfcmpi/hemominas_planilhas.git
cd hemominas_planilhas
```

### 2. Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar Tesseract (opcional, para OCR)

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por
```

### 5. Configurar variaveis de ambiente

Copie o arquivo de exemplo e preencha:

```bash
cp .env.example .env
```

Edite `.env` com os valores do seu ambiente:

```env
# Google Sheets
GOOGLE_SHEETS_ID=id_da_sua_planilha
GOOGLE_CREDENTIALS_PATH=credentials/service-account.json

# SQLite
SQLITE_DB_PATH=data/historico.db

# Email (opcional)
SMTP_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_de_app
SMTP_FROM=seu_email@gmail.com
ALERT_EMAIL_TO=destinatario@gmail.com

# Scheduler (opcional)
SCHEDULER_ENABLED=false
SCHEDULER_ALERT_HOUR=8
SCHEDULER_ALERT_MINUTE=0

# Cache
CACHE_TTL_SECONDS=300

# Auth
SECRET_KEY=gere-uma-chave-secreta-forte
SESSION_LIFETIME_MINUTES=480
```

### 6. Configurar Google Service Account

1. Crie um projeto no [Google Cloud Console](https://console.cloud.google.com/)
2. Ative a API do Google Sheets
3. Crie uma conta de servico e baixe o JSON de credenciais
4. Coloque o arquivo em `credentials/service-account.json`
5. Compartilhe a planilha do Google Sheets com o email da conta de servico

### 7. Inicializar o banco de dados

O banco SQLite e criado automaticamente na primeira execucao. Para popular com dados de teste:

```bash
python seed_mock_data.py
```

### 8. Executar a aplicacao

```bash
python -m src.app
```

A aplicacao estara disponivel em `http://127.0.0.1:4000`.

### 9. Login

Usuario padrao criado automaticamente:

- **Email:** `anavcunha@gmail.com`
- **Senha:** `hemominas2024`
- **Perfil:** admin

## Testes

```bash
python -m pytest tests/ -x -v
```

Os testes cobrem:
- Extracao de PDF e mapeamento de campos
- Validacao de dados
- Historico e banco SQLite
- Rotas da API (consulta, sync, dashboard, upload)
- Autenticacao e RBAC (role_required, has_role)
- CRUD de usuarios
- Edicao inline de dados
- Configuracoes e alertas

## Tecnologias

- **Backend:** Flask, Flask-Login, bcrypt, APScheduler
- **Banco de dados:** SQLite (WAL mode)
- **Extracao PDF:** pdfplumber, pytesseract, pdf2image
- **Google Sheets:** gspread, google-auth
- **Frontend:** HTML/CSS/JS vanilla (sem framework)
- **Testes:** pytest

## Variaveis de Configuracao

| Variavel | Descricao | Default |
|---|---|---|
| `GOOGLE_SHEETS_ID` | ID da planilha Google Sheets | - |
| `GOOGLE_CREDENTIALS_PATH` | Caminho para o JSON da service account | `credentials/service-account.json` |
| `SQLITE_DB_PATH` | Caminho do banco SQLite | `data/historico.db` |
| `SECRET_KEY` | Chave secreta do Flask | `hemominas-secret-change-in-production` |
| `SESSION_LIFETIME_MINUTES` | Duracao da sessao em minutos | `480` |
| `CACHE_TTL_SECONDS` | TTL do cache em segundos | `300` |
| `SYNC_INTERVAL_MINUTES` | Intervalo de sync automatico | `30` |
| `SCHEDULER_ENABLED` | Habilitar scheduler de alertas | `false` |
| `SMTP_ENABLED` | Habilitar envio de email | `false` |
