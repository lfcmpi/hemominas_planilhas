# PRP: PDF-to-Sheets — Banco de Sangue (Phase 2 Enhance)

**Gerado em:** 2026-02-28
**Confidence Score:** 8.5/10
**Origem:** docs/* (product-roadmap, feature specs 06-10, user journey 06, Phase 1 PRP)
**Depende de:** Phase 1 MVP completa e funcional

---

## 1. Core (OBRIGATORIO)

### Goal
Evoluir a aplicacao web de importacao PDF-to-Sheets do banco de sangue do HMOB com preview interativo, validacao contra dados da aba BASE, deteccao de duplicatas e edicao inline — transformando a tela de resultados do Phase 1 em uma tela completa de revisao e confirmacao antes da escrita na planilha.

### Why
A Phase 1 entrega o pipeline funcional (PDF -> extracao -> planilha), mas sem validacao nem revisao: erros de extracao ou mapeamento so seriam descobertos apos ja estarem na planilha. Reimportacao acidental do mesmo PDF criaria duplicatas. E campos com mapeamento errado passariam despercebidos. A Phase 2 adiciona a rede de seguranca que o ambiente hospitalar exige — revisao, validacao, deteccao de duplicatas e correcao antes da escrita definitiva.

### What
**Phase 2 Enhance — Preview, Validacao e Protecao:**
1. Preview & Review Screen interativa com edicao inline (substitui Results Screen da Phase 1)
2. Validacao de TIPO DE HEMOCOMPONENTE e GS/RH contra listas da aba BASE do Google Sheets
3. Deteccao de duplicatas por Nº DA BOLSA contra coluna M da planilha
4. Dropdowns com valores validos da BASE para correcao rapida
5. Robustez dos campos calculados (formulas A e B) — validar que Phase 1 ja insere e garantir consistencia
6. Robustez da extracao de responsavel — normalizar nome extraido e tratar ausencias

### Success Criteria
- [ ] Tela de Preview exibe todos os dados mapeados com checkboxes por bolsa
- [ ] Campos TIPO e GS/RH mostram dropdown com valores validos da aba BASE
- [ ] Edicao inline funciona: click na linha expande editor, salvar atualiza os dados
- [ ] Campos com erro de mapeamento sao destacados visualmente (icone + cor)
- [ ] Bolsas duplicadas (Nº DA BOLSA ja existe na planilha) sao sinalizadas com icone vermelho
- [ ] Usuario pode excluir duplicatas ou forcar inclusao (override)
- [ ] Importacao bloqueada enquanto houver erros criticos (TIPO ou GS/RH invalido)
- [ ] Warnings em campos opcionais nao bloqueiam importacao
- [ ] Resumo visivel: "X bolsas de Y comprovantes prontas para importacao" + contagem de duplicatas
- [ ] Botao "Confirmar e Enviar" escreve na planilha; "Cancelar" descarta e volta ao upload
- [ ] Formulas A e B sao inseridas corretamente seguindo padrao existente
- [ ] Responsavel extraido com normalizacao (spaces, capitalizacao), campo vazio se nao encontrado

---

## 2. Context

### Codebase Analysis
```
BROWNFIELD — Phase 1 completa. Projeto existente com pipeline funcional.
- Estrutura: src/ com Flask app, pdf_extractor, field_mapper, sheets_writer
- Frontend: SPA com 4 estados (Upload, Processing, Results, Success)
- Testes: tests/ com testes unitarios e integracao
- Phase 2 MODIFICA arquivos existentes da Phase 1 (nao cria projeto novo)
- Insumos reais disponiveis para teste
```

### Arquivos Phase 1 que serao MODIFICADOS

| Arquivo | Papel na Phase 1 | Modificacao Phase 2 |
|---------|------------------|---------------------|
| `src/app.py` | Rotas /api/upload e /api/enviar | Adicionar rotas /api/base-values, /api/check-duplicates; modificar /api/upload para incluir validacao e duplicatas |
| `src/field_mapper.py` | Mapeamento/conversao de campos | Estender com validacao contra BASE; adicionar metodo de validacao |
| `src/sheets_writer.py` | Escreve dados na planilha | Adicionar leitura da aba BASE e leitura da coluna M para duplicatas |
| `src/templates/index.html` | SPA com 4 telas | Substituir tela Results por Preview & Review Screen completa |
| `src/static/app.js` | Logica frontend | Adicionar logica de edicao inline, checkboxes, resolucao duplicatas, validacao UI |
| `src/static/style.css` | Estilos basicos | Estender com estilos para preview, inline edit, status icons, duplicata panel |
| `src/pdf_extractor.py` | Extracao de dados do PDF | Melhorar robustez da extracao de "Expedido por" (normalizacao) |
| `src/config.py` | Configuracoes | Possivelmente adicionar configuracao de cache de BASE |

### Estrutura Real da Planilha Google Sheets (referencia Phase 1)

**Aba: MAPA DE TRANSFUSAO**
- Header na row 10, dados da row 11
- Coluna A: Formula `=IF(D{row}="","",D{row}-TODAY())`
- Coluna B: Formula `=IF(A{row}="","",IF(A{row}<0,"VENCIDO",IF(A{row}=0,"VENCE HOJE",CONCATENATE("VENCE EM ",A{row}," DIAS"))))`
- Coluna M: Nº DA BOLSA — chave para deteccao de duplicatas

**Aba: BASE (listas de referencia — lidas em runtime pela Phase 2)**
- Rows 15-24: GS/RH (O/NEG, O/POS, A/NEG, A/POS, B/NEG, B/POS, AB/NEG, AB/POS, OUTROS)
- Rows 48-70: TIPO DE HEMOCOMPONENTE (22 tipos, col A=nome completo, col B=abreviaturas)
- Rows 107-136: RESPONSAVEL RECEPCAO (28 nomes)

### Data Models (Existentes da Phase 1 + Extensoes Phase 2)

```python
# EXISTENTE (Phase 1) — preservar intacto
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

# NOVO (Phase 2) — adicionar ao projeto
@dataclass
class ValidacaoErro:
    campo: str                  # "tipo_hemocomponente" | "gs_rh"
    valor_atual: str            # "CHXX - Desconhecido"
    mensagem: str               # "Nao encontrado na aba BASE"
    nivel: str                  # "error" (bloqueia) | "warning" (nao bloqueia)
    valores_validos: list[str]  # Lista da BASE para dropdown

@dataclass
class DuplicataInfo:
    num_bolsa: str              # "25014485"
    linha_planilha: int         # 847
    data_cadastro: str | None   # "10/12/2025" (se conseguir extrair da row)

@dataclass
class LinhaPreview:
    """Estende LinhaPlanilha com metadados de preview"""
    linha: LinhaPlanilha
    num_comprovante: str        # "1292305"
    selecionada: bool           # True por default
    erros: list[ValidacaoErro]  # Erros de validacao
    duplicata: DuplicataInfo | None  # Info de duplicata se existir
    editada: bool               # True se usuario editou inline

@dataclass
class ValoresBase:
    """Cache das listas da aba BASE"""
    tipos_hemocomponente: list[str]    # 22 valores da col A, rows 48-70
    gs_rh: list[str]                   # 9 valores, rows 15-24
    responsaveis: list[str]            # 28 nomes, rows 107-136
    timestamp: datetime                # Quando foi lido
```

### Fluxo Phase 2 (Enhanced)

```
Upload PDF
    |
    v
Extracao (Phase 1 - inalterado)
    |
    v
Mapeamento (Phase 1 - inalterado)
    |
    v
[NOVO] Leitura da aba BASE (tipos, GS/RH)
    |
    v
[NOVO] Validacao contra BASE
    |
    v
[NOVO] Leitura coluna M (bolsas existentes)
    |
    v
[NOVO] Deteccao de duplicatas
    |
    v
[MODIFICADO] Preview & Review Screen
    |-- Edicao inline
    |-- Resolucao de duplicatas
    |-- Correcao de validacoes
    |
    v
Confirmacao
    |
    v
Escrita na planilha (Phase 1 - inalterado, mas com dados validados)
    |
    v
Success Screen
```

---

## 3. Tree Structure

### Before (Phase 1 Completed)
```
ana_planilha/
├── .claude/
│   └── settings.local.json
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── docs/
│   ├── product-roadmap-pdf-to-sheets-banco-sangue.md
│   ├── features/           (14 feature specs)
│   └── journey/            (5 user journeys)
├── insumos/
│   ├── BANCO DE SANGUE 2026 AT.xlsx
│   ├── RECEBIMENTO DE BOLSAS -15_12_2025.pdf
│   └── USAR ESSE BANCO DE SANGUE 2024 AT.xlsx
├── PRPs/
│   └── prps/
│       └── pdf-to-sheets-banco-sangue-phase1-prp.md
├── credentials/
│   └── .gitkeep
├── src/
│   ├── app.py                            # Flask app + rotas (upload, enviar)
│   ├── config.py                         # Configuracoes
│   ├── pdf_extractor.py                  # Extracao de dados do PDF
│   ├── field_mapper.py                   # Mapeamento/conversao de campos
│   ├── sheets_writer.py                  # Escrita Google Sheets
│   ├── templates/
│   │   └── index.html                    # SPA (Upload → Processing → Results → Success)
│   └── static/
│       ├── style.css
│       └── app.js
└── tests/
    ├── test_pdf_extractor.py
    ├── test_field_mapper.py
    └── test_sheets_writer.py
```

### After (Phase 2 Completed)
```
ana_planilha/
├── .claude/
│   └── settings.local.json
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt                      # (inalterado — sem novas dependencias)
├── docs/                                 # (inalterado)
├── insumos/                              # (inalterado)
├── PRPs/
│   └── prps/
│       ├── pdf-to-sheets-banco-sangue-phase1-prp.md
│       └── pdf-to-sheets-banco-sangue-phase2-prp.md
├── credentials/                          # (inalterado)
├── src/
│   ├── app.py                            # [MODIFICADO] Novas rotas: /api/base-values, /api/check-duplicates; /api/upload estendido
│   ├── config.py                         # [MODIFICADO] Config cache BASE
│   ├── pdf_extractor.py                  # [MODIFICADO] Robustez extracao responsavel
│   ├── field_mapper.py                   # [MODIFICADO] Validacao contra BASE
│   ├── sheets_reader.py                  # [NOVO] Leitura de aba BASE e coluna M
│   ├── validators.py                     # [NOVO] Validacao de dados contra BASE + duplicatas
│   ├── sheets_writer.py                  # [MODIFICADO] Robustez formulas A/B
│   ├── templates/
│   │   └── index.html                    # [MODIFICADO] Preview & Review Screen completa
│   └── static/
│       ├── style.css                     # [MODIFICADO] Estilos preview, inline edit, icons
│       └── app.js                        # [MODIFICADO] Logica preview, edit, duplicatas, validacao
└── tests/
    ├── test_pdf_extractor.py             # [MODIFICADO] Testes robustez responsavel
    ├── test_field_mapper.py              # [MODIFICADO] Testes validacao
    ├── test_sheets_reader.py             # [NOVO] Testes leitura BASE + duplicatas
    ├── test_validators.py                # [NOVO] Testes validacao + duplicatas
    └── test_sheets_writer.py             # [MODIFICADO] Testes robustez formulas
```

---

## 4. Known Gotchas

| # | Gotcha | Solucao |
|---|--------|---------|
| 1 | **Leitura da aba BASE a cada request pode ser lenta:** A planilha tem 12700+ rows. Ler BASE + coluna M em cada upload adiciona latencia significativa. | Ler BASE e coluna M em paralelo (duas chamadas async). Cachear valores da BASE por 5 minutos (listas mudam raramente). Coluna M sempre fresh (duplicatas precisam ser atuais). |
| 2 | **Rate limits da Google Sheets API:** Multiplas leituras (BASE rows 15-24, BASE rows 48-70, coluna M inteira) podem exceder quota. | Consolidar em poucas chamadas: uma para BASE (range amplo rows 15-136), uma para coluna M. Respeitar quota de 60 requests/min por usuario. |
| 3 | **Formato Nº DA BOLSA divergente (herdado Phase 1 Gotcha #1):** Se Phase 1 usou Nº Doacao direto (ex: "25051087") mas planilha existente tem formato longo (ex: "B32022500044633"), a deteccao de duplicatas falha — nunca encontra match. | Usar EXATAMENTE o mesmo formato que Phase 1 grava na coluna M. A comparacao deve ser string-to-string do valor como aparece na planilha. Se Phase 1 grava "25051087", comparar contra "25051087". |
| 4 | **Valores da BASE podem ter espacos extras, non-breaking spaces ou acentuacao inconsistente:** Os nomes na aba BASE contem acentos, espacos duplos e ate non-breaking spaces (xa0). | Normalizar ambos os lados da comparacao: strip, lowercase, remover non-breaking spaces. Mas PRESERVAR o valor original da BASE ao exibir no dropdown e ao gravar na planilha. |
| 5 | **Edicao inline altera dados ja validados:** Se o usuario edita um campo apos validacao, o novo valor precisa ser revalidado. | Re-executar validacao do campo editado ao clicar "Salvar" no editor inline. Frontend envia campo editado ao backend para revalidacao via POST /api/validate-field ou valida localmente se tiver a lista de valores. |
| 6 | **Coluna M pode conter celulas vazias intercaladas ou formatacao mista:** Celulas podem ter numero formatado como texto vs numero, ou linhas em branco no meio. | Ao ler coluna M, converter todos os valores para string e filtrar vazios. Comparacao sempre como string (str(valor).strip()). |
| 7 | **Campos calculados (A e B) — Phase 1 ja pode cobrir isso:** A Phase 1 PRP ja especifica insercao de formulas nas colunas A e B. Phase 2 deve validar, nao reimplementar. | Primeiro verificar se Phase 1 ja implementou formulas. Se sim, Phase 2 apenas adiciona testes de robustez. Se nao, implementar. Nao duplicar logica. |
| 8 | **Responsavel — Phase 1 ja extrai "Expedido por":** A Phase 1 PRP ja especifica extracao de responsavel. Phase 2 melhora robustez. | Verificar implementacao Phase 1 de extracao. Phase 2 adiciona: normalizacao de capitalizacao (TITLE CASE), remocao de espacos extras, tratamento gracioso se campo ausente (string vazia, nao erro). |
| 9 | **Checkbox "select all" vs bolsas com erro:** Se o usuario marca "selecionar todas" mas ha bolsas com erros criticos, o botao "Confirmar" deve permanecer desabilitado ate erros serem corrigidos. | Separar selecao de validacao. Bolsas selecionadas com erros criticos impedem confirmacao. UI mostra: "Corrija X erros para confirmar". |
| 10 | **Duplicata parcial — mesmo PDF com bolsas novas e existentes:** Um reupload pode ter 3 bolsas novas e 3 duplicatas. O usuario deve poder importar as novas e excluir as duplicatas. | Duplicatas sao sinalizadas individualmente. Checkbox default OFF para duplicatas, ON para novas. Usuario pode override cada uma. |

---

## 5. Implementation Blueprint

### Tech Stack

| Componente | Tecnologia | Justificativa |
|------------|-----------|---------------|
| Backend | **Python 3 + Flask** (existente) | Manter stack Phase 1 |
| PDF Parsing | **pdfplumber** (existente) | Inalterado |
| Google Sheets Read | **gspread** (existente) | Mesmo client para leitura e escrita |
| Google Sheets Write | **gspread** (existente) | Inalterado |
| Frontend | **HTML + Vanilla JS + CSS** (existente) | Estender SPA existente |
| Validacao | **Python stdlib** | Sem dependencia extra — comparacao de strings |

### Dependencias (requirements.txt)

```
# SEM MUDANCAS — Phase 2 nao adiciona novas dependencias
flask>=3.0
pdfplumber>=0.11
gspread>=6.0
google-auth>=2.0
google-auth-oauthlib>=1.0
python-dotenv>=1.0
```

### API Contracts (Novos e Modificados)

```yaml
# MODIFICADO — /api/upload agora retorna validacao e duplicatas
POST /api/upload:
  description: Upload PDF, extrai dados, valida contra BASE, detecta duplicatas
  request:
    content-type: multipart/form-data
    body:
      file: PDF file (max 10MB)
  response:
    200:
      comprovantes: int
      total_bolsas: int
      linhas:
        - num_comprovante: str
          data_entrada: str          # DD/MM/YYYY
          data_validade: str         # DD/MM/YYYY
          tipo_hemocomponente: str
          gs_rh: str
          volume: int
          responsavel: str
          num_bolsa: str
          selecionada: bool          # [NOVO] true por default, false se duplicata
          erros:                     # [NOVO] lista de erros de validacao
            - campo: str
              valor_atual: str
              mensagem: str
              nivel: str             # "error" | "warning"
              valores_validos: [str] # Lista para dropdown
          duplicata:                 # [NOVO] null se nao duplicata
            num_bolsa: str
            linha_planilha: int
            data_cadastro: str | null
      resumo:                        # [NOVO] resumo para exibicao
        total_bolsas: int
        total_comprovantes: int
        total_duplicatas: int
        total_erros_criticos: int
        total_warnings: int
      base_values:                   # [NOVO] listas da BASE para dropdowns
        tipos_hemocomponente: [str]
        gs_rh: [str]
    400:
      error: str

# MODIFICADO — /api/enviar agora recebe dados potencialmente editados
POST /api/enviar:
  description: Envia dados revisados/editados para Google Sheets
  request:
    content-type: application/json
    body:
      linhas: array                  # Apenas linhas selecionadas (sem duplicatas excluidas)
        - data_entrada: str
          data_validade: str
          tipo_hemocomponente: str    # Pode ter sido editado
          gs_rh: str                 # Pode ter sido editado
          volume: int                # Pode ter sido editado
          responsavel: str
          num_bolsa: str
  response:
    200:
      linhas_inseridas: int
      mensagem: str
    400:
      error: str                     # "Dados com erros criticos" (se frontend bypassar validacao)
    500:
      error: str

# NOVO — Validacao de campo individual (para revalidacao apos edicao inline)
POST /api/validate-field:
  description: Valida um campo editado contra a BASE
  request:
    content-type: application/json
    body:
      campo: str                     # "tipo_hemocomponente" | "gs_rh"
      valor: str                     # Novo valor digitado ou selecionado
  response:
    200:
      valido: bool
      mensagem: str | null           # Mensagem de erro se invalido
```

### Integration Points

| Ponto | Arquivo | Acao | Descricao |
|-------|---------|------|-----------|
| Leitura BASE | `src/sheets_reader.py` | **Criar** | Ler aba BASE (tipos, GS/RH, responsaveis) |
| Leitura duplicatas | `src/sheets_reader.py` | **Criar** | Ler coluna M da aba MAPA DE TRANSFUSAO |
| Validacao | `src/validators.py` | **Criar** | Validar dados contra listas da BASE + checar duplicatas |
| Pipeline upload | `src/app.py` | **Modificar** | Injetar validacao e duplicatas no fluxo de upload |
| Rota enviar | `src/app.py` | **Modificar** | Aceitar dados editados, revalidar antes de escrever |
| Rota validate | `src/app.py` | **Modificar** | Nova rota para validacao de campo individual |
| Extracao responsavel | `src/pdf_extractor.py` | **Modificar** | Robustez: normalizacao, tratamento de ausencia |
| Mapeamento | `src/field_mapper.py` | **Modificar** | Estender para retornar erros de mapeamento (nao so valor) |
| Formulas | `src/sheets_writer.py` | **Modificar** | Validar robustez de formulas A/B |
| Preview UI | `src/templates/index.html` | **Modificar** | Substituir Results Screen por Preview & Review Screen |
| Preview JS | `src/static/app.js` | **Modificar** | Logica de edicao inline, checkboxes, resolucao duplicatas |
| Preview CSS | `src/static/style.css` | **Modificar** | Estilos para status icons, inline editor, duplicata panel |

---

## 6. Tasks

### Task 1: Criar modulo de leitura do Google Sheets (sheets_reader.py)
**Keywords:** create reader module, find BASE tab, extract valid values, read column M
**Files:**
- `src/sheets_reader.py` (create)
- `tests/test_sheets_reader.py` (create)

**Description:**
Criar modulo separado para leituras do Google Sheets (separar responsabilidade de escrita em sheets_writer.py). Reutilizar a autenticacao/conexao ja existente em sheets_writer.py.

1. `ler_valores_base(spreadsheet_id) -> ValoresBase` — le aba BASE e retorna:
   - GS/RH: ler cells A15:A24, filtrar vazios → lista de strings
   - Tipos hemocomponente: ler cells A48:A70, filtrar vazios → lista de strings
   - Responsaveis: ler cells A107:A136, filtrar vazios → lista de strings
2. `ler_bolsas_existentes(spreadsheet_id) -> set[str]` — le coluna M da aba MAPA DE TRANSFUSAO:
   - Ler range "MAPA DE TRANSFUSAO!M11:M" (da row 11 ate o fim)
   - Converter todos os valores para string, strip whitespace
   - Filtrar celulas vazias
   - Retornar como set para O(1) lookup
3. Cache da BASE: armazenar resultado de `ler_valores_base` com timestamp; invalidar apos 5 minutos

**Pseudocode:**
```python
import gspread
from datetime import datetime, timedelta
from src.config import get_sheets_client

_base_cache = None
_base_cache_time = None
BASE_CACHE_TTL = timedelta(minutes=5)

def ler_valores_base(spreadsheet_id: str) -> ValoresBase:
    global _base_cache, _base_cache_time
    if _base_cache and _base_cache_time and datetime.now() - _base_cache_time < BASE_CACHE_TTL:
        return _base_cache

    client = get_sheets_client()
    sheet = client.open_by_key(spreadsheet_id)
    base_ws = sheet.worksheet("BASE")

    gs_rh = [v for v in base_ws.col_values(1)[14:24] if v.strip()]
    tipos = [v for v in base_ws.col_values(1)[47:70] if v.strip()]
    responsaveis = [v for v in base_ws.col_values(1)[106:136] if v.strip()]

    _base_cache = ValoresBase(
        tipos_hemocomponente=tipos,
        gs_rh=gs_rh,
        responsaveis=responsaveis,
        timestamp=datetime.now()
    )
    _base_cache_time = datetime.now()
    return _base_cache

def ler_bolsas_existentes(spreadsheet_id: str) -> set[str]:
    client = get_sheets_client()
    sheet = client.open_by_key(spreadsheet_id)
    mapa_ws = sheet.worksheet("MAPA DE TRANSFUSÃO")
    col_m_values = mapa_ws.col_values(13)  # Coluna M = 13
    # Pular header (rows 1-10)
    bolsas = {str(v).strip() for v in col_m_values[10:] if str(v).strip()}
    return bolsas
```

**Validation:**
```bash
python3 -m pytest tests/test_sheets_reader.py -v
```

---

### Task 2: Criar modulo de validacao (validators.py)
**Keywords:** create validator, find errors against BASE, detect duplicates, classify severity
**Files:**
- `src/validators.py` (create)
- `tests/test_validators.py` (create)

**Description:**
Criar modulo que valida os dados mapeados contra as listas da BASE e detecta duplicatas.

1. `validar_linha(linha: LinhaPlanilha, base: ValoresBase) -> list[ValidacaoErro]`:
   - Validar `tipo_hemocomponente` contra `base.tipos_hemocomponente` — nivel "error" se nao encontrado
   - Validar `gs_rh` contra `base.gs_rh` — nivel "error" se nao encontrado
   - Validar `volume` > 0 — nivel "warning" se zero ou negativo
   - Validar `responsavel_recepcao` nao vazio — nivel "warning" se vazio
   - Para cada erro, incluir lista de `valores_validos` do campo correspondente

2. `detectar_duplicatas(linhas: list[LinhaPlanilha], bolsas_existentes: set[str]) -> dict[str, DuplicataInfo]`:
   - Para cada linha, verificar se `num_bolsa` esta em `bolsas_existentes`
   - Se sim, criar `DuplicataInfo` com num_bolsa e info disponivel
   - Retornar dict: num_bolsa -> DuplicataInfo

3. `montar_preview(linhas: list[LinhaPlanilha], comprovantes: list[Comprovante], base: ValoresBase, bolsas_existentes: set[str]) -> list[LinhaPreview]`:
   - Para cada linha, executar validacao + deteccao duplicata
   - Montar `LinhaPreview` com resultados
   - Duplicatas: `selecionada = False` por default
   - Erros criticos: nao bloquear selecao, mas impedir confirmacao final

4. Normalizacao para comparacao: `_normalizar(valor: str) -> str`:
   - Strip whitespace (incluindo \xa0 non-breaking space)
   - Lowercase
   - Remover acentos (unicodedata.normalize + strip accents)
   - Usado APENAS para comparacao, nunca para gravar na planilha

**Pseudocode:**
```python
import unicodedata

def _normalizar(valor: str) -> str:
    valor = valor.replace('\xa0', ' ').strip()
    valor = unicodedata.normalize('NFD', valor)
    valor = ''.join(c for c in valor if unicodedata.category(c) != 'Mn')
    return valor.lower()

def validar_linha(linha: LinhaPlanilha, base: ValoresBase) -> list[ValidacaoErro]:
    erros = []
    # Validar tipo_hemocomponente
    tipos_norm = {_normalizar(t): t for t in base.tipos_hemocomponente}
    if _normalizar(linha.tipo_hemocomponente) not in tipos_norm:
        erros.append(ValidacaoErro(
            campo="tipo_hemocomponente",
            valor_atual=linha.tipo_hemocomponente,
            mensagem="Tipo de hemocomponente nao encontrado na aba BASE",
            nivel="error",
            valores_validos=base.tipos_hemocomponente
        ))
    # Validar gs_rh
    gs_norm = {_normalizar(g): g for g in base.gs_rh}
    if _normalizar(linha.gs_rh) not in gs_norm:
        erros.append(ValidacaoErro(
            campo="gs_rh",
            valor_atual=linha.gs_rh,
            mensagem="GS/RH nao encontrado na aba BASE",
            nivel="error",
            valores_validos=base.gs_rh
        ))
    # Warnings
    if linha.volume <= 0:
        erros.append(ValidacaoErro(
            campo="volume", valor_atual=str(linha.volume),
            mensagem="Volume deve ser maior que zero",
            nivel="warning", valores_validos=[]
        ))
    if not linha.responsavel_recepcao.strip():
        erros.append(ValidacaoErro(
            campo="responsavel_recepcao", valor_atual="",
            mensagem="Responsavel nao extraido do PDF",
            nivel="warning", valores_validos=base.responsaveis
        ))
    return erros
```

**Validation:**
```bash
python3 -m pytest tests/test_validators.py -v
```

---

### Task 3: Modificar pdf_extractor.py — Robustez da extracao de responsavel
**Keywords:** find "Expedido por" pattern, modify extraction, normalize name, wrap with error handling
**Files:**
- `src/pdf_extractor.py` (modify)
- `tests/test_pdf_extractor.py` (modify)

**Description:**
A Phase 1 ja extrai "Expedido por" — Phase 2 torna essa extracao mais robusta.

1. **Find** o trecho de codigo que extrai "Expedido por:" do texto da pagina
2. **Modify** para adicionar:
   - Normalizacao de capitalizacao: converter para TITLE CASE (ex: "nilmara tania" → "Nilmara Tania")
   - Remocao de espacos extras: regex `\s+` → single space, then strip
   - Tratamento de variantes: "Expedido por:" e "Expedido por :" (com espaco antes dos dois pontos)
3. **Wrap** a extracao em try/except: se falhar, retornar string vazia (nao propagar erro)
4. **Preserve** todo o resto da logica de extracao do Phase 1

**Pseudocode das modificacoes:**
```python
# ANTES (Phase 1 — hipotetico)
expedido_match = re.search(r'Expedido por\s*:\s*(.+?)(?:\s+em:)', text)
expedido_por = expedido_match.group(1) if expedido_match else ""

# DEPOIS (Phase 2 — robusto)
def _extrair_responsavel(text: str) -> str:
    """Extrai e normaliza o nome do responsavel do texto da pagina."""
    try:
        # Tentar varios padroes
        patterns = [
            r'Expedido por\s*:\s*(.+?)(?:\s+em\s*:)',
            r'Expedido por\s*:\s*(.+?)(?:\s+\d{2}/\d{2}/\d{4})',
            r'Expedido por\s*:\s*(.+?)$',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                nome = match.group(1).strip()
                # Remover espacos extras
                nome = re.sub(r'\s+', ' ', nome)
                # Normalizar capitalizacao (TITLE CASE)
                nome = nome.title()
                # Reverter preposicoes para lowercase (ex: "De" → "de")
                # Nao necessario se BASE usa UPPER CASE — verificar
                return nome
        return ""
    except Exception:
        return ""
```

**NOTA:** Antes de modificar, LER o codigo Phase 1 para entender a implementacao real. Nao assumir — adaptar as modificacoes ao codigo existente.

**Validation:**
```bash
python3 -m pytest tests/test_pdf_extractor.py -v
# Testar especificamente a extracao de responsavel
python3 -c "
from src.pdf_extractor import extrair_pdf
comps = extrair_pdf('insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf')
for c in comps:
    assert c.expedido_por.strip() != '', f'Responsavel vazio no comprovante {c.numero}'
    assert '  ' not in c.expedido_por, f'Espacos duplos em: {c.expedido_por}'
    print(f'Comprovante {c.numero}: Responsavel = \"{c.expedido_por}\"')
print('OK')
"
```

---

### Task 4: Modificar field_mapper.py — Estender com info de validacao
**Keywords:** modify mapper, inject validation metadata, extend return type, preserve mapping logic
**Files:**
- `src/field_mapper.py` (modify)
- `tests/test_field_mapper.py` (modify)

**Description:**
O field_mapper.py da Phase 1 faz mapeamento e levanta ValueError se nao encontra correspondencia. Na Phase 2, erros de mapeamento NAO devem ser excecoes — devem ser retornados como dados para exibicao no preview.

1. **Find** a funcao `mapear_hemocomponente()` que levanta ValueError
2. **Modify** para retornar o valor mais proximo ou o valor bruto do PDF quando nao encontra match, junto com flag de erro
3. **Find** a funcao `mapear_comprovantes()` que monta a lista de LinhaPlanilha
4. **Extend** para aceitar um parametro opcional `tolerante: bool = False`:
   - Se `tolerante=True` (Phase 2): nao levantar excecao em mapeamento falho; gravar valor bruto e sinalizar
   - Se `tolerante=False` (Phase 1 compat): manter comportamento original com ValueError
5. **Preserve** toda a logica de mapeamento existente (tabela HEMOCOMPONENTE_MAP, converter_gs_rh, etc.)

**Pseudocode:**
```python
# Modificar mapear_hemocomponente para modo tolerante
def mapear_hemocomponente(componente_pdf: str, tolerante: bool = False) -> tuple[str, bool]:
    """
    Retorna (valor_mapeado, sucesso).
    Se tolerante=True e nao encontra match: retorna (componente_pdf, False)
    Se tolerante=False e nao encontra match: levanta ValueError
    """
    normalized = _normalize(componente_pdf)
    for key, value in HEMOCOMPONENTE_MAP.items():
        if key in normalized:
            return (value, True)
    if tolerante:
        return (componente_pdf, False)  # Retorna valor bruto + flag de falha
    raise ValueError(f"Hemocomponente nao mapeado: {componente_pdf}")
```

**Validation:**
```bash
python3 -m pytest tests/test_field_mapper.py -v
```

---

### Task 5: Modificar sheets_writer.py — Validar robustez de formulas A/B
**Keywords:** find formula insertion, validate pattern, modify if needed, preserve append logic
**Files:**
- `src/sheets_writer.py` (modify)
- `tests/test_sheets_writer.py` (modify)

**Description:**
Phase 1 ja deveria inserir formulas nas colunas A e B. Phase 2 garante robustez.

1. **Find** o trecho que monta as formulas `=IF(D{row}...` e `=IF(A{row}...`
2. **Validate** que:
   - O row number e calculado corretamente (baseado na ultima linha + offset)
   - `valueInputOption` e `USER_ENTERED` (para que Google Sheets interprete formulas)
   - A formula segue EXATAMENTE o padrao existente na planilha (sem divergencia)
3. **Modify** se necessario para adicionar:
   - Validacao pre-escrita: confirmar que o row number calculado e o correto
   - Log do row number usado para cada formula (debugging)
4. **Preserve** toda a logica de append existente

**Adicionar validacao pre-escrita:**
```python
def _validar_row_numbers(start_row: int, num_linhas: int, worksheet) -> bool:
    """Verifica que as rows destino estao vazias antes de escrever."""
    # Ler o range que sera escrito
    range_check = f"A{start_row}:A{start_row + num_linhas - 1}"
    existing = worksheet.get(range_check)
    if any(row for row in existing if row and row[0]):
        raise ValueError(f"Rows {start_row}-{start_row + num_linhas - 1} ja contem dados!")
    return True
```

**Validation:**
```bash
python3 -m pytest tests/test_sheets_writer.py -v
```

---

### Task 6: Modificar app.py — Estender rotas com validacao e duplicatas
**Keywords:** modify upload route, inject validation pipeline, add new routes, preserve existing contract
**Files:**
- `src/app.py` (modify)

**Description:**
Estender o Flask app para orquestrar o fluxo Phase 2.

1. **Find** a rota `POST /api/upload`
2. **Modify** para apos extracao+mapeamento:
   - Chamar `sheets_reader.ler_valores_base()` para obter listas validas
   - Chamar `sheets_reader.ler_bolsas_existentes()` para obter bolsas existentes
   - Chamar `validators.montar_preview()` para gerar dados de preview com erros e duplicatas
   - Retornar JSON estendido com `erros`, `duplicata`, `selecionada`, `resumo`, `base_values`
3. **Modify** a rota `POST /api/enviar` para:
   - Aceitar apenas linhas selecionadas (filtradas pelo frontend)
   - Revalidar dados antes de escrever (nao confiar apenas no frontend)
   - Rejeitar com 400 se houver erros criticos nao resolvidos
4. **Criar** rota `POST /api/validate-field` para validacao de campo individual:
   - Recebe campo + valor, retorna se e valido + mensagem
5. **Preserve** a rota `GET /` e o comportamento base do app

**Pseudocode da rota upload modificada:**
```python
@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    file = request.files['file']
    # ... validacoes existentes (Phase 1) ...

    # Phase 1 — extracao e mapeamento
    comprovantes = extrair_pdf(temp_path)
    linhas = mapear_comprovantes(comprovantes, tolerante=True)  # [MODIFICADO] modo tolerante

    # Phase 2 — validacao e duplicatas
    base = ler_valores_base(SPREADSHEET_ID)
    bolsas_existentes = ler_bolsas_existentes(SPREADSHEET_ID)
    preview = montar_preview(linhas, comprovantes, base, bolsas_existentes)

    # Montar resumo
    total_duplicatas = sum(1 for p in preview if p.duplicata)
    total_erros = sum(1 for p in preview if any(e.nivel == "error" for e in p.erros))
    total_warnings = sum(1 for p in preview if any(e.nivel == "warning" for e in p.erros))

    return jsonify({
        "comprovantes": len(comprovantes),
        "total_bolsas": len(linhas),
        "linhas": [serialize_preview(p) for p in preview],
        "resumo": {
            "total_bolsas": len(linhas),
            "total_comprovantes": len(comprovantes),
            "total_duplicatas": total_duplicatas,
            "total_erros_criticos": total_erros,
            "total_warnings": total_warnings,
        },
        "base_values": {
            "tipos_hemocomponente": base.tipos_hemocomponente,
            "gs_rh": base.gs_rh,
        }
    })
```

**Validation:**
```bash
python3 -c "from src.app import app; print('Flask app OK')"
# Teste com curl:
# cd src && python3 app.py &
# curl -X POST http://localhost:5000/api/upload -F "file=@../insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf"
# Verificar que response tem campos: resumo, base_values, linhas[].erros, linhas[].duplicata
```

---

### Task 7: Modificar frontend — Preview & Review Screen
**Keywords:** modify index.html, inject preview screen, extend app.js with edit/validation logic, modify style.css
**Files:**
- `src/templates/index.html` (modify)
- `src/static/app.js` (modify)
- `src/static/style.css` (modify)

**Description:**
Substituir a tela Results da Phase 1 pela Preview & Review Screen completa. Esta e a tarefa mais complexa da Phase 2.

#### 7a. Modificar index.html — Preview Screen HTML

1. **Find** a secao/div da Results Screen da Phase 1
2. **Replace** com a Preview & Review Screen contendo:
   - Header resumo: "X comprov. / Y bolsas / Z duplicatas"
   - Campo responsavel no topo (por comprovante)
   - Tabela com colunas: Checkbox, DATA ENT, VALIDADE, TIPO, GS/RH, VOL, Nº BOLSA, STATUS (icons)
   - Cada linha com: checkbox para selecao, icones de status (warning, duplicata)
   - Footer com botoes: "Cancelar" e "CONFIRMAR E ENVIAR"
3. **Adicionar** template de inline editor (hidden por default):
   - Dropdown para TIPO (populated com base_values.tipos_hemocomponente)
   - Dropdown para GS/RH (populated com base_values.gs_rh)
   - Input numerico para VOLUME
   - Botoes "Cancelar" e "Salvar"
4. **Adicionar** painel de duplicata (hidden por default):
   - Info da duplicata (bolsa, linha, data)
   - Radio: "Excluir da importacao" (default) / "Importar mesmo assim"
   - Botao "Aplicar e voltar"
5. **Adicionar** painel de erro de validacao (hidden por default):
   - Mostra valor invalido + mensagem
   - Dropdown com valores validos para correcao rapida
   - Botao "Aplicar correcao"
6. **Preserve** as telas Upload, Processing e Success da Phase 1

#### 7b. Modificar app.js — Logica de preview

1. **Find** o handler de resposta do /api/upload (que popula Results Screen)
2. **Modify** para popular a nova Preview Screen:
   - Renderizar tabela com dados de preview
   - Mostrar icones de status por linha
   - Preencher dropdowns com base_values
   - Marcar checkboxes (ON para novas, OFF para duplicatas)
   - Exibir contadores no header
3. **Adicionar** handlers de edicao inline:
   - Click na linha → expandir inline editor com valores atuais
   - Salvar → POST /api/validate-field → atualizar dados + fechar editor
   - Cancelar → fechar editor sem alterar
4. **Adicionar** handlers de duplicata:
   - Click no icone de duplicata → expandir painel de duplicata
   - "Excluir" → desmarcar checkbox
   - "Importar mesmo assim" → marcar checkbox
5. **Adicionar** logica de bloqueio de confirmacao:
   - Desabilitar botao "CONFIRMAR E ENVIAR" se ha linhas selecionadas com erros criticos
   - Mostrar mensagem: "Corrija X erros para confirmar"
6. **Modificar** handler de "CONFIRMAR E ENVIAR":
   - Filtrar apenas linhas selecionadas
   - POST /api/enviar com dados filtrados
7. **Preserve** logica de upload, processing e success

#### 7c. Modificar style.css — Estilos de preview

1. **Adicionar** estilos para:
   - Tabela de preview (bordas, padding, hover)
   - Inline editor (background destacado, transicao expand/collapse)
   - Icones de status: warning (amarelo), duplicata (vermelho), valido (verde)
   - Checkbox styling
   - Painel de duplicata e validacao (borda lateral colorida)
   - Botao CONFIRMAR desabilitado (cinza quando bloqueado)
   - Resumo header (badge counts)
2. **Preserve** estilos existentes da Phase 1

**Wireframe de referencia (da user journey):**
```
┌────────────────────────────────────────┐
│ Hemominas → Sheets              [Sobre]│
├────────────────────────────────────────┤
│ 2 comprov · 6 bolsas · 1 duplicata    │
│ Responsavel: NILMARA T. VELOSO MATOS  │
├────────────────────────────────────────┤
│  [ ] DATA ENT  VALID.  TIPO  GS  VOL  │
│  ─────────────────────────────────────│
│  [x] 14/12/25 08/01/26 CHD O/POS 292  │
│  [x] 14/12/25 08/01/26 CHD A/POS 273  │
│  [!] 14/12/25 22/01/26 CHD A/POS 300  │  ← warning
│  [x] 14/12/25 20/01/26 CHD O/NEG 299  │
│  [x] 14/12/25 22/01/26 CHD O/NEG 287  │
│  [D] 14/12/25 23/01/26 CHD O/NEG 276  │  ← duplicata
│                                        │
│  [ Cancelar ]  [ CONFIRMAR E ENVIAR ] │
└────────────────────────────────────────┘
```

**Validation:**
```bash
# Iniciar servidor e verificar manualmente:
cd src && python3 app.py
# Abrir http://localhost:5000
# Upload do PDF de teste
# Verificar:
# - Tabela de preview aparece com dados corretos
# - Dropdowns populados com valores da BASE
# - Click em linha expande editor inline
# - Icones de status visiveis
# - Checkbox funciona (selecionar/deselecionar)
# - Botao CONFIRMAR se comporta corretamente com erros
```

---

### Task 8: Testes de integracao Phase 2
**Keywords:** validate full Phase 2 pipeline, test validation + duplicates + preview flow
**Files:**
- Nenhum novo — usa os existentes

**Description:**
Executar o pipeline completo Phase 2 com o PDF real:

1. Upload do PDF via interface web
2. Verificar que Preview Screen aparece (nao Results Screen)
3. Verificar que dados de validacao estao presentes (campos validados contra BASE)
4. Simular duplicata: inserir manualmente um num_bolsa de teste na planilha, re-fazer upload, verificar que duplicata e detectada
5. Testar edicao inline: alterar um campo, verificar revalidacao
6. Testar exclusao de duplicata: desmarcar bolsa duplicada, confirmar envio de apenas as nao-duplicatas
7. Verificar formulas A e B na planilha apos escrita

**Dados esperados:**
- 6 bolsas extraidas, 2 comprovantes
- Validacao: TIPO e GS/RH devem ser validos (CHD esta na BASE, O/POS esta na BASE)
- Se nenhum num_bolsa existe na planilha: 0 duplicatas
- Responsavel: "Nilmara Tania Veloso Matos" ou formato normalizado

**Validation:**
```bash
# Teste de pipeline Phase 2 isolado
python3 -c "
from src.pdf_extractor import extrair_pdf
from src.field_mapper import mapear_comprovantes
from src.sheets_reader import ler_valores_base, ler_bolsas_existentes
from src.validators import montar_preview
from src.config import SPREADSHEET_ID

# Extracao (Phase 1)
comps = extrair_pdf('insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf')
linhas = mapear_comprovantes(comps, tolerante=True)
assert len(linhas) == 6

# Validacao (Phase 2)
base = ler_valores_base(SPREADSHEET_ID)
assert len(base.tipos_hemocomponente) >= 20, f'Esperado 20+ tipos, got {len(base.tipos_hemocomponente)}'
assert len(base.gs_rh) >= 8, f'Esperado 8+ GS/RH, got {len(base.gs_rh)}'

bolsas = ler_bolsas_existentes(SPREADSHEET_ID)

preview = montar_preview(linhas, comps, base, bolsas)
assert len(preview) == 6

erros_criticos = [p for p in preview if any(e.nivel == 'error' for e in p.erros)]
print(f'Erros criticos: {len(erros_criticos)}')
for p in erros_criticos:
    for e in p.erros:
        print(f'  Bolsa {p.linha.num_bolsa}: {e.campo} = \"{e.valor_atual}\" -> {e.mensagem}')

duplicatas = [p for p in preview if p.duplicata]
print(f'Duplicatas: {len(duplicatas)}')

print(f'OK: {len(preview)} linhas no preview, {len(erros_criticos)} erros, {len(duplicatas)} duplicatas')
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
import src.sheets_reader
import src.validators
import src.app
print('All imports OK')
"
```
**Criterio:** Zero errors

### Level 2: Unit Tests
```bash
python3 -m pytest tests/ -v --tb=short
```
**Criterio:** All tests pass (Phase 1 tests still pass + Phase 2 new tests pass)

### Level 3: Validacao contra BASE (Integration)
```bash
python3 -c "
from src.sheets_reader import ler_valores_base
from src.config import SPREADSHEET_ID

base = ler_valores_base(SPREADSHEET_ID)
assert len(base.tipos_hemocomponente) >= 20, f'Expected 20+ tipos, got {len(base.tipos_hemocomponente)}'
assert len(base.gs_rh) >= 8, f'Expected 8+ GS/RH, got {len(base.gs_rh)}'
assert 'O/POS' in base.gs_rh or any('O/POS' in v for v in base.gs_rh)
print(f'BASE: {len(base.tipos_hemocomponente)} tipos, {len(base.gs_rh)} GS/RH, {len(base.responsaveis)} responsaveis')
print('Validacao BASE OK')
"
```
**Criterio:** Leitura da BASE retorna listas completas

### Level 4: Deteccao de Duplicatas (Integration)
```bash
python3 -c "
from src.sheets_reader import ler_bolsas_existentes
from src.config import SPREADSHEET_ID

bolsas = ler_bolsas_existentes(SPREADSHEET_ID)
print(f'Bolsas existentes na planilha: {len(bolsas)}')
# Verificar que retorna set nao vazio (planilha tem 12700+ rows)
assert len(bolsas) > 0, 'Nenhuma bolsa encontrada — verificar leitura da coluna M'
print('Leitura duplicatas OK')
"
```
**Criterio:** Retorna set com bolsas existentes

### Level 5: Pipeline Completo Phase 2
```bash
python3 -c "
from src.pdf_extractor import extrair_pdf
from src.field_mapper import mapear_comprovantes
from src.sheets_reader import ler_valores_base, ler_bolsas_existentes
from src.validators import montar_preview, validar_linha
from src.config import SPREADSHEET_ID

comps = extrair_pdf('insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf')
linhas = mapear_comprovantes(comps, tolerante=True)
base = ler_valores_base(SPREADSHEET_ID)
bolsas = ler_bolsas_existentes(SPREADSHEET_ID)
preview = montar_preview(linhas, comps, base, bolsas)

assert len(preview) == 6
for p in preview:
    assert p.linha.num_bolsa != ''
    assert p.linha.tipo_hemocomponente != ''
    assert p.linha.gs_rh != ''
print(f'Pipeline Phase 2 OK: {len(preview)} linhas no preview')
"
```
**Criterio:** 6 linhas no preview com dados completos

### Level 6: E2E (Servidor + Frontend)
```bash
# 1. Iniciar servidor
cd src && python3 app.py &

# 2. Upload via curl
curl -s -X POST http://localhost:5000/api/upload \
  -F "file=@../insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf" | python3 -m json.tool

# 3. Verificar response JSON contem:
#    - resumo.total_bolsas == 6
#    - resumo.total_comprovantes == 2
#    - base_values.tipos_hemocomponente (lista com 20+ items)
#    - base_values.gs_rh (lista com 8+ items)
#    - linhas[].erros (pode ser lista vazia se tudo valido)
#    - linhas[].duplicata (null se nao duplicata)

# 4. Kill servidor
```
**Criterio:** Response JSON contem todos os campos Phase 2 com dados corretos

---

## 8. Final Checklist

### Quality Gates
- [ ] All Level 1 validations pass (imports — Phase 1 + Phase 2 modules)
- [ ] All Level 2 validations pass (unit tests — Phase 1 continuam passando)
- [ ] All Level 3 validations pass (leitura da aba BASE)
- [ ] All Level 4 validations pass (leitura de duplicatas)
- [ ] All Level 5 validations pass (pipeline completo Phase 2)
- [ ] All Level 6 validations pass (E2E com servidor)
- [ ] Preview Screen substitui Results Screen da Phase 1
- [ ] Dados de preview mostram erros de validacao quando aplicavel
- [ ] Duplicatas sao detectadas e sinalizadas corretamente
- [ ] Edicao inline funciona com dropdowns para TIPO e GS/RH
- [ ] Validacao bloqueia confirmacao quando ha erros criticos
- [ ] Warnings nao bloqueiam confirmacao
- [ ] Checkboxes permitem selecao/desselecao individual
- [ ] Duplicatas vem desmarcadas por default
- [ ] Formulas A e B sao inseridas corretamente
- [ ] Responsavel e extraido e normalizado
- [ ] Nenhum teste da Phase 1 quebrou

### Patterns to Follow
- [ ] Modificar arquivos existentes — nao duplicar logica
- [ ] Manter backward compatibility das funcoes Phase 1 (parametros opcionais)
- [ ] Testar com o MESMO PDF real da Phase 1 (insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf)
- [ ] Normalizar strings para comparacao mas preservar valores originais para exibicao e gravacao
- [ ] Separar leitura (sheets_reader) de escrita (sheets_writer) em modulos distintos

### Patterns to Avoid
- [ ] Nao cachear bolsas existentes (coluna M) — sempre ler fresh para duplicatas
- [ ] Nao validar no frontend apenas — backend deve revalidar antes de escrever
- [ ] Nao quebrar testes da Phase 1 ao modificar funcoes existentes
- [ ] Nao hardcodar ranges da aba BASE — usar constantes em config.py
- [ ] Nao ignorar non-breaking spaces (xa0) na comparacao de strings
- [ ] Nao bloquear importacao por warnings (apenas errors bloqueiam)
- [ ] Nao cachear BASE por mais de 5 minutos (usuario pode editar a aba BASE)

---

## 9. Confidence Assessment

**Score:** 8.5/10

**Factors:**
- [+2] Phase 1 PRP completo e detalhado — baseline bem definida
- [+1.5] Feature specs 06-10 com acceptance criteria claros
- [+1.5] User journey 06 com wireframes detalhados da Preview Screen
- [+1] Estrutura da aba BASE documentada (rows, colunas, tipos)
- [+1] Mapeamento PDF→Planilha ja validado na Phase 1 com dados reais
- [+1] Dados reais (PDF e planilha) disponiveis para teste
- [+0.5] API contract Phase 1 serve como base para extensoes
- [-0.5] Formato Nº DA BOLSA (Gotcha #3) — depende da decisao/implementacao da Phase 1
- [-0.5] Implementacao real da Phase 1 pode divergir do PRP — Tasks devem ser adaptadas ao codigo existente
- [-0.5] Edicao inline no frontend e complexa em vanilla JS — pode exigir mais iteracoes

**Se score < 7, missing context:**
N/A — score e 8.5.

**Para chegar a 10:**
- Ter a Phase 1 implementada e testada para validar que as funcoes existem como descrito
- Ter mais PDFs de teste com tipos variados (PFC, CRIO, etc.) para validar mapeamento
- Confirmar comportamento do formato Nº DA BOLSA na coluna M da planilha real
- Testar latencia real da leitura da BASE + coluna M (12700+ rows)

---

*PRP generated by dev-kit:10-generate-prp*
*IMPORTANTE: Execute em nova instancia do Claude Code (use /clear antes de executar)*
*PRE-REQUISITO: Phase 1 deve estar completa e funcional antes de iniciar Phase 2*
