# PRP: PDF-to-Sheets — Banco de Sangue (Phase 3 Grow)

**Gerado em:** 2026-02-28
**Confidence Score:** 7/10
**Origem:** docs/* (product-roadmap, feature specs 11-14, user journeys 11-13, PRPs phase1)

---

## 1. Core (OBRIGATORIO)

### Goal
Expandir a aplicacao web do banco de sangue do HMOB com funcionalidades alem do fluxo core de importacao: processamento em lote de multiplos PDFs, historico auditavel de importacoes, dashboard de estoque em tempo quase-real, e alertas de vencimento de bolsas.

### Why
Com o pipeline de importacao estavel (Phase 1) e revisao/validacao implementados (Phase 2), os profissionais do banco de sangue precisam de ferramentas para operar em escala (lotes), auditar o que foi importado (historico), visualizar o estado do estoque (dashboard), e prevenir desperdicios por vencimento (alertas). Estas funcionalidades transformam a ferramenta de "automacao de digitacao" em uma plataforma de gestao do banco de sangue.

### What
**Phase 3 Grow — Expansao alem do fluxo core:**
1. Processamento em lote — upload e processamento de multiplos PDFs simultaneamente
2. Historico de importacoes — log auditavel de todas as importacoes com filtro por periodo
3. Dashboard de estoque — visualizacao de bolsas por tipo sanguineo e hemocomponente
4. Alertas de vencimento — notificacao configuravel de bolsas proximas do vencimento

### Success Criteria
- [ ] Upload aceita multiplos PDFs simultaneamente (drag-and-drop ou selecao multipla)
- [ ] Cada PDF e processado independentemente — erro em um nao bloqueia os demais
- [ ] Status individual por arquivo durante processamento (queued, processing, done, error)
- [ ] Preview consolida dados de todos os PDFs do lote antes de escrita
- [ ] Resumo final mostra: X arquivos processados, Y bolsas importadas, Z erros
- [ ] Cada importacao e registrada em SQLite com: data/hora, nome PDF, num comprovante, qtd bolsas, status
- [ ] Tela de historico lista importacoes em ordem cronologica reversa
- [ ] Filtro por periodo (data inicio/fim) funciona corretamente
- [ ] Detalhe de importacao mostra bolsas individuais importadas
- [ ] Historico persiste entre reinicializacoes do servidor
- [ ] Dashboard mostra contagem de bolsas por GS/RH (8 tipos) como barras horizontais
- [ ] Dashboard mostra contagem de bolsas por tipo de hemocomponente
- [ ] Dashboard filtra apenas bolsas "em estoque" (coluna F=DESTINO vazia)
- [ ] Dashboard destaca bolsas vencendo em 7, 14, 30 dias
- [ ] Botao "Atualizar" recarrega dados do Google Sheets
- [ ] Alertas de vencimento com thresholds configuraveis (padrao: 7 e 14 dias)
- [ ] Alerta exibe: tipo hemocomponente, GS/RH, num bolsa, dias ate vencimento
- [ ] Notificacao in-app (banner no dashboard) funciona
- [ ] Notificacao por email funciona (SMTP configuravel)
- [ ] Configuracoes de alerta persistem entre sessoes

---

## 2. Context

### Codebase Analysis
```
BROWNFIELD — Projeto existente com Phase 1 (MVP) e Phase 2 (Enhance) implementados.
Estrutura atual apos Phase 2:

ana_planilha/
├── .claude/settings.local.json
├── .env                           # GOOGLE_SHEETS_ID, GOOGLE_CREDENTIALS_PATH
├── .env.example
├── .gitignore
├── requirements.txt               # flask, pdfplumber, gspread, google-auth, python-dotenv
├── credentials/                   # Google service account JSON (gitignored)
├── docs/                          # Feature specs + user journeys
├── insumos/                       # PDFs e planilhas reais
├── PRPs/prps/                     # PRP files
├── src/
│   ├── app.py                     # Flask app + routes (/api/upload, /api/enviar, /)
│   ├── config.py                  # Configuracoes via .env
│   ├── pdf_extractor.py           # Extracao de dados do PDF (pdfplumber)
│   ├── field_mapper.py            # Mapeamento/conversao de campos
│   ├── sheets_writer.py           # Google Sheets integration (read + write)
│   ├── sheets_reader.py           # Google Sheets reader (BASE tab, duplicates)
│   ├── validator.py               # Validacao contra aba BASE
│   ├── templates/index.html       # SPA frontend com preview/review
│   └── static/
│       ├── style.css
│       └── app.js
└── tests/
    ├── test_pdf_extractor.py
    ├── test_field_mapper.py
    └── test_sheets_writer.py
```

### Modelos de dados existentes (Phase 1+2)

```python
@dataclass
class BolsaExtraida:
    inst_coleta: str; num_doacao: str; componente_pdf: str
    cod_isbt: str; seq: int; volume: int; abo: str; rh: str; validade: date

@dataclass
class Comprovante:
    numero: str; data_emissao: datetime; instituicao: str
    expedido_por: str; data_expedicao: date
    bolsas: list[BolsaExtraida]; total_bolsas_declarado: int

@dataclass
class LinhaPlanilha:
    dias_antes_vencimento: str; status: str
    data_entrada: date; data_validade: date
    tipo_hemocomponente: str; gs_rh: str; volume: int
    responsavel_recepcao: str; num_bolsa: str
```

### Google Sheets Structure (referencia)

**Aba: MAPA DE TRANSFUSAO**
- Header na row 10, dados a partir da row 11
- A=DIAS ANTES VENCIMENTO (formula), B=STATUS (formula), C=DATA ENTRADA, D=DATA VALIDADE, E=DATA TRANSFUSAO/DESTINO, F=DESTINO, G=NOME COMPLETO PACIENTE, H=TIPO HEMOCOMPONENTE, I=GS/RH, J=VOLUME, K=RESPONSAVEL RECEPCAO, L=SETOR TRANSFUSAO, M=Num DA BOLSA, N-S=manual
- Bolsa "em estoque" = coluna F (DESTINO) vazia (sem destino atribuido)
- Bolsa "ja transfundida" = coluna F preenchida

**Aba: BASE** — listas de referencia (GS/RH, hemocomponentes, setores, responsaveis, destinos, reacoes)

### Decisoes de Arquitetura para Phase 3

**Armazenamento do Historico: SQLite**
- Escolhido por simplicidade: sem infra extra, arquivo local, suporte nativo Python
- Alternativa descartada: aba dedicada na planilha (limita queries, consume quota API, mistura dados operacionais com metadados)
- Alternativa descartada: PostgreSQL (overengineering para uso single-user)
- SQLite DB path configuravel via .env (padrao: `data/historico.db`)

**Email para Alertas: SMTP direto**
- Usar smtplib do Python (stdlib, sem dependencia extra)
- Configuracao via .env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_TO
- Alternativa descartada: SendGrid/Mailgun (requer conta, overengineering)
- Fallback: se SMTP nao configurado, alertas apenas in-app

**API Quota Google Sheets:**
- Quota: 300 requests/minuto por projeto
- Dashboard le planilha inteira de uma vez (1 request) em vez de queries por coluna
- Cache local com TTL configuravel (padrao: 5 minutos) para evitar chamadas repetidas
- Batch upload: agrupar todas as bolsas do lote em 1 append call

---

## 3. Tree Structure

### Before (Phase 2 — Current)
```
ana_planilha/
├── .claude/settings.local.json
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── credentials/
├── docs/
├── insumos/
├── PRPs/prps/
├── src/
│   ├── app.py
│   ├── config.py
│   ├── pdf_extractor.py
│   ├── field_mapper.py
│   ├── sheets_writer.py
│   ├── sheets_reader.py
│   ├── validator.py
│   ├── templates/index.html
│   └── static/
│       ├── style.css
│       └── app.js
└── tests/
    ├── test_pdf_extractor.py
    ├── test_field_mapper.py
    └── test_sheets_writer.py
```

### After (Phase 3 — Desired)
```
ana_planilha/
├── .claude/settings.local.json
├── .env                                    # + SMTP_*, ALERT_*, SQLITE_DB_PATH
├── .env.example                            # (modify) adicionar novas variaveis
├── .gitignore                              # (modify) adicionar data/*.db
├── requirements.txt                        # (modify) adicionar apscheduler
├── credentials/
├── data/                                   # (create) diretorio para SQLite
│   └── .gitkeep
├── docs/
├── insumos/
├── PRPs/prps/
├── src/
│   ├── app.py                              # (modify) novas rotas batch/historico/dashboard/alertas
│   ├── config.py                           # (modify) novas variaveis de configuracao
│   ├── pdf_extractor.py                    # (inalterado)
│   ├── field_mapper.py                     # (inalterado)
│   ├── sheets_writer.py                    # (modify) suporte a batch write
│   ├── sheets_reader.py                    # (modify) metodos para dashboard (estoque, vencimentos)
│   ├── validator.py                        # (inalterado)
│   ├── batch_processor.py                  # (create) orquestracao de processamento em lote
│   ├── history_store.py                    # (create) CRUD SQLite para historico de importacoes
│   ├── dashboard_service.py                # (create) logica de agregacao de estoque
│   ├── alert_service.py                    # (create) verificacao de vencimento + notificacoes
│   ├── email_sender.py                     # (create) envio de emails via SMTP
│   ├── scheduler.py                        # (create) agendamento de tarefas (alertas diarios)
│   ├── templates/
│   │   ├── index.html                      # (modify) adaptar upload para modo lote
│   │   ├── history.html                    # (create) tela de historico de importacoes
│   │   ├── history_detail.html             # (create) detalhe de uma importacao
│   │   ├── dashboard.html                  # (create) dashboard de estoque + vencimentos
│   │   └── alert_settings.html             # (create) configuracao de alertas
│   └── static/
│       ├── style.css                       # (modify) estilos para novas telas
│       ├── app.js                          # (modify) logica batch upload
│       ├── history.js                      # (create) logica tela de historico
│       ├── dashboard.js                    # (create) logica dashboard + graficos de barra
│       └── alert_settings.js               # (create) logica config alertas
└── tests/
    ├── test_pdf_extractor.py               # (inalterado)
    ├── test_field_mapper.py                # (inalterado)
    ├── test_sheets_writer.py               # (inalterado)
    ├── test_batch_processor.py             # (create) testes processamento em lote
    ├── test_history_store.py               # (create) testes CRUD historico
    ├── test_dashboard_service.py           # (create) testes agregacao dashboard
    └── test_alert_service.py               # (create) testes alertas vencimento
```

---

## 4. Known Gotchas

| # | Gotcha | Solucao |
|---|--------|---------|
| 1 | **Quota da Google Sheets API (300 req/min):** Batch upload com muitos PDFs pode gerar multiplas chamadas (leitura para duplicatas + escrita). Se 10 PDFs com 6 bolsas cada = 60 bolsas, cada verificacao de duplicata pode consumir requests. | Agrupar operacoes: (a) ler planilha inteira 1x no inicio do lote, (b) verificar duplicatas localmente contra os dados carregados, (c) fazer 1 unico append_rows com todas as bolsas validadas. Maximo: 2-3 requests por lote inteiro. |
| 2 | **SQLite concorrencia:** Flask em modo desenvolvimento usa 1 thread, mas em producao com gunicorn pode ter multiplas threads/workers. SQLite nao suporta bem escrita concorrente. | Usar `check_same_thread=False` na conexao, e `WAL mode` (Write-Ahead Logging) para melhor concorrencia. Para o caso de uso single-user do HMOB, o risco e minimo. |
| 3 | **Migracoes do SQLite:** Se o schema do historico mudar entre versoes, nao ha migracao automatica. | Criar tabelas com `CREATE TABLE IF NOT EXISTS` e versionar schema. Se necessario, adicionar colunas com `ALTER TABLE ... ADD COLUMN ... DEFAULT`. Manter simples — sem migration framework. |
| 4 | **Email SMTP em rede hospitalar:** Redes hospitalares frequentemente bloqueiam portas SMTP (25, 587, 465) ou exigem proxy. | Tornar email opcional: se SMTP nao configurado, alertas funcionam apenas in-app. Documentar configuracao SMTP no .env.example. Testar com variavel SMTP_ENABLED=true/false. |
| 5 | **Cache do dashboard desatualizado:** O dashboard le dados do Sheets e cacheia por 5 min. Se uma importacao acontece e o usuario vai ao dashboard imediatamente, pode nao ver as bolsas recem-importadas. | Apos importacao bem-sucedida, invalidar cache do dashboard explicitamente. Botao "Atualizar" no dashboard sempre forca leitura fresca (bypass cache). |
| 6 | **Bolsas "em estoque" vs "transfundidas":** O criterio e coluna F (DESTINO) vazia. Mas pode haver bolsas devolvidas, descartadas, etc. que nao tem destino mas tambem nao estao "em estoque". | Usar criterio conservador: "em estoque" = coluna F vazia E coluna E (DATA TRANSFUSAO/DESTINO) vazia. Bolsas com E preenchida mas F vazia sao ambiguas — incluir mas sinalizar. |
| 7 | **Tamanho da planilha para dashboard:** Planilha com 12700+ rows — ler tudo via API demora e consome memoria. | Usar `worksheet.get_all_values()` que retorna todas as linhas de uma vez (1 API call). Filtrar em Python. Para planilhas muito grandes (>50k rows), considerar paginacao no futuro. |
| 8 | **Fuso horario nos alertas:** Verificacao de vencimento compara `DATA VALIDADE` com `today()`. Se o servidor roda em fuso diferente de Brasilia (BRT/UTC-3), os alertas podem disparar no dia errado. | Forcar timezone Brasilia no calculo: `datetime.now(ZoneInfo('America/Sao_Paulo')).date()`. Adicionar `tzdata` ao requirements se necessario. |
| 9 | **Processamento em lote — arquivos duplicados:** Usuario pode selecionar o mesmo PDF duas vezes no lote, ou PDFs com os mesmos comprovantes. | Antes de processar: (a) detectar filenames duplicados no lote, (b) apos extracao, detectar nums de bolsa duplicados entre PDFs do lote, (c) detectar contra planilha existente (reusa logica Phase 2). |
| 10 | **Scheduler em desenvolvimento vs producao:** APScheduler roda dentro do processo Flask. Em dev com auto-reload, pode criar multiplas instancias do scheduler. | Usar flag ou PID file para garantir unica instancia. Em dev, desabilitar scheduler por padrao (SCHEDULER_ENABLED=false). |

---

## 5. Implementation Blueprint

### Tech Stack (Adicoes para Phase 3)

| Componente | Tecnologia | Justificativa |
|------------|-----------|---------------|
| Historico DB | **SQLite** (stdlib) | Sem dependencia extra, Python nativo, suficiente para single-user |
| Scheduler | **APScheduler** | Agendamento de tarefas (alerta diario) dentro do processo Flask |
| Email | **smtplib** (stdlib) | Envio SMTP nativo Python, sem dependencia |
| Barras Dashboard | **HTML/CSS puro** | Barras horizontais com `<div>` + width percentual, sem lib de graficos |
| Timezone | **zoneinfo** (stdlib 3.9+) | Fuso horario Brasilia para alertas |

### Dependencias Adicionais (requirements.txt)

```
# Phase 1+2 (existentes)
flask>=3.0
pdfplumber>=0.11
gspread>=6.0
google-auth>=2.0
google-auth-oauthlib>=1.0
python-dotenv>=1.0

# Phase 3 (novas)
APScheduler>=3.10
```

### Data Models (Novos para Phase 3)

```python
# Registro de uma importacao no historico
@dataclass
class ImportRecord:
    id: int                        # PK autoincrement
    timestamp: datetime            # Data/hora da importacao
    filename: str                  # Nome do arquivo PDF
    comprovante_nums: str          # Nums dos comprovantes (comma-separated)
    bolsa_count: int               # Quantidade de bolsas importadas
    status: str                    # "sucesso" | "parcial" | "erro"
    error_message: str | None      # Mensagem de erro, se houver

# Detalhe de cada bolsa importada (ligada a ImportRecord)
@dataclass
class ImportBolsaDetail:
    id: int                        # PK autoincrement
    import_id: int                 # FK -> ImportRecord.id
    num_bolsa: str                 # Num da bolsa
    tipo_hemocomponente: str       # Tipo mapeado
    gs_rh: str                     # Tipo sanguineo
    volume: int                    # Volume em ML
    data_validade: date            # Data de validade

# Dados agregados para o dashboard
@dataclass
class EstoqueResumo:
    por_gs_rh: dict[str, int]      # {"O/POS": 24, "A/POS": 20, ...}
    por_hemocomponente: dict[str, int]  # {"CHD": 45, "PFC": 12, ...}
    total_em_estoque: int
    vencendo_7d: list[dict]        # Bolsas vencendo em 7 dias
    vencendo_14d: list[dict]       # Bolsas vencendo em 14 dias
    vencendo_30d: list[dict]       # Bolsas vencendo em 30 dias
    ultima_atualizacao: datetime

# Configuracao de alertas
@dataclass
class AlertConfig:
    threshold_urgente: int         # Dias (padrao: 7)
    threshold_atencao: int         # Dias (padrao: 14)
    email_enabled: bool            # Enviar email?
    email_to: str | None           # Destinatario
    inapp_enabled: bool            # Mostrar no app?

# Status de processamento de um arquivo no lote
@dataclass
class BatchFileStatus:
    filename: str
    status: str                    # "queued" | "processing" | "done" | "error"
    comprovante_count: int | None
    bolsa_count: int | None
    error_message: str | None
    linhas: list[LinhaPlanilha] | None  # Dados extraidos (None se error)
```

### Database Schema (SQLite)

```sql
CREATE TABLE IF NOT EXISTS import_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,        -- ISO 8601
    filename TEXT NOT NULL,
    comprovante_nums TEXT,          -- "1292305,1292307"
    bolsa_count INTEGER NOT NULL,
    status TEXT NOT NULL,           -- "sucesso", "parcial", "erro"
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS import_bolsas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id INTEGER NOT NULL,
    num_bolsa TEXT NOT NULL,
    tipo_hemocomponente TEXT NOT NULL,
    gs_rh TEXT NOT NULL,
    volume INTEGER NOT NULL,
    data_validade TEXT NOT NULL,    -- ISO 8601 date
    FOREIGN KEY (import_id) REFERENCES import_records(id)
);

CREATE TABLE IF NOT EXISTS alert_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Singleton row
    threshold_urgente INTEGER NOT NULL DEFAULT 7,
    threshold_atencao INTEGER NOT NULL DEFAULT 14,
    email_enabled INTEGER NOT NULL DEFAULT 0,
    email_to TEXT,
    inapp_enabled INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_import_records_timestamp ON import_records(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_import_bolsas_import_id ON import_bolsas(import_id);
```

### API Contracts

```yaml
# === BATCH PROCESSING (Feature 11) ===

POST /api/batch/upload:
  description: Upload multiplos PDFs e extrai dados de todos
  request:
    content-type: multipart/form-data
    body:
      files: PDF files[] (max 10 files, 10MB each)
  response:
    200:
      batch_id: str               # UUID do lote
      files: array
        - filename: str
          status: "done" | "error"
          comprovantes: int | null
          bolsas: int | null
          error: str | null
          linhas: array | null     # Dados mapeados (mesmo formato /api/upload)
      summary:
        total_files: int
        success_files: int
        error_files: int
        total_bolsas: int
    400:
      error: str                   # "Nenhum arquivo enviado" / "Maximo 10 arquivos"

POST /api/batch/enviar:
  description: Envia dados consolidados do lote para Google Sheets
  request:
    content-type: application/json
    body:
      linhas: array                # Consolidado de todos os PDFs do lote
  response:
    200:
      linhas_inseridas: int
      import_ids: array[int]       # IDs dos registros no historico
      mensagem: str
    500:
      error: str

# === HISTORICO (Feature 12) ===

GET /api/historico:
  description: Lista importacoes com filtro opcional por periodo
  params:
    data_inicio: str (optional)    # DD/MM/YYYY
    data_fim: str (optional)       # DD/MM/YYYY
    page: int (optional, default 1)
    per_page: int (optional, default 20)
  response:
    200:
      importacoes: array
        - id: int
          timestamp: str           # DD/MM/YYYY HH:MM
          filename: str
          comprovante_nums: str
          bolsa_count: int
          status: str
      total: int
      page: int
      per_page: int

GET /api/historico/<id>:
  description: Detalhe de uma importacao especifica
  response:
    200:
      importacao:
        id: int
        timestamp: str
        filename: str
        comprovante_nums: str
        bolsa_count: int
        status: str
        error_message: str | null
      bolsas: array
        - num_bolsa: str
          tipo_hemocomponente: str
          gs_rh: str
          volume: int
          data_validade: str
    404:
      error: str

# === DASHBOARD (Feature 13) ===

GET /api/dashboard:
  description: Dados agregados de estoque atual
  params:
    force_refresh: bool (optional, default false)  # Bypass cache
  response:
    200:
      por_gs_rh:                   # Ordenado por contagem decrescente
        - tipo: str                # "O/POS", "A/POS", etc.
          count: int
      por_hemocomponente:
        - tipo: str                # "CHD", "PFC", etc.
          count: int
      total_em_estoque: int
      vencendo:
        urgente:                   # <= threshold_urgente dias
          count: int
          bolsas: array
            - num_bolsa: str
              tipo: str
              gs_rh: str
              volume: int
              data_validade: str
              dias_restantes: int
        atencao:                   # <= threshold_atencao dias
          count: int
          bolsas: array[...]
      ultima_atualizacao: str      # DD/MM/YYYY HH:MM:SS

# === ALERTAS (Feature 14) ===

GET /api/alertas/config:
  description: Retorna configuracao atual de alertas
  response:
    200:
      threshold_urgente: int
      threshold_atencao: int
      email_enabled: bool
      email_to: str | null
      inapp_enabled: bool

PUT /api/alertas/config:
  description: Atualiza configuracao de alertas
  request:
    content-type: application/json
    body:
      threshold_urgente: int
      threshold_atencao: int
      email_enabled: bool
      email_to: str | null
      inapp_enabled: bool
  response:
    200:
      mensagem: str
    400:
      error: str

GET /api/alertas/verificar:
  description: Executa verificacao manual de vencimentos (mesmo que o scheduler faz)
  response:
    200:
      urgente: array[...]
      atencao: array[...]
      email_enviado: bool

# === NAVIGATION ===

GET /historico:
  description: Serve pagina HTML de historico

GET /historico/<id>:
  description: Serve pagina HTML de detalhe de importacao

GET /dashboard:
  description: Serve pagina HTML do dashboard

GET /alertas/config:
  description: Serve pagina HTML de configuracao de alertas
```

### Integration Points

| Ponto | Arquivo | Modificacao |
|-------|---------|-------------|
| Batch orchestration | `src/batch_processor.py` | **create** — processa lista de PDFs, agrega resultados, gerencia status individual |
| Batch routes | `src/app.py` | **inject** — rotas /api/batch/upload, /api/batch/enviar |
| History storage | `src/history_store.py` | **create** — CRUD SQLite, schema init, queries com filtro |
| History routes | `src/app.py` | **inject** — rotas /api/historico, /historico (HTML) |
| History recording | `src/sheets_writer.py` | **modify** — apos escrita bem-sucedida, registrar no historico |
| Dashboard data | `src/dashboard_service.py` | **create** — le planilha, agrega por GS/RH e hemocomponente, filtra vencimentos |
| Dashboard cache | `src/dashboard_service.py` | **create** — cache com TTL, invalidacao apos importacao |
| Dashboard reading | `src/sheets_reader.py` | **extend** — metodo para ler planilha inteira com colunas relevantes para dashboard |
| Dashboard routes | `src/app.py` | **inject** — rotas /api/dashboard, /dashboard (HTML) |
| Alert logic | `src/alert_service.py` | **create** — verificacao de vencimento, classificacao urgente/atencao |
| Alert email | `src/email_sender.py` | **create** — composicao e envio de email HTML via SMTP |
| Alert scheduler | `src/scheduler.py` | **create** — APScheduler job diario para verificacao de alertas |
| Alert config | `src/history_store.py` | **extend** — CRUD para tabela alert_config (reusa conexao SQLite) |
| Alert routes | `src/app.py` | **inject** — rotas /api/alertas/*, /alertas/config (HTML) |
| Batch upload UI | `src/templates/index.html` | **modify** — adaptar drop-zone para multiplos arquivos, lista com remocao |
| Batch processing UI | `src/static/app.js` | **modify** — logica de status individual, progress bar, preview consolidado |
| History UI | `src/templates/history.html` | **create** — lista + filtro + paginacao |
| History detail UI | `src/templates/history_detail.html` | **create** — metadados + tabela de bolsas |
| Dashboard UI | `src/templates/dashboard.html` | **create** — barras horizontais + secao vencimento |
| Dashboard JS | `src/static/dashboard.js` | **create** — fetch dados, renderizar barras, refresh |
| Alert settings UI | `src/templates/alert_settings.html` | **create** — form de configuracao |
| Navigation | `src/templates/*.html` | **modify** — header com links [Upload] [Historico] [Dashboard] |
| Config | `src/config.py` | **modify** — novas variaveis SMTP_*, SQLITE_DB_PATH, SCHEDULER_*, CACHE_TTL |
| Env vars | `.env.example` | **modify** — documentar novas variaveis |
| Dependencies | `requirements.txt` | **modify** — adicionar APScheduler |
| Gitignore | `.gitignore` | **modify** — adicionar data/*.db |

---

## 6. Tasks

### Task 1: Setup de infraestrutura Phase 3
**Keywords:** create data directory, modify requirements, extend config, modify gitignore
**Files:**
- `data/.gitkeep` (create)
- `requirements.txt` (modify)
- `.env.example` (modify)
- `.gitignore` (modify)
- `src/config.py` (modify)

**Description:**
1. Criar diretorio `data/` com `.gitkeep` para o banco SQLite
2. Adicionar `APScheduler>=3.10` ao requirements.txt
3. Adicionar novas variaveis ao .env.example:
   - `SQLITE_DB_PATH=data/historico.db`
   - `SMTP_ENABLED=false`
   - `SMTP_HOST=`
   - `SMTP_PORT=587`
   - `SMTP_USER=`
   - `SMTP_PASSWORD=`
   - `SMTP_FROM=`
   - `ALERT_EMAIL_TO=`
   - `SCHEDULER_ENABLED=false`
   - `CACHE_TTL_SECONDS=300`
4. Adicionar `data/*.db` ao .gitignore
5. Estender config.py para carregar todas as novas variaveis de ambiente com valores padrao

**Validation:**
```bash
pip install -r requirements.txt
python3 -c "from apscheduler.schedulers.background import BackgroundScheduler; print('APScheduler OK')"
python3 -c "from src.config import Config; c = Config(); print(f'DB: {c.SQLITE_DB_PATH}')"
```

---

### Task 2: Implementar armazenamento de historico (SQLite)
**Keywords:** create history_store, create database schema, implement CRUD operations
**Files:**
- `src/history_store.py` (create)
- `tests/test_history_store.py` (create)

**Description:**
Criar modulo de armazenamento SQLite para historico de importacoes e configuracao de alertas.
1. Funcao `init_db(db_path)` — cria tabelas se nao existem (import_records, import_bolsas, alert_config)
2. Funcao `registrar_importacao(filename, comprovante_nums, bolsa_count, status, error_message, bolsas_detail)` — insere registro + detalhes de bolsas em transacao
3. Funcao `listar_importacoes(data_inicio, data_fim, page, per_page)` — retorna lista paginada com contagem total
4. Funcao `obter_importacao(import_id)` — retorna registro + bolsas detalhadas
5. Funcao `obter_alert_config()` — retorna config atual (cria padrao se nao existe)
6. Funcao `salvar_alert_config(config)` — upsert da config de alertas
7. Usar `check_same_thread=False` e WAL mode na conexao
8. Usar context manager para conexoes (abrir, usar, fechar)

**Pseudocode:**
```python
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db(db_path: str):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path: str):
    with get_db(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS import_records (...);
            CREATE TABLE IF NOT EXISTS import_bolsas (...);
            CREATE TABLE IF NOT EXISTS alert_config (...);
            CREATE INDEX IF NOT EXISTS ...;
        """)

def registrar_importacao(db_path, filename, comprovante_nums, bolsa_count,
                         status, error_message, bolsas_detail) -> int:
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO import_records (...) VALUES (...)",
            (datetime.now().isoformat(), filename, comprovante_nums,
             bolsa_count, status, error_message)
        )
        import_id = cursor.lastrowid
        for bolsa in bolsas_detail:
            conn.execute(
                "INSERT INTO import_bolsas (...) VALUES (...)",
                (import_id, bolsa.num_bolsa, bolsa.tipo_hemocomponente,
                 bolsa.gs_rh, bolsa.volume, bolsa.data_validade.isoformat())
            )
        return import_id

def listar_importacoes(db_path, data_inicio=None, data_fim=None,
                       page=1, per_page=20) -> tuple[list, int]:
    with get_db(db_path) as conn:
        # Build WHERE clause with date filters
        # SELECT with LIMIT/OFFSET for pagination
        # Also SELECT COUNT(*) for total
        ...
```

**Validation:**
```bash
python3 -m pytest tests/test_history_store.py -v
```

---

### Task 3: Implementar processamento em lote
**Keywords:** create batch_processor, extend app.py with batch routes, modify frontend for multi-upload
**Files:**
- `src/batch_processor.py` (create)
- `tests/test_batch_processor.py` (create)
- `src/app.py` (modify — inject batch routes)

**Description:**
Criar modulo de processamento em lote e rotas correspondentes.
1. Funcao `processar_lote(files: list[FileStorage]) -> BatchResult`:
   - Para cada arquivo: chamar `extrair_pdf()` + `mapear_comprovantes()` individualmente
   - Capturar excecoes por arquivo (try/except interno)
   - Retornar lista de `BatchFileStatus` com dados ou erro por arquivo
   - Consolidar todas as `LinhaPlanilha` de arquivos bem-sucedidos
2. Rota `POST /api/batch/upload`:
   - Receber multiplos arquivos via `request.files.getlist('files')`
   - Validar: ao menos 1 arquivo, maximo 10, todos PDF, cada um <10MB
   - Chamar `processar_lote()`
   - Retornar JSON com status por arquivo + linhas consolidadas
3. Rota `POST /api/batch/enviar`:
   - Receber linhas consolidadas
   - Reusar logica de envio existente (sheets_writer)
   - Registrar no historico (1 registro por arquivo/comprovante)
   - Retornar resumo

**Pseudocode:**
```python
def processar_lote(files: list) -> dict:
    results = []
    all_linhas = []
    for file in files:
        try:
            temp_path = save_temp(file)
            comprovantes = extrair_pdf(temp_path)
            linhas = mapear_comprovantes(comprovantes)
            results.append(BatchFileStatus(
                filename=file.filename,
                status="done",
                comprovante_count=len(comprovantes),
                bolsa_count=len(linhas),
                linhas=linhas
            ))
            all_linhas.extend(linhas)
        except Exception as e:
            results.append(BatchFileStatus(
                filename=file.filename,
                status="error",
                error_message=str(e)
            ))
        finally:
            cleanup_temp(temp_path)
    return {
        "files": results,
        "all_linhas": all_linhas,
        "summary": {
            "total_files": len(files),
            "success_files": sum(1 for r in results if r.status == "done"),
            "error_files": sum(1 for r in results if r.status == "error"),
            "total_bolsas": len(all_linhas)
        }
    }
```

**Validation:**
```bash
python3 -m pytest tests/test_batch_processor.py -v
# Teste manual com multiplos PDFs (pode usar o mesmo PDF 2x para simular)
curl -X POST http://localhost:5000/api/batch/upload \
  -F "files=@insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf"
```

---

### Task 4: Implementar frontend de processamento em lote
**Keywords:** modify index.html for multi-upload, modify app.js for batch processing UI
**Files:**
- `src/templates/index.html` (modify)
- `src/static/app.js` (modify)
- `src/static/style.css` (modify)

**Description:**
Adaptar o frontend existente para suportar upload em lote.

1. **Batch Upload Screen** (modificar tela de upload existente):
   - Alterar input file para `multiple` attribute
   - Drop-zone aceita multiplos arquivos
   - Mostrar lista de arquivos selecionados com nome, tamanho e botao remover (X)
   - Contador: "N arquivos selecionados"
   - Botao "PROCESSAR TODOS" (desabilitado se 0 arquivos)
   - Manter compatibilidade: upload de 1 arquivo continua funcionando igual

2. **Batch Processing Screen** (novo estado na SPA):
   - Lista de arquivos com status visual: checkmark (done), spinner (processing), circle (queued)
   - Contagem por arquivo: "N comprovantes, M bolsas" quando done
   - Mensagem de erro inline quando error
   - Barra de progresso: N/Total
   - Botao "Cancelar" (cancela arquivos nao processados)

3. **Batch Preview** (adaptar tela de preview existente):
   - Agrupar linhas por arquivo de origem
   - Header visual separando dados de cada PDF
   - Totalizadores: X arquivos, Y comprovantes, Z bolsas
   - Manter botoes "Cancelar" e "Enviar para Planilha"

4. **Batch Success** (adaptar tela de sucesso):
   - Resumo: "X arquivos processados, Y comprovantes lidos, Z bolsas importadas, W erros"
   - Botoes "Abrir planilha" e "Novo lote"

**Validation:**
```bash
# Iniciar servidor e testar manualmente
cd src && python3 app.py
# Abrir http://localhost:5000
# Arrastar multiplos PDFs, verificar lista, processar, revisar preview, enviar
```

---

### Task 5: Implementar telas e rotas de historico
**Keywords:** create history templates, inject history routes, wire history_store to app
**Files:**
- `src/templates/history.html` (create)
- `src/templates/history_detail.html` (create)
- `src/static/history.js` (create)
- `src/app.py` (modify — inject history routes)
- `src/sheets_writer.py` (modify — registrar importacao apos escrita)

**Description:**
1. **Rota GET /historico** — serve history.html
2. **Rota GET /historico/<id>** — serve history_detail.html
3. **Rota GET /api/historico** — retorna JSON paginado com filtro de data
4. **Rota GET /api/historico/<id>** — retorna JSON com detalhes
5. **Modificar sheets_writer** — apos `append_rows` bem-sucedido, chamar `registrar_importacao()` com dados do lote

6. **history.html:**
   - Header com navegacao [Upload] [Historico] [Dashboard]
   - Filtro de periodo: campos data inicio/fim + botao "Filtrar"
   - Tabela: DATA | ARQUIVO | COMPROVANTES | BOLSAS | STATUS
   - Status com icone visual (checkmark verde = sucesso, warning amarelo = parcial, X vermelho = erro)
   - Paginacao: "Mostrando X de Y importacoes" + botoes pagina anterior/proxima
   - Click em linha abre detalhe

7. **history_detail.html:**
   - Header com [Voltar] para historico
   - Card com metadados: data/hora, arquivo, comprovantes, bolsas, status
   - Se erro: mostrar mensagem de erro
   - Tabela de bolsas: NUM BOLSA | TIPO | GS/RH | VOLUME | VALIDADE

8. **history.js:**
   - Fetch /api/historico com parametros de filtro
   - Renderizar tabela dinamicamente
   - Handler de paginacao
   - Handler de filtro de data

**Validation:**
```bash
# Apos importar ao menos 1 PDF:
curl http://localhost:5000/api/historico
# Deve retornar JSON com ao menos 1 importacao
curl http://localhost:5000/api/historico/1
# Deve retornar detalhes com bolsas
```

---

### Task 6: Implementar dashboard de estoque
**Keywords:** create dashboard_service, extend sheets_reader, create dashboard template, wire routes
**Files:**
- `src/dashboard_service.py` (create)
- `src/sheets_reader.py` (modify — extend with full read method)
- `src/templates/dashboard.html` (create)
- `src/static/dashboard.js` (create)
- `src/app.py` (modify — inject dashboard routes)
- `tests/test_dashboard_service.py` (create)

**Description:**
1. **Estender sheets_reader.py:**
   - Metodo `ler_planilha_completa()` — retorna todas as linhas da aba MAPA DE TRANSFUSAO (rows 11+)
   - Retornar como lista de dicts com colunas nomeadas
   - 1 unica API call: `worksheet.get_all_values()`

2. **Criar dashboard_service.py:**
   - Classe `DashboardService` com cache interno
   - Metodo `obter_estoque(force_refresh=False)` → `EstoqueResumo`
   - Logica de cache: se dados tem menos de CACHE_TTL_SECONDS, retornar cache
   - Metodo `invalidar_cache()` — chamado apos importacao
   - Logica de filtragem:
     - "Em estoque" = coluna E (DATA TRANSFUSAO/DESTINO) vazia AND coluna F (DESTINO) vazia
     - Parsing de coluna D (DATA VALIDADE) para calcular dias restantes
     - Agrupamento por coluna I (GS/RH): contar bolsas por tipo
     - Agrupamento por coluna H (TIPO HEMOCOMPONENTE): contar bolsas por tipo
     - Classificar vencimentos: urgente (<=threshold_urgente), atencao (<=threshold_atencao), proximo (<=30d)
   - Usar thresholds da alert_config do SQLite

3. **Rota GET /dashboard** — serve dashboard.html
4. **Rota GET /api/dashboard** — retorna JSON com dados agregados

5. **dashboard.html:**
   - Header com navegacao [Upload] [Historico] [Dashboard]
   - Titulo "Estoque Atual" + botao "Atualizar" (icone refresh)
   - Secao "POR TIPO SANGUINEO":
     - 8 barras horizontais (O/POS, A/POS, O/NEG, B/POS, A/NEG, AB/POS, B/NEG, AB/NEG)
     - Barra = div com background-color e width proporcional ao max
     - Numero ao lado de cada barra
     - "Total: N" abaixo
   - Secao "POR HEMOCOMPONENTE":
     - Barras horizontais por tipo (CHD, PFC, CRIO, etc.)
   - Banner inferior: "N bolsas vencem em 7 dias" (vermelho se >0)
   - Click no banner expande secao de vencimentos

6. **Secao de Vencimento (integrada no dashboard):**
   - Urgente (vermelho): lista de bolsas vencendo em <=7 dias
   - Atencao (amarelo): lista de bolsas vencendo em <=14 dias
   - Cada item: num_bolsa, tipo, GS/RH, volume, data_validade, dias_restantes
   - Listas expandiveis/collapsiveis
   - Link [Config] para tela de configuracao de alertas

7. **dashboard.js:**
   - Fetch /api/dashboard
   - Renderizar barras com largura proporcional (max value = 100%)
   - Renderizar lista de vencimentos
   - Handler botao "Atualizar" (fetch com force_refresh=true)
   - Cores: vermelho (#e74c3c) urgente, amarelo (#f39c12) atencao

**Validation:**
```bash
python3 -m pytest tests/test_dashboard_service.py -v
# Teste manual:
curl http://localhost:5000/api/dashboard
# Deve retornar JSON com por_gs_rh, por_hemocomponente, vencendo
```

---

### Task 7: Implementar servico de alertas de vencimento
**Keywords:** create alert_service, create email_sender, create scheduler, create alert_settings template
**Files:**
- `src/alert_service.py` (create)
- `src/email_sender.py` (create)
- `src/scheduler.py` (create)
- `src/templates/alert_settings.html` (create)
- `src/static/alert_settings.js` (create)
- `src/app.py` (modify — inject alert routes, initialize scheduler)
- `tests/test_alert_service.py` (create)

**Description:**
1. **Criar alert_service.py:**
   - Funcao `verificar_vencimentos(db_path, sheets_reader, dashboard_service)`:
     - Obter dados de estoque via dashboard_service (reusar cache)
     - Obter config de alertas via history_store
     - Classificar bolsas por threshold
     - Retornar dict com listas `urgente` e `atencao`
   - Funcao `executar_alerta(db_path, sheets_reader, dashboard_service, email_sender)`:
     - Chamar verificar_vencimentos()
     - Se inapp_enabled: salvar notificacoes pendentes (tabela extra ou flag)
     - Se email_enabled e ha bolsas em alerta: chamar email_sender
     - Retornar resumo

2. **Criar email_sender.py:**
   - Funcao `enviar_alerta_email(config, bolsas_urgente, bolsas_atencao)`:
     - Compor email HTML com tabela de bolsas
     - Template: "Alerta de Vencimento - Banco de Sangue HMOB"
     - Secao vermelha: bolsas urgentes
     - Secao amarela: bolsas atencao
     - Enviar via smtplib (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
     - Usar STARTTLS se porta 587
   - Funcao `testar_smtp(config) -> bool`: envia email de teste

3. **Criar scheduler.py:**
   - Funcao `iniciar_scheduler(app)`:
     - Usar APScheduler BackgroundScheduler
     - Job diario (padrao 08:00 Brasilia): `executar_alerta()`
     - Configuracao de horario via env (SCHEDULER_ALERT_HOUR, SCHEDULER_ALERT_MINUTE)
     - Protecao contra multiplas instancias (flag global)
     - Apenas iniciar se SCHEDULER_ENABLED=true

4. **Rotas de alertas:**
   - `GET /alertas/config` — serve alert_settings.html
   - `GET /api/alertas/config` — retorna config JSON
   - `PUT /api/alertas/config` — salva config
   - `GET /api/alertas/verificar` — executa verificacao manual
   - `POST /api/alertas/testar-email` — envia email de teste

5. **alert_settings.html:**
   - Header com [Dashboard] (voltar)
   - Secao "Prazos de alerta":
     - Campo numerico "Urgente" (padrao 7) com cor vermelha
     - Campo numerico "Atencao" (padrao 14) com cor amarela
   - Secao "Notificacoes":
     - Checkbox "Alerta no app (ao abrir)"
     - Checkbox "Email diario" + campo email
     - Botao "Testar email" (envia email de teste para o endereco configurado)
   - Botao "SALVAR"
   - Feedback visual (salvo com sucesso / erro)

6. **alert_settings.js:**
   - Fetch /api/alertas/config ao carregar
   - Popular form com valores atuais
   - Handler salvar: PUT /api/alertas/config
   - Handler testar email: POST /api/alertas/testar-email

7. **Integrar scheduler no app.py:**
   - No `if __name__ == '__main__'` ou em `create_app()`:
     - Chamar `init_db()` para garantir tabelas existem
     - Se SCHEDULER_ENABLED: chamar `iniciar_scheduler(app)`

**Validation:**
```bash
python3 -m pytest tests/test_alert_service.py -v
# Teste manual de verificacao:
curl http://localhost:5000/api/alertas/verificar
# Deve retornar bolsas em alerta (se houver)
# Teste de configuracao:
curl -X PUT http://localhost:5000/api/alertas/config \
  -H "Content-Type: application/json" \
  -d '{"threshold_urgente": 7, "threshold_atencao": 14, "email_enabled": false, "inapp_enabled": true}'
```

---

### Task 8: Implementar navegacao global e notificacao in-app
**Keywords:** modify all templates with navigation header, wire in-app alerts to dashboard
**Files:**
- `src/templates/index.html` (modify — header navigation)
- `src/templates/history.html` (modify — header navigation)
- `src/templates/dashboard.html` (modify — alert banner)
- `src/static/style.css` (modify — navigation styles, alert banner styles)

**Description:**
1. **Navegacao global** — todas as paginas devem ter header consistente:
   ```
   [Upload] [Historico] [Dashboard]
   ```
   - Link ativo destacado (bold/underline)
   - Mesmo estilo visual em todas as paginas
   - Links: `/` (Upload), `/historico` (Historico), `/dashboard` (Dashboard)

2. **Notificacao in-app:**
   - No dashboard: se ha bolsas urgentes, mostrar banner vermelho no topo
   - No header de todas as paginas: indicador visual (badge com numero) se ha alertas pendentes
   - Endpoint `/api/alertas/pendentes` — retorna contagem de bolsas urgentes/atencao
   - Badge desaparece se nao ha alertas

3. **Estilos de navegacao:**
   - Header fixo no topo
   - Logo/titulo "Hemominas > Sheets" a esquerda
   - Links de navegacao a direita
   - Badge de alerta: circulo vermelho com numero

**Validation:**
```bash
# Verificar visualmente:
# 1. Abrir http://localhost:5000 — header com 3 links
# 2. Navegar para /historico — mesmo header, link Historico ativo
# 3. Navegar para /dashboard — mesmo header, link Dashboard ativo
# 4. Se houver alertas, badge visivel no header
```

---

### Task 9: Testes de integracao Phase 3
**Keywords:** validate batch processing, validate history recording, validate dashboard, validate alerts
**Files:**
- Nenhum novo — usa os existentes

**Description:**
Executar testes de integracao cobrindo os fluxos completos de Phase 3.

1. **Fluxo Batch:**
   - Upload de 2 copias do PDF real via /api/batch/upload
   - Verificar que 2 arquivos reportam sucesso, 12 bolsas total
   - Enviar via /api/batch/enviar
   - Verificar escrita na planilha de teste

2. **Fluxo Historico:**
   - Apos batch enviar, verificar que /api/historico retorna registros
   - Verificar filtro por data
   - Verificar detalhe com bolsas corretas

3. **Fluxo Dashboard:**
   - Chamar /api/dashboard e verificar que retorna dados agregados
   - Verificar que totais batem com dados da planilha
   - Verificar que cache funciona (2a chamada mais rapida)
   - Verificar que force_refresh recarrega

4. **Fluxo Alertas:**
   - Configurar thresholds via /api/alertas/config
   - Chamar /api/alertas/verificar
   - Verificar que bolsas proximas do vencimento sao listadas

**Validation:**
```bash
# Teste batch
curl -X POST http://localhost:5000/api/batch/upload \
  -F "files=@insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf" \
  -F "files=@insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf"
# Esperar: 2 arquivos sucesso, 12 bolsas total

# Teste historico
curl http://localhost:5000/api/historico
# Esperar: ao menos 1 importacao listada

# Teste dashboard
curl http://localhost:5000/api/dashboard
# Esperar: JSON com por_gs_rh, por_hemocomponente, vencendo

# Teste alertas
curl http://localhost:5000/api/alertas/verificar
# Esperar: listas urgente/atencao
```

---

## 7. Validation Gating

### Level 1: Syntax & Imports
```bash
python3 -c "
import src.batch_processor
import src.history_store
import src.dashboard_service
import src.alert_service
import src.email_sender
import src.scheduler
print('All Phase 3 imports OK')
"
```
**Criterio:** Zero errors

### Level 2: Unit Tests
```bash
python3 -m pytest tests/test_batch_processor.py tests/test_history_store.py tests/test_dashboard_service.py tests/test_alert_service.py -v --tb=short
```
**Criterio:** All tests pass

### Level 3: Integration Test (Batch + History)
```bash
python3 -c "
from src.history_store import init_db, registrar_importacao, listar_importacoes, obter_importacao
import tempfile, os

# Setup temp DB
db_path = tempfile.mktemp(suffix='.db')
init_db(db_path)

# Simular importacao
from dataclasses import dataclass
from datetime import date

@dataclass
class BolsaMock:
    num_bolsa: str = '25051087'
    tipo_hemocomponente: str = 'CHD'
    gs_rh: str = 'O/POS'
    volume: int = 292
    data_validade: date = date(2026, 3, 8)

import_id = registrar_importacao(
    db_path, 'test.pdf', '1292305', 1, 'sucesso', None, [BolsaMock()]
)
assert import_id > 0

# Verificar listagem
imports, total = listar_importacoes(db_path)
assert total == 1
assert imports[0]['filename'] == 'test.pdf'

# Verificar detalhe
detail = obter_importacao(db_path, import_id)
assert detail is not None
assert len(detail['bolsas']) == 1

os.unlink(db_path)
print('History store integration test PASSED')
"
```
**Criterio:** Import record created, listed, and detailed correctly

### Level 4: Integration Test (Dashboard Aggregation)
```bash
python3 -c "
from src.dashboard_service import DashboardService
from datetime import date, datetime

# Mock data simulating spreadsheet rows
mock_rows = [
    # Header row (index 0, row 10 in sheet)
    ['DIAS ANTES VENCIMENTO', 'STATUS', 'DATA ENTRADA', 'DATA VALIDADE', 'DATA TRANSFUSAO', 'DESTINO', 'PACIENTE', 'TIPO HEMOCOMPONENTE', 'GS/RH', 'VOLUME', 'RESPONSAVEL', 'SETOR', 'NUM BOLSA'],
    # Bolsa em estoque (E e F vazias)
    ['5', 'VENCE EM 5 DIAS', '14/12/2025', '05/03/2026', '', '', '', 'CHD - Concentrado de Hemacias', 'O/POS', '292', 'NILMARA', '', '25051087'],
    # Bolsa ja transfundida (F preenchida)
    ['-10', 'VENCIDO', '14/12/2025', '18/02/2026', '15/02/2026', 'CENTRO CIRURGICO', 'JOAO', 'CHD', 'A/POS', '273', 'NILMARA', 'CC', '25009258'],
    # Bolsa em estoque
    ['20', 'VENCE EM 20 DIAS', '14/12/2025', '20/03/2026', '', '', '', 'PFC - Plasma Fresco', 'O/NEG', '268', 'ANA', '', '25019832'],
]

# Test aggregation logic
service = DashboardService.__new__(DashboardService)
resumo = service._agregar_dados(mock_rows[1:], mock_rows[0])
assert resumo.total_em_estoque == 2  # Apenas bolsas sem destino
assert resumo.por_gs_rh.get('O/POS', 0) == 1
assert resumo.por_gs_rh.get('O/NEG', 0) == 1
assert resumo.por_gs_rh.get('A/POS', 0) == 0  # Transfundida, nao conta
print(f'Dashboard aggregation test PASSED: {resumo.total_em_estoque} bolsas em estoque')
"
```
**Criterio:** Aggregation correctly filters and groups bolsas

### Level 5: E2E (Servidor + Fluxo Completo)
```bash
# 1. Iniciar servidor
cd src && python3 app.py &

# 2. Batch upload
curl -s -X POST http://localhost:5000/api/batch/upload \
  -F "files=@../insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf" | python3 -m json.tool

# 3. Verificar historico
curl -s http://localhost:5000/api/historico | python3 -m json.tool

# 4. Verificar dashboard
curl -s http://localhost:5000/api/dashboard | python3 -m json.tool

# 5. Verificar alertas
curl -s http://localhost:5000/api/alertas/verificar | python3 -m json.tool

# 6. Verificar paginas HTML servidas
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/historico
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/dashboard
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/alertas/config

# 7. Kill servidor
kill %1
```
**Criterio:** All endpoints return 200, JSON responses contain expected fields

---

## 8. Final Checklist

### Quality Gates
- [ ] All Level 1 validations pass (imports dos novos modulos)
- [ ] All Level 2 validations pass (unit tests Phase 3)
- [ ] All Level 3 validations pass (history store integration)
- [ ] All Level 4 validations pass (dashboard aggregation)
- [ ] All Level 5 validations pass (E2E completo)
- [ ] Batch upload processa multiplos PDFs independentemente
- [ ] Erro em 1 PDF do lote nao impede processamento dos demais
- [ ] Preview consolida dados de todos os PDFs do lote
- [ ] Resumo do lote mostra contadores corretos (arquivos, comprovantes, bolsas, erros)
- [ ] Historico registra cada importacao com metadados completos
- [ ] Filtro por periodo funciona corretamente no historico
- [ ] Detalhe de importacao mostra bolsas individuais
- [ ] Historico persiste apos reiniciar servidor (SQLite)
- [ ] Dashboard mostra contagem por GS/RH com barras horizontais
- [ ] Dashboard mostra contagem por hemocomponente
- [ ] Dashboard filtra apenas bolsas "em estoque" (colunas E e F vazias)
- [ ] Botao "Atualizar" recarrega dados do Sheets
- [ ] Cache do dashboard funciona (2a chamada rapida) e invalida apos importacao
- [ ] Alertas de vencimento listam bolsas corretamente por threshold
- [ ] Configuracao de alertas persiste no SQLite
- [ ] Email de alerta e enviado quando SMTP configurado
- [ ] Se SMTP nao configurado, alertas in-app funcionam sem erro
- [ ] Navegacao global presente em todas as paginas
- [ ] Nenhuma funcionalidade de Phase 1/2 quebrada

### Patterns to Avoid
- [ ] Nao fazer multiplas chamadas ao Sheets API quando 1 e suficiente (respeitar quota 300 req/min)
- [ ] Nao armazenar dados senssiveis (credenciais SMTP) no SQLite — manter em .env
- [ ] Nao bloquear a thread principal com processamento longo de lote — processar sequencialmente mas com feedback ao frontend
- [ ] Nao confiar em ordem de colunas da planilha — usar indice de header (row 10) para mapear
- [ ] Nao criar scheduler multiplo quando Flask recarrega em modo debug — usar flag de protecao
- [ ] Nao enviar emails em ambiente de desenvolvimento — SMTP_ENABLED=false por padrao
- [ ] Nao permitir threshold_urgente >= threshold_atencao na config de alertas
- [ ] Nao cachear dados do dashboard indefinidamente — TTL configuravel com fallback para 5min
- [ ] Nao ignorar timezone — usar America/Sao_Paulo para calculos de vencimento

---

## 9. Confidence Assessment

**Score:** 7/10

**Factors:**
- [+2] Funcionalidades de Phase 3 sao independentes entre si (batch, historico, dashboard, alertas) — podem ser implementadas em paralelo se necessario
- [+1] Feature specs e user journeys detalhados disponveis para todas as 4 features
- [+1] Wireframes de tela definidos nos user journeys (layouts claros)
- [+1] Tech stack simples e consistente com Phase 1/2 (Flask, vanilla JS, gspread)
- [+1] SQLite e abordagem madura e testavel para historico
- [+1] Modelos de dados e schema SQL definidos no PRP
- [-1] Dashboard depende de leitura massiva da planilha (12700+ rows) — performance nao testada com dados reais de producao
- [-1] Configuracao de email SMTP em ambiente hospitalar nao validada — pode exigir configuracao especifica da rede do HMOB
- [-1] Scheduler (APScheduler) dentro de Flask pode ter comportamento inesperado com auto-reload e gunicorn workers — requer testes em ambiente proximo ao de producao

**Se score < 7, missing context:**
N/A — score e 7.

**Para chegar a 10:**
- Testar leitura completa da planilha real (12700+ rows) e medir tempo/memoria
- Validar configuracao SMTP com equipe de TI do HMOB
- Testar APScheduler em cenario de producao (gunicorn com workers)
- Obter feedback da Ana sobre layout do dashboard e thresholds de alerta adequados
- Testar batch upload com 10+ PDFs reais simultaneamente para validar performance

---

*PRP generated by dev-kit:10-generate-prp*
*IMPORTANTE: Execute em nova instancia do Claude Code (use /clear antes de executar)*
*PRE-REQUISITO: Phases 1 e 2 devem estar completas antes de iniciar Phase 3*
