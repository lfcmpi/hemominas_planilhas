# User Journey: Enhanced Review Flow (Phase 2)

**Covers features:** 06 (Preview e Confirmação), 07 (Campos Calculados), 08 (Validação BASE), 09 (Extração Responsável), 10 (Detecção Duplicatas)

**Modifies:** Results Screen from Phase 1 journey → becomes full Preview & Review Screen

---

## 1. Goal → Screen Mapping

```
GOAL                                    SCREEN
──────────────────────────────────────────────────────────
Revisar dados antes de enviar           Preview Screen
Editar campos com erro                  Preview Screen
Ver campos calculados (status)          Preview Screen
Ver validação contra BASE               Preview Screen
Ver responsável extraído                Preview Screen
Ver alertas de duplicatas               Preview Screen
Excluir/manter duplicatas               Preview Screen
Confirmar ou cancelar importação        Preview Screen
```

---

## 2. Journey Diagram

```
              (vem do Processing Screen - Phase 1)
                    │
            ┌───────┴───────┐
            │   Preview &   │
            │    Review     │
            └───────┬───────┘
                    │
                    ◇ Tem duplicatas?
                   ╱ ╲
                 sim  não
                  │    │
                  ▼    │
            ┌──────────┐│
            │ Resolver ││
            │ duplicat.││
            └────┬─────┘│
                 │      │
                 ▼      ▼
                 ◇ Tem erros de validação?
                ╱ ╲
              sim  não
               │    │
               ▼    │
         ┌──────────┐│
         │  Corrigir ││
         │  campos   ││
         └────┬──────┘│
              │       │
              ▼       ▼
              ◇ Confirmar?
             ╱ ╲
           sim  não
            │    │
            ▼    ▼
      ┌──────────┐ ┌──────────┐
      │  Enviar  │ │ Cancelar │
      │ c/ calc. │ │ descartar│
      └────┬─────┘ └────┬─────┘
           │             │
           ▼             ▼
     (Success Screen)  (Upload Screen)
```

---

## 3. Screen Layouts

### Preview Screen (Enhanced — replaces Phase 1 Results Screen)

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets         [Sobre] │
├────────────────────────────────────────┤
│ 2 comprov · 6 bolsas · 1 duplicata ⚠  │
│ Responsável: NILMARA T. VELOSO MATOS  │
├────────────────────────────────────────┤
│  ☐ DATA ENT  VALID.  TIPO  GS   VOL  │
│  ──────────────────────────────────── │
│  ☑ 14/12/25 08/01/26 CHD  O/POS  292 │
│  ☑ 14/12/25 08/01/26 CHD  A/POS  273 │
│  ☑ 14/12/25 22/01/26 CHD  A/POS  300 │
│  ⚠ 14/12/25 20/01/26 CHD  O/NEG  299 │
│  ☑ 14/12/25 22/01/26 CHD  O/NEG  287 │
│  🔴 14/12/25 23/01/26 CHD O/NEG  276 │
│                                    [▼] │
│ [ Cancelar ]  [ CONFIRMAR E ENVIAR ]  │
└────────────────────────────────────────┘
```
← Checkboxes para seleção individual; ícones de status (⚠ warning, 🔴 duplicata) inline; responsável no topo pois é dado do comprovante, não da bolsa

### Preview Screen — Inline Edit (on click)

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets         [Sobre] │
├────────────────────────────────────────┤
│ 2 comprov · 6 bolsas · 1 duplicata ⚠  │
│ Responsável: NILMARA T. VELOSO MATOS  │
├────────────────────────────────────────┤
│  ☐ DATA ENT  VALID.  TIPO  GS   VOL  │
│  ──────────────────────────────────── │
│  ☑ 14/12/25 08/01/26 CHD  O/POS  292 │
│  ☑ 14/12/25 08/01/26 CHD  A/POS  273 │
│  ┌──── Editando linha 3 ───────────┐  │
│  │ TIPO: [CHD            ▼]        │  │
│  │ GS:   [A/POS          ▼]        │  │
│  │ VOL:  [300       ]              │  │
│  │ [ Cancelar ]     [ Salvar ]     │  │
│  └──────────────────────────────────┘  │
│ [ Cancelar ]  [ CONFIRMAR E ENVIAR ]  │
└────────────────────────────────────────┘
```
← Edição inline expande a linha com dropdowns para campos com lista fixa (TIPO, GS) e input livre para numéricos (VOL); validação ao salvar

### Preview Screen — Duplicata Detail

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets         [Sobre] │
├────────────────────────────────────────┤
│ ⚠ 1 bolsa já existe na planilha       │
│                                        │
│  Bolsa: 25014485                       │
│  Já cadastrada em: 10/12/2025          │
│  Linha na planilha: 847                │
│                                        │
│  O que fazer?                          │
│  (●) Excluir da importação             │
│  ( ) Importar mesmo assim              │
│                                        │
│         [ Aplicar e voltar ]           │
│                                        │
│                                        │
│                                        │
└────────────────────────────────────────┘
```
← Mostra contexto da duplicata (quando foi cadastrada) para decisão informada; default é excluir (mais seguro) com override explícito

### Preview Screen — Validation Error

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets         [Sobre] │
├────────────────────────────────────────┤
│ ⚠ 1 campo com problema de validação   │
│                                        │
│  Linha 4 — Bolsa 25012667              │
│  ┌──────────────────────────────────┐  │
│  │ TIPO: "CHXX - Desconhecido"     │  │
│  │ ❌ Não encontrado na aba BASE   │  │
│  │                                  │  │
│  │ Corrigir: [Selecione...      ▼]  │  │
│  │  CHD - Conc. Hemácias Desleu.   │  │
│  │  CHM - Conc. Hemácias Comum     │  │
│  │  CHCR - Conc. Hemácias CLR      │  │
│  └──────────────────────────────────┘  │
│         [ Aplicar correção ]           │
└────────────────────────────────────────┘
```
← Erro mostra valor inválido + dropdown com valores válidos da BASE para correção rápida sem digitar

---

## 4. Legend

```
◇ Tem duplicatas?         : sim → painel de resolução com excluir/override; não → pula
◇ Tem erros de validação? : sim → destaque + edição obrigatória; não → pula
◇ Confirmar?              : sim → escreve (com campos calculados A,B); não → descarta e volta
⚠  = warning (validação)
🔴 = duplicata detectada
☑  = bolsa selecionada para importação
☐  = cabeçalho checkbox (selecionar todas)
```
