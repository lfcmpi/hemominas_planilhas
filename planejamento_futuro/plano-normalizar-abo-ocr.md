# Plano: Melhorar normalização ABO no OCR

**Data:** 2026-03-03
**Prioridade:** Alta (causa erros críticos que bloqueiam envio)
**Esforço:** Pequeno (~30 min)

## Problema

O Tesseract confunde a letra "O" (grupo sanguíneo) com dígitos variados.
Casos já conhecidos: `0`, `6`, `16`. Novo caso detectado: `9`.
A cada PDF novo pode surgir uma variante diferente.

**Exemplo real:** PDF de 02/03/2026 → OCR leu `9/POS` em vez de `O/POS`.

## Causa raiz

A função `_normalizar_abo()` em `src/pdf_extractor.py:34-48` trata dígitos
específicos (0, 6, 16) mas não cobre o caso genérico. O grupo "O" é o único
que o OCR confunde com números — "A", "B" e "AB" nunca são lidos como dígitos.

## Solução

Substituir as verificações individuais por uma regra de domínio genérica:
**se o valor limpo for composto apenas de dígitos, é "O"**.

## Arquivos a alterar

### 1. `src/pdf_extractor.py` (linha ~34-48)

**De:**
```python
def _normalizar_abo(raw: str) -> str:
    """Normalize ABO blood type from OCR output.

    OCR often misreads 'O' as '(0)', '(6)', '0', '6', '16)', etc.
    """
    cleaned = re.sub(r"[()|\[\]]", "", raw).strip()
    if cleaned in ("0", "6", "16"):
        return "O"
    if cleaned.upper() in ("O", "A", "B", "AB"):
        return cleaned.upper()
    # Fallback: try to extract a letter
    match = re.search(r"[OoAaBb]", cleaned)
    if match:
        return match.group().upper()
    return cleaned.upper()
```

**Para:**
```python
def _normalizar_abo(raw: str) -> str:
    """Normalize ABO blood type from OCR output.

    OCR often misreads 'O' as digits (0, 6, 9, 16, etc.).
    Rule: any all-digit value must be 'O' — the only blood group
    that OCR confuses with numbers.
    """
    cleaned = re.sub(r"[()|\[\]]", "", raw).strip()
    if cleaned.isdigit():
        return "O"
    if cleaned.upper() in ("O", "A", "B", "AB"):
        return cleaned.upper()
    # Fallback: try to extract a letter
    match = re.search(r"[OoAaBb]", cleaned)
    if match:
        return match.group().upper()
    return cleaned.upper()
```

**Mudança:** linha `if cleaned in ("0", "6", "16"):` → `if cleaned.isdigit():`

### 2. `tests/test_pdf_extractor.py` (classe TestNormalizarAbo, linha ~17)

Adicionar testes para o novo comportamento e o caso do "9":

```python
class TestNormalizarAbo:
    def test_letter_o(self):
        assert _normalizar_abo("O") == "O"

    def test_zero_becomes_o(self):
        assert _normalizar_abo("0") == "O"

    def test_parenthesis_zero(self):
        assert _normalizar_abo("(0)") == "O"

    def test_parenthesis_six(self):
        assert _normalizar_abo("(6)") == "O"

    def test_letter_a(self):
        assert _normalizar_abo("A") == "A"

    def test_letter_b(self):
        assert _normalizar_abo("B") == "B"

    def test_ab(self):
        assert _normalizar_abo("AB") == "AB"

    def test_sixteen(self):
        assert _normalizar_abo("16)") == "O"

    # --- NOVOS TESTES ---
    def test_nine_becomes_o(self):
        """OCR do PDF 02/03/2026 leu 'O' como '9'."""
        assert _normalizar_abo("9") == "O"

    def test_any_single_digit_becomes_o(self):
        """Qualquer digito isolado deve virar 'O'."""
        for d in "0123456789":
            assert _normalizar_abo(d) == "O", f"Falhou para '{d}'"

    def test_multi_digit_becomes_o(self):
        """Qualquer sequencia de digitos deve virar 'O'."""
        assert _normalizar_abo("16") == "O"
        assert _normalizar_abo("19") == "O"

    def test_parenthesis_nine(self):
        assert _normalizar_abo("(9)") == "O"
```

## Validação

1. Rodar os testes unitários: `python -m pytest tests/test_pdf_extractor.py -v`
2. Testar com o PDF problemático: `docs_novos/mapa de fornecimento 02-03-26.pdf`
3. Verificar que o GS/RH aparece como `O/POS` (não mais `9/POS`)
4. Confirmar que o erro crítico de validação desaparece

## Riscos

**Nenhum.** A regra `cleaned.isdigit() → "O"` é segura porque:
- Grupos sanguíneos válidos: O, A, B, AB
- "A" e "B" nunca são confundidos com dígitos pelo OCR
- Qualquer dígito no campo ABO só pode ser leitura errada de "O"
