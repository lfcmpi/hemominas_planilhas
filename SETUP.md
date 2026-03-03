# Setup e Teste — Banco de Sangue PDF-to-Sheets

## Requisitos

- Python 3.10+
- Tesseract OCR: `brew install tesseract tesseract-lang`

## Instalacao

```bash
cd /Users/luismartins/ia/claude/novos_projetos/ana_planilha

# Criar e ativar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## 1. Testar a extracao (sem Google Sheets)

Funciona imediatamente, sem configurar nada:

```bash
source venv/bin/activate
python3 -m src.app
```

Abrir http://localhost:5000 no navegador:

1. Arrastar o PDF ou clicar "Selecionar arquivo"
2. Clicar "Processar PDF"
3. Conferir os dados extraidos na tabela de resultados

> O botao "Enviar para Planilha" vai dar erro ate configurar o Google Sheets (passo 2).

---

## 2. Configurar Google Sheets

### Passo A: Criar Service Account no Google Cloud

1. Acessar https://console.cloud.google.com
2. Criar um projeto (ou usar existente)
3. Ativar a **Google Sheets API**:
   - Menu lateral → APIs & Services → Library
   - Buscar "Google Sheets API" → Enable
4. Criar Service Account:
   - Menu lateral → IAM & Admin → Service Accounts
   - Create Service Account
   - Nome: "banco-sangue-bot" (ou qualquer nome)
   - Clicar Create and Continue → Done
5. Gerar chave JSON:
   - Clicar na service account criada
   - Aba Keys → Add Key → Create new key → JSON
   - O arquivo JSON sera baixado automaticamente

### Passo B: Colocar credenciais no projeto

```bash
# Copiar o JSON baixado para a pasta credentials/
cp ~/Downloads/seu-arquivo-xxxx.json credentials/service-account.json

# Criar .env a partir do template
cp .env.example .env
```

Editar o arquivo `.env`:

```
GOOGLE_SHEETS_ID=cole_o_id_da_planilha_aqui
GOOGLE_CREDENTIALS_PATH=credentials/service-account.json
```

**Como encontrar o ID da planilha:**

A URL da planilha tem este formato:
```
https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/edit
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                       ESTE E O ID
```

Copiar a parte entre `/d/` e `/edit`.

### Passo C: Compartilhar a planilha com o bot

1. Abrir o arquivo `credentials/service-account.json`
2. Copiar o valor do campo `"client_email"` (algo como `banco-sangue-bot@projeto.iam.gserviceaccount.com`)
3. Abrir a planilha Google Sheets no navegador
4. Clicar em **Compartilhar** (botao verde no canto superior direito)
5. Colar o email da service account
6. Selecionar permissao **Editor**
7. Clicar Enviar

---

## 3. Testar end-to-end (com planilha de TESTE)

**IMPORTANTE:** Usar uma copia da planilha para nao mexer na original.

1. Abrir a planilha "BANCO DE SANGUE 2026 AT" no Google Sheets
2. Menu Arquivo → Fazer uma copia
3. Copiar o ID da planilha de **copia** (da URL)
4. Colar no `.env` como `GOOGLE_SHEETS_ID`
5. Compartilhar a copia com o email da service account (Passo C acima)

Depois rodar:

```bash
source venv/bin/activate
python3 -m src.app
```

Abrir http://localhost:5000:

1. Fazer upload do PDF (`insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf`)
2. Conferir os 2 comprovantes e 6 bolsas na tabela
3. Clicar "Enviar para Planilha"
4. Abrir a planilha de teste e verificar que os dados apareceram nas colunas corretas

### Dados esperados apos envio

| Col C (Entrada) | Col D (Validade) | Col H (Tipo) | Col I (GS/RH) | Col J (Vol) | Col K (Responsavel) | Col M (Nº Bolsa) |
|---|---|---|---|---|---|---|
| 14/12/2025 | 08/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | O/POS | 292 | NILMARA TANIA VELOSO MATOS | 25051087 |
| 14/12/2025 | 08/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | A/POS | 273 | NILMARA TANIA VELOSO MATOS | 25009258 |
| 14/12/2025 | 22/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | A/POS | 300 | NILMARA TANIA VELOSO MATOS | 25053572 |
| 14/12/2025 | 20/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | O/NEG | 299 | NILMARA TANIA VELOSO MATOS | 25012667 |
| 14/12/2025 | 22/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | O/NEG | 287 | NILMARA TANIA VELOSO MATOS | 25014403 |
| 14/12/2025 | 23/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | O/NEG | 276 | ANA OLIVEIRA | 25014485 |

As colunas A e B terao formulas automaticas (dias ate vencimento e status).
As colunas E, F, G, L, N-S ficam em branco (preenchimento manual).

---

## Rodar testes automatizados

```bash
source venv/bin/activate
python3 -m pytest tests/ -v
```

Resultado esperado: 55 tests passed.

---

## Estrutura do projeto

```
ana_planilha/
├── .env                    ← Suas configuracoes (nao versionado)
├── .env.example            ← Template
├── requirements.txt        ← Dependencias Python
├── SETUP.md                ← Este arquivo
├── credentials/
│   └── service-account.json  ← Chave Google (nao versionado)
├── src/
│   ├── app.py              ← Servidor Flask (rotas API)
│   ├── config.py           ← Configuracoes
│   ├── pdf_extractor.py    ← Extracao OCR do PDF
│   ├── field_mapper.py     ← Mapeamento de campos
│   ├── sheets_writer.py    ← Escrita na Google Sheets
│   ├── templates/
│   │   └── index.html      ← Interface web
│   └── static/
│       ├── style.css
│       └── app.js
├── tests/                  ← Testes automatizados
└── insumos/                ← PDFs e planilhas de referencia
```
