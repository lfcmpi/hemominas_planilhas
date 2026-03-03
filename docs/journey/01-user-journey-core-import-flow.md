# User Journey: Core Import Flow (Phase 1)

**Covers features:** 01 (Upload), 02 (Extração), 03 (Multi-Página), 04 (Mapeamento), 05 (Integração Google Sheets)

---

## 1. Goal → Screen Mapping

```
GOAL                                    SCREEN
──────────────────────────────────────────────────────────
Upload PDF do comprovante               Upload Screen
Ver feedback de formato inválido        Upload Screen
Ver progresso da extração               Processing Screen
Ver comprovantes encontrados            Processing Screen
Confirmar dados antes de enviar         Results Screen
Enviar dados para Google Sheets         Results Screen
Ver confirmação de sucesso              Success Screen
```

---

## 2. Journey Diagram

```
                    ●
                    │
            ┌───────┴───────┐
            │  Upload PDF   │
            │  (drag/drop)  │
            └───────┬───────┘
                    │
                    ◇ PDF válido?
                   ╱ ╲
                 não  sim
                  │    │
                  ▼    ▼
            ┌─────────┐  ┌──────────────┐
            │  Erro:  │  │  Processando │
            │ formato │  │  extração... │
            └────┬────┘  └──────┬───────┘
                 │              │
                 │              ◇ Extração OK?
                 │             ╱ ╲
                 │           não  sim
                 │            │    │
                 │            ▼    ▼
                 │      ┌─────────┐  ┌──────────────┐
                 │      │  Erro:  │  │  Resultados  │
                 │      │ formato │  │  X comprova. │
                 │      │ inválid │  │  Y bolsas    │
                 │      └────┬────┘  └──────┬───────┘
                 │           │              │
                 │◄──────────┘         ┌────┴────┐
                 │                     │ Enviar  │
                 │                     │ p/ Goog │
                 │                     │ Sheets  │
                 │                     └────┬────┘
                 │                          │
                 │                          ◇ Escrita OK?
                 │                         ╱ ╲
                 │                       não  sim
                 │                        │    │
                 │                        ▼    ▼
                 │                  ┌─────────┐  ┌──────────┐
                 │                  │  Erro   │  │ Sucesso! │
                 │                  │  API    │  │ N linhas │
                 │                  └────┬────┘  │ inseridas│
                 │                       │       └────┬─────┘
                 │◄──────────────────────┘            │
                 │                                    │
                 ▼                                    ▼
            ┌─────────┐                          ┌─────────┐
            │  Novo   │◄─────────────────────────│ Abrir   │
            │ upload  │                          │planilha │
            └────┬────┘                          └────┬────┘
                 │                                    │
                 ○                                    ○
```

---

## 3. Screen Layouts

### Upload Screen

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets         [Sobre] │
├────────────────────────────────────────┤
│                                        │
│   ┌────────────────────────────────┐   │
│   │                                │   │
│   │     Arraste o PDF aqui         │   │
│   │         ou                     │   │
│   │   [ Selecionar arquivo ]       │   │
│   │                                │   │
│   │     .pdf - até 10MB            │   │
│   └────────────────────────────────┘   │
│                                        │
│                                        │
│                                        │
│                                        │
└────────────────────────────────────────┘
```
← Drop-zone como elemento central e maior da tela; limite de formato e tamanho visível antes da ação para evitar erros

### Upload Screen (arquivo selecionado)

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets         [Sobre] │
├────────────────────────────────────────┤
│                                        │
│   ┌────────────────────────────────┐   │
│   │  📄 RECEBIMENTO-15_12.pdf     │   │
│   │     452 KB                     │   │
│   │                        [ ✕ ]   │   │
│   └────────────────────────────────┘   │
│                                        │
│   ┌────────────────────────────────┐   │
│   │        PROCESSAR               │   │
│   └────────────────────────────────┘   │
│                                        │
│                                        │
│                                        │
└────────────────────────────────────────┘
```
← Arquivo selecionado mostra nome e tamanho com opção de remover; botão Processar é a ação primária e aparece só após seleção

### Processing Screen

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets         [Sobre] │
├────────────────────────────────────────┤
│                                        │
│   Processando: RECEBIMENTO-15_12.pdf   │
│                                        │
│   ████████████░░░░░░░░  60%           │
│                                        │
│   ✓ PDF lido com sucesso               │
│   ✓ 2 comprovantes encontrados         │
│   ◌ Extraindo dados...                 │
│   ○ Mapeando campos                    │
│   ○ Convertendo tipos                  │
│                                        │
│                                        │
│                     [ Cancelar ]       │
│                                        │
└────────────────────────────────────────┘
```
← Progresso step-by-step mostra exatamente onde o sistema está; contagem de comprovantes dá confiança de que multi-página funciona

### Results Screen

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets         [Sobre] │
├────────────────────────────────────────┤
│  2 comprovantes · 6 bolsas extraídas  │
│                                        │
│  Comp  DATA ENT  VALIDADE  TIPO  GS   │
│  ─────────────────────────────────────│
│  #305  14/12/25  08/01/26  CHD   O/POS│
│  #305  14/12/25  08/01/26  CHD   A/POS│
│  #305  14/12/25  22/01/26  CHD   A/POS│
│  #305  14/12/25  20/01/26  CHD   O/NEG│
│  #305  14/12/25  22/01/26  CHD   O/NEG│
│  #307  14/12/25  23/01/26  CHD   O/NEG│
│                                    [▼] │
│                                        │
│  [ Cancelar ]   [ ENVIAR P/ PLANILHA ] │
│                                        │
└────────────────────────────────────────┘
```
← Tabela resume dados mapeados para conferência rápida; ação destrutiva (Cancelar) isolada à esquerda, ação primária (Enviar) à direita

### Success Screen

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets         [Sobre] │
├────────────────────────────────────────┤
│                                        │
│            ✓ Importação                │
│              concluída!                │
│                                        │
│   6 bolsas inseridas na planilha       │
│   MAPA DE TRANSFUSÃO                   │
│                                        │
│   ┌────────────────────────────────┐   │
│   │    Abrir planilha no Google    │   │
│   │          Sheets                │   │
│   └────────────────────────────────┘   │
│                                        │
│        [ Importar outro PDF ]          │
│                                        │
└────────────────────────────────────────┘
```
← Confirmação clara com contagem; link direto para planilha como ação primária; opção secundária para novo ciclo

---

## 4. Legend

```
◇ PDF válido?     : sim → extração; não → erro formato com opção de tentar outro arquivo
◇ Extração OK?    : sim → resultados; não → erro com descrição do problema
◇ Escrita OK?     : sim → sucesso; não → erro API com opção de retry
```
