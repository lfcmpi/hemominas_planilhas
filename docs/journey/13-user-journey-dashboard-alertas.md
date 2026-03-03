# User Journey: Dashboard de Estoque + Alertas (Phase 3)

**Covers features:** 13 (Dashboard de Estoque), 14 (Alertas de Vencimento)

---

## 1. Goal → Screen Mapping

```
GOAL                                    SCREEN
──────────────────────────────────────────────────────────
Ver estoque por tipo sanguíneo          Dashboard Screen
Ver estoque por hemocomponente          Dashboard Screen
Ver bolsas perto do vencimento          Dashboard Screen
Configurar alertas de vencimento        Alert Settings Screen
Receber notificação de vencimento       (Email / In-app)
```

---

## 2. Journey Diagram

```
                    ●
                    │
            ┌───────┴───────┐
            │   Dashboard   │
            │   estoque     │
            └───────┬───────┘
                    │
              ┌─────┼─────┐
              │     │     │
              ▼     ▼     ▼
         ┌────────┐ │ ┌────────┐
         │Por tipo│ │ │Vencim. │
         │sangue  │ │ │próximo │
         └───┬────┘ │ └───┬────┘
             │      │     │
             │      ▼     ◇ Configurar
             │  ┌────────┐  alertas?
             │  │Por hemo│   ╱ ╲
             │  │compone.│ sim  não
             │  └───┬────┘  │    │
             │      │       ▼    │
             │      │ ┌──────────┐│
             │      │ │  Config  ││
             │      │ │ alertas  ││
             │      │ └────┬─────┘│
             │      │      │      │
             └──────┴──────┴──────┘
                       │
                       ○
```

---

## 3. Screen Layouts

### Dashboard Screen

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets       [Upload]  │
├────────────────────────────────────────┤
│ Estoque Atual          [ Atualizar ↻] │
│                                        │
│ POR TIPO SANGUÍNEO                     │
│ O/POS ████████████  24                 │
│ A/POS ██████████    20                 │
│ O/NEG ██████        12                 │
│ B/POS ████           8                 │
│ A/NEG ███            6                 │
│ AB/POS██             4                 │
│ B/NEG █              2                 │
│ AB/NEG               0                 │
│                           Total: 76    │
│                                        │
│ [ ⚠ 5 bolsas vencem em 7 dias ]      │
└────────────────────────────────────────┘
```
← Barras horizontais para comparação rápida entre tipos; alerta de vencimento como banner fixo no rodapé para visibilidade constante

### Dashboard Screen — Seção Vencimento

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets       [Upload]  │
├────────────────────────────────────────┤
│ Vencimento Próximo      [ Config ⚙ ] │
│                                        │
│ 🔴 Vencem em 7 dias (5 bolsas)        │
│  25051087  CHD  O/POS  292ml  02/03   │
│  25009258  CHD  A/POS  273ml  02/03   │
│  25053572  CHD  A/POS  300ml  04/03   │
│  25012667  CHD  O/NEG  299ml  05/03   │
│  25014403  CHD  O/NEG  287ml  06/03   │
│                                        │
│ 🟡 Vencem em 14 dias (8 bolsas)       │
│  25014485  CHD  O/NEG  276ml  09/03   │
│  25019832  PFC  O/POS  268ml  11/03   │
│  ... +6 mais                       [▼] │
│                                        │
└────────────────────────────────────────┘
```
← Urgência por cor (vermelho 7d, amarelo 14d); lista expandível para não sobrecarregar; botão Config leva às configurações de alerta

### Alert Settings Screen

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets   [← Dashboard]│
├────────────────────────────────────────┤
│ Configuração de Alertas                │
│                                        │
│ Prazos de alerta:                      │
│ ┌──────────────────────────────────┐   │
│ │ 🔴 Urgente:  [ 7  ▼] dias       │   │
│ │ 🟡 Atenção:  [ 14 ▼] dias       │   │
│ └──────────────────────────────────┘   │
│                                        │
│ Notificações:                          │
│ ┌──────────────────────────────────┐   │
│ │ [✓] Alerta no app (ao abrir)    │   │
│ │ [✓] Email diário                │   │
│ │     Para: [ana@hmob.mg.gov  ]   │   │
│ └──────────────────────────────────┘   │
│               [ SALVAR ]               │
└────────────────────────────────────────┘
```
← Configuração simples: dois thresholds + canal de notificação; email como padrão por ser universalmente acessível no ambiente hospitalar

---

## 4. Legend

```
◇ Configurar alertas? : sim → tela de config; não → permanece no dashboard
🔴 = urgente (vence em ≤ 7 dias)
🟡 = atenção (vence em ≤ 14 dias)
```
