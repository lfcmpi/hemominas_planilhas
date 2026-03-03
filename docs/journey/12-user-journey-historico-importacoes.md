# User Journey: Histórico de Importações (Phase 3)

**Covers feature:** 12 (Histórico de Importações)

---

## 1. Goal → Screen Mapping

```
GOAL                                    SCREEN
──────────────────────────────────────────────────────────
Ver todas as importações passadas       History Screen
Filtrar por período                     History Screen
Ver detalhes de uma importação          Import Detail Screen
```

---

## 2. Journey Diagram

```
                    ●
                    │
            ┌───────┴───────┐
            │   Histórico   │
            │ importações   │
            └───────┬───────┘
                    │
                    ◇ Filtrar?
                   ╱ ╲
                 sim  não
                  │    │
                  ▼    │
            ┌──────────┐│
            │ Aplicar  ││
            │ filtro   ││
            └────┬─────┘│
                 │      │
                 └──┬───┘
                    │
                    ◇ Ver detalhe?
                   ╱ ╲
                 sim  não
                  │    │
                  ▼    ▼
            ┌──────────┐
            │ Detalhe  │  ○
            │ importa. │
            └────┬─────┘
                 │
                 ○
```

---

## 3. Screen Layouts

### History Screen

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets       [Upload]  │
├────────────────────────────────────────┤
│  Histórico de Importações              │
│                                        │
│  De: [01/01/2026] Até: [28/02/2026]   │
│                          [ Filtrar ]   │
│                                        │
│  DATA       ARQUIVO       BOLSAS  ST  │
│  ──────────────────────────────────── │
│  28/02/26  RECEB-28_02     8     ✓    │
│  15/02/26  RECEB-15_02     12    ✓    │
│  02/02/26  RECEB-02_02     3     ⚠    │
│  20/01/26  RECEB-20_01     6     ✓    │
│  14/01/26  RECEB-14_01     6     ✓    │
│                                        │
│  Mostrando 5 de 23 importações   [▼]  │
└────────────────────────────────────────┘
```
← Lista cronológica reversa como padrão; filtro de período no topo para auditorias; status visual rápido por ícone

### Import Detail Screen

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets   [← Voltar]   │
├────────────────────────────────────────┤
│  Importação: 28/02/2026 às 14:32      │
│  Arquivo: RECEB-28_02_2026.pdf         │
│  Comprovantes: 3  ·  Bolsas: 8        │
│  Status: ✓ Sucesso                     │
├────────────────────────────────────────┤
│  Nº BOLSA    TIPO    GS     VOL  VAL  │
│  ──────────────────────────────────── │
│  25051087    CHD    O/POS   292  08/03 │
│  25009258    CHD    A/POS   273  08/03 │
│  25053572    CHD    A/POS   300  22/03 │
│  25012667    CHD    O/NEG   299  20/03 │
│  25014403    CHD    O/NEG   287  22/03 │
│  25014485    CHD    O/NEG   276  23/03 │
│  25019832    PFC    O/POS   268  15/04 │
│  25021004    CRIO   B/POS    26  31/05 │
└────────────────────────────────────────┘
```
← Detalhe mostra metadados da importação no topo + tabela completa das bolsas importadas; botão voltar claro para retornar à lista

---

## 4. Legend

```
◇ Filtrar?     : sim → aplica filtro de data; não → mostra todas
◇ Ver detalhe? : sim → abre detalhe da importação; não → fim
✓ = sucesso completo
⚠ = sucesso parcial (algumas bolsas com warning)
```
