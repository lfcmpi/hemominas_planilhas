# PRP: PDF-to-Sheets — Banco de Sangue (Phase 1 MVP)

**Gerado em:** 2026-02-28
**Confidence Score:** 8/10
**Origem:** docs/* (product-roadmap, 14 feature specs, 5 user journeys, insumos reais)

---

## 1. Core (OBRIGATORIO)

### Goal
Construir uma aplicacao web que extrai dados de PDFs de "Comprovante de Expedicao" da Hemominas e insere automaticamente na planilha Google Sheets "MAPA DE TRANSFUSAO" do HMOB, eliminando a digitacao manual.

### Why
Os profissionais do banco de sangue do HMOB (Hospital Metropolitano Odilon Behrens) digitam manualmente os dados de cada bolsa de sangue recebida — processo lento, repetitivo e propenso a erros. Com ~6 bolsas por comprovante e multiplos comprovantes por dia, a automacao economiza tempo e reduz erros de registro.

### What
**Phase 1 MVP — Pipeline completo PDF → Google Sheets:**
1. Upload de PDF com drag-and-drop
2. Extracao automatica de tabela de hemocomponentes (pdfplumber)
3. Suporte a multiplas paginas/comprovantes no mesmo PDF
4. Mapeamento e conversao de campos (GS/RH, hemocomponentes)
5. Tela de resultados com dados extraidos
6. Escrita direta na planilha Google Sheets via API

### Success Criteria
- [ ] Upload de PDF funciona com drag-and-drop e botao de selecao
- [ ] Extrai corretamente TODOS os campos da tabela do PDF real (testado com `insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf`)
- [ ] Detecta 2 comprovantes (Nº 1292305 com 5 bolsas + Nº 1292307 com 1 bolsa) do PDF de teste
- [ ] Converte ABO+Rh para GS/RH (ex: "O"+"P" → "O/POS")
- [ ] Mapeia componente do PDF para nome padronizado da aba BASE
- [ ] Escreve dados nas colunas corretas (C, D, H, I, J, K, M) da aba "MAPA DE TRANSFUSAO"
- [ ] Insere formulas nas colunas A e B (para compatibilidade com planilha existente)
- [ ] Nenhum dado existente na planilha e sobrescrito (append only)
- [ ] Tela de resultados mostra dados antes do envio

---

## 2. Context

### Codebase Analysis
```
GREENFIELD — Nao existe codigo. Projeto novo.
- Settings .claude/settings.local.json permite: Bash(python3:*)
- Insumos disponiveis:
  - PDF real: insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf (2 comprovantes, 6 bolsas)
  - Excel real: insumos/BANCO DE SANGUE 2026 AT.xlsx (planilha alvo com 12717+ rows)
  - Excel 2024: insumos/USAR ESSE BANCO DE SANGUE 2024 AT.xlsx (referencia historica)
```

### Estrutura Real da Planilha Google Sheets

**Aba: MAPA DE TRANSFUSAO**
- Header na row 10: A=DIAS ANTES DO VENCIMENTO, B=STATUS, C=DATA ENTRADA, D=DATA VALIDADE, E=DATA TRANSFUSAO/DESTINO, F=DESTINO, G=NOME COMPLETO DO PACIENTE, H=TIPO DE HEMOCOMPONENTE, I=GS/RH, J=VOLUME (ML), K=RESPONSAVEL RECEPCAO, L=SETOR DA TRANSFUSAO, M=Nº DA BOLSA, N-S=campos manuais
- Dados comecam na row 11
- Formulas existentes:
  - A: `=IF(D11="","",D11-TODAY())`
  - B: `=IF(A11="","",IF(A11<0,"VENCIDO",IF(A11=0,"VENCE HOJE",CONCATENATE("VENCE EM ",A11," DIAS"))))`

**Aba: BASE** (listas de referencia)
- Rows 1-13: DESTINO (12 valores)
- Rows 15-24: GS/RH (8 tipos + OUTROS)
- Rows 29-44: REACAO TRANSFUSIONAL (15 tipos)
- Rows 48-70: TIPO DE HEMOCOMPONENTE (22 tipos, col A=nome completo, col B=abreviaturas)
- Rows 72-103: SETOR DA TRANSFUSAO (30+ setores)
- Rows 107-136: RESPONSAVEL RECEPCAO (28 nomes)

### Estrutura Real do PDF (Comprovante de Expedicao - Hemominas)

**Pagina 1 — Comprovante Nº 1292305:**
```
Cabecalho:
  Emissao: 14/12/2025 09:23:13
  Instituicao: HMOB - HOSPITAL METROPOLITANO ODILON BHERENS HOB
  Responsavel: PATREICIA
  Nº Comprovante: 1292305

Tabela de produtos (5 bolsas):
  | Inst.Coleta | Nº Doacao | Componente                                        | Cod.ISBT128 | Seq | Vol | ABO | Rh | Validade   |
  | B3013       | 25051087  | CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado  | E6514V00    | 1   | 292 | O   | P  | 08/01/2026 |
  | B3208       | 25009258  | CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado  | E6514V00    | 1   | 273 | A   | P  | 08/01/2026 |
  | B3013       | 25053572  | CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado  | E6514V00    | 1   | 300 | A   | P  | 22/01/2026 |
  | B3209       | 25012667  | CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado  | E6514V00    | 1   | 299 | O   | N  | 20/01/2026 |
  | B3483       | 25014403  | CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado  | E6514V00    | 1   | 287 | O   | N  | 22/01/2026 |

  Total de bolsa(s) expedida(s): 5

Rodape:
  Expedido por: NILMARA TANIA VELOSO MATOS  em: 14/12/2025 as 09:22
  Recebido por: (manuscrito)                em: 14/12/2025 as 10:00
```

**Pagina 2 — Comprovante Nº 1292307:**
```
  | B3483       | 25014485  | CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado  | E6514V00    | 1   | 276 | O   | N  | 23/01/2026 |

  Total de bolsa(s) expedida(s): 1
  Expedido por: ANA OLIVEIRA  em: 14/12/2025 as 09:23
```

### Mapeamento PDF → Planilha (Colunas preenchidas automaticamente)

| Coluna Planilha | Campo | Origem no PDF | Transformacao |
|-----------------|-------|---------------|---------------|
| A | DIAS ANTES DO VENCIMENTO | D (calculado) | Formula: `=IF(D{row}="","",D{row}-TODAY())` |
| B | STATUS | A (calculado) | Formula: `=IF(A{row}="","",IF(A{row}<0,"VENCIDO",IF(A{row}=0,"VENCE HOJE",CONCATENATE("VENCE EM ",A{row}," DIAS"))))` |
| C | DATA ENTRADA | "em: DD/MM/YYYY" do rodape (Expedido por) | Parse DD/MM/YYYY |
| D | DATA VALIDADE | Coluna "Validade" da tabela | Parse DD/MM/YYYY |
| H | TIPO DE HEMOCOMPONENTE | Coluna "Componente" da tabela | Mapeamento para nome da aba BASE |
| I | GS/RH | Colunas "ABO" + "Rh" da tabela | Concatenar: ABO + "/" + (P→POS, N→NEG) |
| J | VOLUME (ML) | Coluna "Vol." da tabela | Inteiro direto |
| K | RESPONSAVEL RECEPCAO | "Expedido por:" do rodape | Texto direto (normalizar) |
| M | Nº DA BOLSA | Coluna "Nº Doacao" da tabela | Direto (ver GOTCHA #1) |

### Mapeamento GS/RH (8 combinacoes)

| PDF ABO | PDF Rh | Planilha GS/RH |
|---------|--------|----------------|
| O | P | O/POS |
| O | N | O/NEG |
| A | P | A/POS |
| A | N | A/NEG |
| B | P | B/POS |
| B | N | B/NEG |
| AB | P | AB/POS |
| AB | N | AB/NEG |

### Mapeamento de Hemocomponentes (PDF → BASE)

O PDF usa nomes descritivos. A aba BASE usa siglas padronizadas. Mapeamento necessario:

| Componente no PDF | Nome na aba BASE (col A, rows 49-70) |
|-------------------|--------------------------------------|
| CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado | CHD - Concentrado de Hemacias Desleucocitado |
| CONCENTRADO HEMACIAS Comum | CHM - Concentrado de Hemacias Comum |
| CONCENTRADO HEMACIAS Camada Leucoplaquetaria | CHCR - Concentrado de Hemacias Camada Leucoplaquetaria Removida |
| PLASMA FRESCO CONGELADO | PFC - Plasma Fresco Congelado |
| CRIOPRECIPITADO | CRIO - Crioprecipitado |
| PLAQUETA RANDOMICA | CPQ - Plaqueta Randomica |
| CONCENTRADO HEMACIAS Fenotipado | CHF - Concentrado de Hemacias Fenotipado |
| CONCENTRADO HEMACIAS Fenotipado Desleucocitado | CHFD - Concentrado de Hemacias Fenotipado e Desleucocitado |

> **NOTA:** O mapeamento acima cobre os tipos mais comuns. A tabela completa deve ser construida a partir das 22 entradas da aba BASE (rows 49-70). Usar fuzzy matching para lidar com variacoes de grafia.

---

## 3. Tree Structure

### Before (Current)
```
ana_planilha/
├── .claude/
│   └── settings.local.json
├── docs/
│   ├── product-roadmap-pdf-to-sheets-banco-sangue.md
│   ├── features/           (14 feature specs)
│   └── journey/            (5 user journeys)
├── insumos/
│   ├── BANCO DE SANGUE 2026 AT.xlsx
│   ├── RECEBIMENTO DE BOLSAS -15_12_2025.pdf
│   └── USAR ESSE BANCO DE SANGUE 2024 AT.xlsx
└── PRPs/
    └── prps/
```

### After (Desired)
```
ana_planilha/
├── .claude/
│   └── settings.local.json
├── .env.example                          # Template de variaveis de ambiente
├── .gitignore
├── README.md
├── requirements.txt                      # Dependencias Python
├── docs/                                 # (inalterado)
├── insumos/                              # (inalterado)
├── PRPs/                                 # (inalterado)
├── credentials/                          # Google service account (gitignored)
│   └── .gitkeep
├── src/
│   ├── app.py                            # Flask app principal + rotas
│   ├── config.py                         # Configuracoes (spreadsheet ID, etc.)
│   ├── pdf_extractor.py                  # Extracao de dados do PDF (pdfplumber)
│   ├── field_mapper.py                   # Mapeamento/conversao de campos
│   ├── sheets_writer.py                  # Integracao Google Sheets API
│   ├── templates/
│   │   └── index.html                    # SPA com upload + resultados + sucesso
│   └── static/
│       ├── style.css                     # Estilos (minimo, funcional)
│       └── app.js                        # Logica frontend (upload, preview, envio)
└── tests/
    ├── test_pdf_extractor.py             # Testes com PDF real
    ├── test_field_mapper.py              # Testes de mapeamento/conversao
    └── test_sheets_writer.py             # Testes de escrita (mock)
```

---

## 4. Known Gotchas

| # | Gotcha | Solucao |
|---|--------|---------|
| 1 | **Formato Nº DA BOLSA divergente:** O PDF mostra Nº Doacao curto (ex: "25051087") mas a planilha existente usa codigos longos com prefixo (ex: "B32022500044633"). Sao formatos diferentes — Nº Doacao vs codigo ISBT/SBS. | Investigar com a Ana qual formato usar. Opcoes: (a) usar Nº Doacao direto do PDF, (b) construir codigo completo combinando Inst.Coleta + Nº Doacao + sufixo. **Recomendacao:** usar Nº Doacao direto por simplicidade no MVP e validar com usuario. |
| 2 | **Grafia "Deleucocitado" vs "Desleucocitado":** O PDF da Hemominas escreve "Deleucocitado" mas a aba BASE da planilha escreve "Desleucocitado". | Usar fuzzy matching ou tabela de aliases explicita no mapeamento de hemocomponentes. |
| 3 | **Formulas vs valores na Google Sheets API:** Ao inserir via API, precisa usar `valueInputOption: USER_ENTERED` para que formulas sejam interpretadas. | Usar `USER_ENTERED` e inserir formulas como string (ex: `=IF(D11="","",D11-TODAY())`). |
| 4 | **Multiplos comprovantes por pagina:** Um comprovante com muitas bolsas pode ocupar mais de uma pagina no PDF. O delimitador entre comprovantes e o cabecalho "Comprovante de Expedicao" + Nº. | Detectar inicio de novo comprovante pelo padrao "Comprovante de Expedicao" + "Nº" no texto extraido. |
| 5 | **Data de entrada:** O campo "em: DD/MM/YYYY" aparece no rodape junto a "Expedido por". Cada comprovante pode ter data diferente. | Extrair a data do campo "Expedido por...em:" para cada comprovante individualmente. |
| 6 | **Colunas E-G, L, N-S ficam em branco:** Sao preenchidas manualmente depois. Nao inserir nada nessas colunas. | Ao escrever via API, pular essas colunas (inserir string vazia ou null). |
| 7 | **Planilha tem 12700+ rows:** Append deve encontrar a ultima linha com dados e inserir abaixo. Nao confiar em max_row do Excel. | Usar `spreadsheets.values.append` da Google Sheets API que faz append automatico. |
| 8 | **Row 10 e header:** Dados comecam na row 11. Nunca sobrescrever row 10 ou anteriores. | Usar range "MAPA DE TRANSFUSAO!A11" com append para garantir insercao abaixo dos dados. |

---

## 5. Implementation Blueprint

### Tech Stack

| Componente | Tecnologia | Justificativa |
|------------|-----------|---------------|
| Backend | **Python 3 + Flask** | Settings ja permitem python3; Flask e simples para MVP |
| PDF Parsing | **pdfplumber** | Melhor lib Python para extracao de tabelas de PDFs estruturados |
| Google Sheets | **gspread + google-auth** | API wrapper Pythonic, mais simples que googleapis raw |
| Frontend | **HTML + Vanilla JS + CSS** | Single page, sem necessidade de framework; Jinja2 templates |
| Upload | **Flask file upload** | Nativo do Flask, sem dependencias extras |

### Dependencias (requirements.txt)

```
flask>=3.0
pdfplumber>=0.11
gspread>=6.0
google-auth>=2.0
google-auth-oauthlib>=1.0
python-dotenv>=1.0
```

### Data Models

```python
# Dados extraidos de uma bolsa (1 linha da tabela do PDF)
@dataclass
class BolsaExtraida:
    inst_coleta: str          # "B3013"
    num_doacao: str           # "25051087"
    componente_pdf: str       # "CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado"
    cod_isbt: str             # "E6514V00"
    seq: int                  # 1
    volume: int               # 292
    abo: str                  # "O"
    rh: str                   # "P"
    validade: date            # 2026-01-08

# Dados de um comprovante completo
@dataclass
class Comprovante:
    numero: str               # "1292305"
    data_emissao: datetime    # 2025-12-14 09:23:13
    instituicao: str          # "HMOB..."
    expedido_por: str         # "NILMARA TANIA VELOSO MATOS"
    data_expedicao: date      # 2025-12-14
    bolsas: list[BolsaExtraida]
    total_bolsas_declarado: int  # 5 (do "Total de bolsa(s) expedida(s)")

# Dados mapeados para a planilha (1 linha)
@dataclass
class LinhaPlanilha:
    dias_antes_vencimento: str   # Formula: "=IF(D{row}=\"\",\"\",D{row}-TODAY())"
    status: str                  # Formula: "=IF(A{row}=\"\",..."
    data_entrada: date           # 2025-12-14
    data_validade: date          # 2026-01-08
    tipo_hemocomponente: str     # "CHD - Concentrado de Hemacias Desleucocitado"
    gs_rh: str                   # "O/POS"
    volume: int                  # 292
    responsavel_recepcao: str    # "NILMARA TANIA VELOSO MATOS"
    num_bolsa: str               # "25051087"
```

### API Contracts

```yaml
POST /api/upload:
  description: Upload PDF e extrai dados
  request:
    content-type: multipart/form-data
    body:
      file: PDF file (max 10MB)
  response:
    200:
      comprovantes: int        # Nº de comprovantes encontrados
      total_bolsas: int        # Total de bolsas extraidas
      linhas:                  # Array de dados mapeados
        - num_comprovante: str
          data_entrada: str    # DD/MM/YYYY
          data_validade: str   # DD/MM/YYYY
          tipo_hemocomponente: str
          gs_rh: str
          volume: int
          responsavel: str
          num_bolsa: str
    400:
      error: str               # "Arquivo nao e PDF valido" / "Formato nao reconhecido"

POST /api/enviar:
  description: Envia dados extraidos para Google Sheets
  request:
    content-type: application/json
    body:
      linhas: array            # Mesmo formato do response de /api/upload
  response:
    200:
      linhas_inseridas: int
      mensagem: str
    500:
      error: str               # "Erro ao escrever na planilha"
```

### Integration Points

| Ponto | Arquivo | Modificacao |
|-------|---------|-------------|
| PDF Input | `src/pdf_extractor.py` | Criar — usa pdfplumber para extrair tabela e metadados |
| Mapeamento | `src/field_mapper.py` | Criar — converte dados brutos para formato planilha |
| Google Sheets | `src/sheets_writer.py` | Criar — autenticacao + append de linhas |
| Web Routes | `src/app.py` | Criar — rotas /api/upload e /api/enviar |
| Frontend | `src/templates/index.html` | Criar — upload + preview + confirmacao |

---

## 6. Tasks

### Task 1: Setup do projeto e dependencias
**Keywords:** create project structure, install dependencies, configure environment
**Files:**
- `requirements.txt` (create)
- `.env.example` (create)
- `.gitignore` (create)
- `src/config.py` (create)

**Description:**
Criar estrutura de diretorios, requirements.txt com dependencias, .env.example com variaveis necessarias (GOOGLE_SHEETS_ID, GOOGLE_CREDENTIALS_PATH), .gitignore (credentials/, .env, __pycache__), e config.py que carrega variaveis de ambiente.

**Validation:**
```bash
pip install -r requirements.txt
python3 -c "import pdfplumber, gspread, flask; print('OK')"
```

---

### Task 2: Implementar extracao do PDF
**Keywords:** find table pattern, extract structured data, parse dates, handle multi-page
**Files:**
- `src/pdf_extractor.py` (create)
- `tests/test_pdf_extractor.py` (create)

**Description:**
Usar pdfplumber para extrair dados do PDF de Comprovante de Expedicao da Hemominas.
1. Abrir PDF e iterar paginas
2. Para cada pagina, detectar inicio de comprovante (padrao "Comprovante de Expedicao" + "Nº")
3. Extrair Nº comprovante, data emissao
4. Extrair tabela de produtos usando `page.extract_table()` ou parsing de texto
5. Para cada linha da tabela: extrair Inst.Coleta, Nº Doacao, Componente, Cod.ISBT, Seq, Vol, ABO, Rh, Validade
6. Extrair "Total de bolsa(s) expedida(s)" e validar contra linhas extraidas
7. Extrair "Expedido por:" e data de expedicao
8. Retornar lista de `Comprovante` com suas `BolsaExtraida`

**Testar com PDF real:** `insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf`
- Deve encontrar 2 comprovantes
- Comprovante 1292305: 5 bolsas
- Comprovante 1292307: 1 bolsa
- Total: 6 bolsas

**Pseudocode:**
```python
def extrair_pdf(file_path: str) -> list[Comprovante]:
    comprovantes = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            # Find "Nº    NNNNNN" pattern for comprovante number
            # Find "Emissão:DD/MM/YYYY" for emission date
            # Extract table rows (between header row and "Total de Volume")
            # Parse each row into BolsaExtraida
            # Find "Expedido por : NAME" and "em: DD / MM / YYYY"
            # Validate total_bolsas == len(bolsas)
    return comprovantes
```

**Validation:**
```bash
python3 -m pytest tests/test_pdf_extractor.py -v
```

---

### Task 3: Implementar mapeamento e conversao de campos
**Keywords:** map PDF fields to spreadsheet columns, convert GS/RH, map hemocomponents
**Files:**
- `src/field_mapper.py` (create)
- `tests/test_field_mapper.py` (create)

**Description:**
Converter dados brutos extraidos do PDF para o formato da planilha.
1. Conversao GS/RH: combinar ABO + Rh → "ABO/POS" ou "ABO/NEG"
2. Mapeamento de hemocomponentes: tabela de aliases (nome PDF → nome BASE)
3. Formatacao de datas para o padrao da planilha
4. Construcao de formulas para colunas A e B
5. Montagem da lista de `LinhaPlanilha`

**Tabela de mapeamento de hemocomponentes (aliases):**
```python
HEMOCOMPONENTE_MAP = {
    # Chave: substring normalizada do PDF → Valor: nome completo da aba BASE
    "concentrado hemacias deleucocitado": "CHD -  Concentrado de Hemácias Desleucocitado",
    "concentrado hemacias desleucocitado": "CHD -  Concentrado de Hemácias Desleucocitado",
    "concentrado hemacias comum": "CHM -  Concentrado de Hemácias Comum",
    "concentrado hemacias camada leucoplaquetaria": "CHCR - Concentrado de Hemácias Camada Leucoplaquetária Removida",
    "concentrado hemacias fenotipado desleucocitado irradiado": "CHFDI -\xa0Concentrado de Hemácias Fenotipado, Desleucocitado e Irradiado",
    "concentrado hemacias fenotipado desleucocitado": "CHFD - Concentrado de Hemácias Fenotipado e Desleucocitado",
    "concentrado hemacias fenotipado": "CHF -  Concentrado de Hemácias Fenotipado",
    "concentrado hemacias irradiado": "CHI- Concentrado de Hemácias Radiado",
    "concentrado hemacias desleucocitado irradiado": "CHDI – Concentrado de Hemácias Desleucocitado e Irradiado",
    "plasma fresco congelado": "PFC - Plasma Fresco Congelado ",
    "plasma 24": "P24h – Plasma 24h",
    "crioprecipitado": "CRIO – Crioprecipitado ",
    "plaqueta randomica irradiada": "CPQI – Plaqueta Randômica Irradiada",
    "plaqueta randomica": "CPQ – Plaqueta Randômica",
    "eritroaferese desleucocitada irradiada": "HAFDI - Eritroaférese Desleucocitada Irradiada",
    "eritroaferese desleucocitada": "HAFD – Eritroaférese Desleucocitada",
    "plaquetaferese desleucocitada irradiada": "PAFDI - Plaquetaférese Desleucocitada Irradiada",
    "plaquetaferese desleucocitada": "PAFD – Plaquetaférese Desleucocitada",
    "pool de plaquetas desleucocitado irradiado": "PCPDI - Pool de Plaquetas Desleucocitado Irradiado",
    "pool de plaquetas desleucocitado": "PCPD – Pool de Plaquetas Desleucocitado",
    "pool de plaquetas inativacao": "IPPD - Pool de Plaquetas com inativação de Patógenos",
    "pool de plaquetas ressuspensos": "IPPA - Pool de plaquetas ressuspensos em PAS",
    "eritrocitoaferese desleucocitada fenotipada": "HAFDF - Eritrocitoaferese Desleucocitada e Fenotipada",
}
```

**Pseudocode:**
```python
def converter_gs_rh(abo: str, rh: str) -> str:
    rh_map = {"P": "POS", "N": "NEG"}
    return f"{abo}/{rh_map[rh]}"

def mapear_hemocomponente(componente_pdf: str) -> str:
    normalized = normalize(componente_pdf)  # lowercase, remove acentos
    for key, value in HEMOCOMPONENTE_MAP.items():
        if key in normalized:
            return value
    raise ValueError(f"Hemocomponente nao mapeado: {componente_pdf}")

def mapear_comprovantes(comprovantes: list[Comprovante]) -> list[LinhaPlanilha]:
    linhas = []
    for comp in comprovantes:
        for bolsa in comp.bolsas:
            linhas.append(LinhaPlanilha(
                dias_antes_vencimento="=IF(D{row}=\"\",\"\",D{row}-TODAY())",
                status="=IF(A{row}=\"\",\"\",IF(...))",
                data_entrada=comp.data_expedicao,
                data_validade=bolsa.validade,
                tipo_hemocomponente=mapear_hemocomponente(bolsa.componente_pdf),
                gs_rh=converter_gs_rh(bolsa.abo, bolsa.rh),
                volume=bolsa.volume,
                responsavel_recepcao=comp.expedido_por,
                num_bolsa=bolsa.num_doacao,
            ))
    return linhas
```

**Validation:**
```bash
python3 -m pytest tests/test_field_mapper.py -v
```

---

### Task 4: Implementar integracao Google Sheets
**Keywords:** authenticate Google API, append rows, inject formulas, preserve existing data
**Files:**
- `src/sheets_writer.py` (create)
- `tests/test_sheets_writer.py` (create)

**Description:**
Conectar a Google Sheets API e escrever os dados mapeados.
1. Autenticar via service account (credentials JSON)
2. Abrir planilha por ID (configuravel via .env)
3. Acessar aba "MAPA DE TRANSFUSAO"
4. Para cada LinhaPlanilha, montar array de valores nas colunas corretas (A-S)
5. Usar `worksheet.append_rows()` com `value_input_option='USER_ENTERED'`
6. Formulas nas colunas A e B precisam usar o row number correto

**Mapeamento de colunas (posicao no array):**
```python
# Index: 0=A, 1=B, 2=C, 3=D, 4=E, 5=F, 6=G, 7=H, 8=I, 9=J, 10=K, 11=L, 12=M
def montar_row(linha: LinhaPlanilha, row_num: int) -> list:
    formula_a = f'=IF(D{row_num}="","",D{row_num}-TODAY())'
    formula_b = f'=IF(A{row_num}="","",IF(A{row_num}<0,"VENCIDO",IF(A{row_num}=0,"VENCE HOJE",CONCATENATE("VENCE EM ",A{row_num}," DIAS"))))'
    return [
        formula_a,                          # A
        formula_b,                          # B
        linha.data_entrada.strftime("%d/%m/%Y"),  # C
        linha.data_validade.strftime("%d/%m/%Y"),  # D
        "",                                 # E - manual
        "",                                 # F - manual
        "",                                 # G - manual
        linha.tipo_hemocomponente,          # H
        linha.gs_rh,                        # I
        linha.volume,                       # J
        linha.responsavel_recepcao,         # K
        "",                                 # L - manual
        linha.num_bolsa,                    # M
    ]
```

**NOTA:** Para calcular o row_num correto, primeiro obter a ultima linha com dados via `len(worksheet.get_all_values())` e somar 1 para cada nova linha.

**Validation:**
```bash
python3 -m pytest tests/test_sheets_writer.py -v
# Teste manual com planilha de teste (nao a producao):
python3 -c "from src.sheets_writer import testar_conexao; testar_conexao()"
```

---

### Task 5: Implementar backend Flask (rotas API)
**Keywords:** wire routes, handle file upload, orchestrate pipeline, return JSON
**Files:**
- `src/app.py` (create)

**Description:**
Criar app Flask com duas rotas:
1. `POST /api/upload` — recebe PDF, chama pdf_extractor + field_mapper, retorna JSON com dados
2. `POST /api/enviar` — recebe JSON com linhas, chama sheets_writer, retorna resultado
3. `GET /` — serve o template index.html
4. Validacoes: arquivo PDF, tamanho max 10MB, formato correto

**Pseudocode:**
```python
@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    file = request.files['file']
    # Validar: e PDF? < 10MB?
    # Salvar temporariamente
    comprovantes = extrair_pdf(temp_path)
    linhas = mapear_comprovantes(comprovantes)
    # Retornar JSON com dados mapeados
    return jsonify({...})

@app.route('/api/enviar', methods=['POST'])
def enviar_planilha():
    linhas = request.json['linhas']
    resultado = escrever_sheets(linhas)
    return jsonify(resultado)
```

**Validation:**
```bash
python3 -c "from src.app import app; print('Flask app OK')"
```

---

### Task 6: Implementar frontend (Upload + Preview + Sucesso)
**Keywords:** create SPA, drag-drop upload, display table, send confirmation
**Files:**
- `src/templates/index.html` (create)
- `src/static/style.css` (create)
- `src/static/app.js` (create)

**Description:**
Single-page app com 4 estados (seguindo user journey `01-user-journey-core-import-flow.md`):

1. **Upload Screen:** Drop-zone central com drag-and-drop + botao "Selecionar arquivo". Mostra nome/tamanho apos selecao. Botao "Processar".
2. **Processing Screen:** Barra de progresso + steps (lendo PDF, extraindo, mapeando).
3. **Results Screen:** Tabela com dados extraidos (colunas: Comp#, Data Entrada, Validade, Tipo, GS/RH, Volume, Nº Bolsa). Botoes "Cancelar" e "Enviar para Planilha".
4. **Success Screen:** Confirmacao com contagem de bolsas inseridas + link para planilha + botao "Importar outro PDF".

**Layout:** Seguir wireframes do journey doc. Design funcional — fundo branco, tipografia clara, sem framework CSS (manter simples).

**Validation:**
```bash
# Iniciar servidor e verificar manualmente
cd src && python3 app.py
# Abrir http://localhost:5000
# Fazer upload do PDF de teste
# Verificar se dados aparecem corretamente na tela de resultados
```

---

### Task 7: Teste end-to-end com PDF real
**Keywords:** validate full pipeline, test with real data, verify output
**Files:**
- Nenhum novo — usa os existentes

**Description:**
Executar o pipeline completo com o PDF real `insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf`:
1. Upload do PDF via interface web
2. Verificar que 2 comprovantes e 6 bolsas sao detectados
3. Verificar mapeamento correto de todos os campos
4. Enviar para uma planilha de TESTE (nao a de producao)
5. Verificar dados na planilha

**Dados esperados apos extracao:**

| # | DATA ENTRADA | DATA VALIDADE | TIPO HEMOCOMPONENTE | GS/RH | VOL | RESPONSAVEL | Nº BOLSA |
|---|-------------|---------------|---------------------|-------|-----|------------|----------|
| 1 | 14/12/2025 | 08/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | O/POS | 292 | NILMARA TANIA VELOSO MATOS | 25051087 |
| 2 | 14/12/2025 | 08/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | A/POS | 273 | NILMARA TANIA VELOSO MATOS | 25009258 |
| 3 | 14/12/2025 | 22/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | A/POS | 300 | NILMARA TANIA VELOSO MATOS | 25053572 |
| 4 | 14/12/2025 | 20/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | O/NEG | 299 | NILMARA TANIA VELOSO MATOS | 25012667 |
| 5 | 14/12/2025 | 22/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | O/NEG | 287 | NILMARA TANIA VELOSO MATOS | 25014403 |
| 6 | 14/12/2025 | 23/01/2026 | CHD - Concentrado de Hemacias Desleucocitado | O/NEG | 276 | ANA OLIVEIRA | 25014485 |

**Validation:**
```bash
# Teste de extracao isolada
python3 -c "
from src.pdf_extractor import extrair_pdf
from src.field_mapper import mapear_comprovantes
comps = extrair_pdf('insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf')
assert len(comps) == 2
assert len(comps[0].bolsas) == 5
assert len(comps[1].bolsas) == 1
linhas = mapear_comprovantes(comps)
assert len(linhas) == 6
assert linhas[0].gs_rh == 'O/POS'
assert 'CHD' in linhas[0].tipo_hemocomponente
print('ALL ASSERTIONS PASSED')
"
```

---

## 7. Validation Gating

### Level 1: Syntax & Imports
```bash
python3 -c "
import src.pdf_extractor
import src.field_mapper
import src.sheets_writer
import src.app
print('All imports OK')
"
```
**Criterio:** Zero errors

### Level 2: Unit Tests
```bash
python3 -m pytest tests/ -v --tb=short
```
**Criterio:** All tests pass

### Level 3: Integration Test (PDF real)
```bash
python3 -c "
from src.pdf_extractor import extrair_pdf
from src.field_mapper import mapear_comprovantes
comps = extrair_pdf('insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf')
linhas = mapear_comprovantes(comps)
assert len(linhas) == 6
for l in linhas:
    assert l.gs_rh in ['O/POS','O/NEG','A/POS','A/NEG','B/POS','B/NEG','AB/POS','AB/NEG']
    assert l.volume > 0
    assert l.tipo_hemocomponente != ''
    assert l.num_bolsa != ''
print(f'OK: {len(linhas)} linhas mapeadas corretamente')
"
```
**Criterio:** 6 linhas extraidas e mapeadas corretamente

### Level 4: E2E (Servidor + Upload Manual)
```bash
# 1. Iniciar servidor
cd src && python3 app.py &

# 2. Upload via curl
curl -X POST http://localhost:5000/api/upload \
  -F "file=@../insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf"

# 3. Verificar response JSON com 6 bolsas
# 4. Kill servidor
```
**Criterio:** Response JSON contem 2 comprovantes e 6 bolsas com dados corretos

---

## 8. Final Checklist

### Quality Gates
- [ ] All Level 1 validations pass (imports)
- [ ] All Level 2 validations pass (unit tests)
- [ ] All Level 3 validations pass (PDF real)
- [ ] All Level 4 validations pass (E2E)
- [ ] PDF de teste extrai exatamente 6 bolsas em 2 comprovantes
- [ ] Conversao GS/RH funciona para todas 8 combinacoes
- [ ] Mapeamento de hemocomponentes cobre pelo menos o tipo do PDF de teste (CHD)
- [ ] Formulas A e B sao inseridas corretamente na planilha
- [ ] Append nao sobrescreve dados existentes
- [ ] Upload rejeita arquivos nao-PDF
- [ ] Telas seguem o fluxo do user journey (Upload → Processing → Results → Success)

### Patterns to Avoid
- [ ] Nao usar credenciais hardcoded (usar .env)
- [ ] Nao escrever em planilha de producao durante desenvolvimento (usar planilha de teste)
- [ ] Nao confiar em posicao fixa de colunas no PDF (usar deteccao de header)
- [ ] Nao ignorar erros de extracao silenciosamente (sempre retornar erro claro)
- [ ] Nao cachear dados da aba BASE indefinidamente (ler a cada importacao no futuro, Phase 2)

---

## 9. Confidence Assessment

**Score:** 8/10

**Factors:**
- [+2] PDF real disponivel como insumo de teste — validacao concreta
- [+2] Planilha real disponivel — estrutura, formulas e dados de referencia confirmados
- [+1] User journeys com wireframes detalhados — UI definida
- [+1] Feature specs completas com acceptance criteria
- [+1] Mapeamento de campos PDF→Planilha confirmado via analise dos insumos reais
- [+1] Formulas das colunas A e B extraidas do Excel real
- [-1] Formato Nº DA BOLSA divergente entre PDF e planilha existente (GOTCHA #1) — requer decisao do usuario
- [-1] Mapeamento de hemocomponentes baseado em apenas 1 tipo real (CHD) — outros tipos precisam validacao com mais PDFs

**Se score < 7, missing context:**
N/A — score e 8.

**Para chegar a 10:**
- Confirmar com usuario o formato correto do Nº DA BOLSA
- Obter mais PDFs de teste com outros tipos de hemocomponentes (PFC, CRIO, etc.)
- Configurar credenciais Google Sheets e testar conexao real

---

*PRP generated by dev-kit:10-generate-prp*
*IMPORTANTE: Execute em nova instancia do Claude Code (use /clear antes de executar)*
