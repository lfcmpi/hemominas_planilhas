# Análise de Processamento dos PDFs - docs_novos/

**Data:** 2026-03-02

## Resumo dos PDFs

| PDF | Páginas | Comprovantes | Bolsas |
|-----|---------|-------------|--------|
| `mapa de fornecimento 02-03-26.pdf` | 2 | 2 | **12** |
| `RECEBIMENTO DE BOLSAS -15_12_2025.pdf` | 2 | 2 | **6** |
| `mapa de fornecimento 13-02-26 a 27-02-26.pdf` | 20 (10 dados + 10 verso em branco) | 10 | **32** |
| **TOTAL** | 24 | 14 | **50** |

## BUGS CRÍTICOS ENCONTRADOS

### 1. Regex do código ISBT falha para códigos com letras (E5854VA0, E5854VB0)

**Arquivo:** `src/pdf_extractor.py:180`

O pattern atual é:
```python
r"(E\d{4}V\d{2})\s+"    # cod_isbt
```
Espera `V` + 2 dígitos (`V00`, `V02`, etc.), mas os PDFs contêm:
- `E5854VA0` (Pool Plaquetas, Seq 1)
- `E5854VB0` (Pool Plaquetas, Seq 2)

A letra `A` e `B` após o `V` faz a regex falhar. **5 bolsas são completamente perdidas** (nunca extraídas do OCR):
- Comprovante 1319395: 1 bolsa
- Comprovante 1319782: 2 bolsas
- Comprovante 1320249: 1 bolsa
- Comprovante 1320326: 1 bolsa

### 2. Mapeamento de "CONC HEMACIAS CAMADA LEUCOPLAQ REMOVIDA" falha

**Arquivo:** `src/field_mapper.py:35`

A chave do mapa é `"concentrado hemacias camada leucoplaquetaria"`, mas o PDF usa a forma abreviada `"CONC HEMACIAS CAMADA LEUCOPLAQ REMOVIDA"`. A normalização resulta em `"conc hemacias camada leucoplaq removida"` — a chave NÃO é substring deste texto porque:
- `"concentrado"` ≠ `"conc"`
- `"leucoplaquetaria"` ≠ `"leucoplaq"`

**Afeta 3 bolsas** (2 no PDF 1, 1 no PDF 3).

### 3. Mapeamento de "CONCENTRADO HEMACIAS Deleucocitado **e** Irradiado" falha

**Arquivo:** `src/field_mapper.py:30`

A chave é `"concentrado hemacias deleucocitado irradiado"`, mas o PDF tem a palavra **"e"** entre os termos: `"Deleucocitado e Irradiado"`. O "e" quebra a correspondência de substring.

**Afeta 1 bolsa** (PDF 3, comprovante 1319676).

### 4. "CONCENTRADO HEMACIAS" (simples, sem qualificador) não tem mapeamento

**Arquivo:** `src/field_mapper.py:36`

A chave mais próxima é `"concentrado hemacias comum"`, mas o PDF diz apenas `"CONCENTRADO HEMACIAS"` (cod. E0195V00), sem a palavra "comum". Nenhuma chave é substring do texto normalizado.

**Afeta 1 bolsa** (PDF 3, comprovante 1319780).

### 5. "PLASMA DE 24 HORAS" não mapeia corretamente

**Arquivo:** `src/field_mapper.py:38`

A chave é `"plasma 24"`, mas o texto normalizado é `"plasma de 24 horas"`. O `"de"` entre "plasma" e "24" impede que `"plasma 24"` seja encontrado como substring.

**Afeta 5 bolsas** (PDF 3, comprovante 1319783).

### 6. "POOL PLAQ INATIVACAO DE PATOGENOS PAS..." não mapeia

**Arquivo:** `src/field_mapper.py:48`

A chave é `"pool de plaquetas inativacao"`, mas o PDF diz `"POOL PLAQ INATIVACAO..."`. `"plaq"` ≠ `"plaquetas"` e falta `"de"`. Nenhuma chave faz match.

**Afeta 5 bolsas** (as mesmas do bug #1, agravando).

### 7. "CONC. DE HEMACIAS AFERESE DESLEUCOCITADO" sem mapeamento

**Arquivo:** `src/field_mapper.py`

O mapa tem `"eritroaferese desleucocitada"`, mas o PDF usa `"CONC. DE HEMACIAS AFERESE DESLEUCOCITADO"`. São nomenclaturas completamente diferentes.

**Afeta 2 bolsas** (PDF 3, comprovante 1320327).

## BUG DE INTEGRIDADE DE DADOS

### 8. `num_bolsa` usa apenas `num_doacao`, ignorando `seq` — duplicatas falsas

**Arquivo:** `src/field_mapper.py:123`

```python
num_bolsa=bolsa.num_doacao,  # Apenas número de doação
```

Vários PDFs contêm bolsas com o **mesmo número de doação mas sequências diferentes** (produtos distintos da mesma doação):
- `26007133` Seq 1 (E4544V00) + Seq 2 (E4545V00)
- `26701509` Seq 1 (E5854VA0) + Seq 2 (E5854VB0)

A segunda bolsa de cada par seria marcada como duplicata e potencialmente rejeitada.

**Afeta 4 bolsas** no PDF 3.

## IMPACTO TOTAL POR PDF

| PDF | Total Bolsas | Bolsas OK | Com Problema | % Perda |
|-----|-------------|-----------|-------------|---------|
| PDF 1 (02-03-26) | 12 | 10 | 2 (mapeamento) | 17% |
| PDF 2 (15-12-2025) | 6 | **6** | 0 | 0% |
| PDF 3 (13-02-26 a 27-02-26) | 32 | 14 | **18** | 56% |
| **TOTAL** | **50** | **30** | **20** | **40%** |

## O QUE FUNCIONA CORRETAMENTE

- Páginas em branco (verso do PDF 3) são ignoradas corretamente
- Extração de metadados do comprovante (número, data, instituição, expedido por)
- "CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado" (tipo mais comum) → extrai e mapeia OK
- "CRIOPRECIPITADO" → mapeia corretamente (match exato)
- Normalização de ABO (O, A, B, AB) e Rh (P→POS, N→NEG)
- Detecção de continuação de componente em múltiplas linhas
- Validação contra aba BASE e detecção de duplicatas (lógica funcional)
- Escrita na planilha com fórmulas corretas
