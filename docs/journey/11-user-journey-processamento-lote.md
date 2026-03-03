# User Journey: Processamento em Lote (Phase 3)

**Covers feature:** 11 (Processamento em Lote)

---

## 1. Goal → Screen Mapping

```
GOAL                                    SCREEN
──────────────────────────────────────────────────────────
Upload de múltiplos PDFs                Batch Upload Screen
Ver status de cada PDF                  Batch Upload Screen
Revisar dados consolidados              Batch Preview Screen
Ver resumo final                        Batch Success Screen
```

---

## 2. Journey Diagram

```
                    ●
                    │
            ┌───────┴───────┐
            │ Upload lote   │
            │ (N arquivos)  │
            └───────┬───────┘
                    │
            ┌───────┴───────┐
            │ Processando   │
            │ 1/N, 2/N...  │
            └───────┬───────┘
                    │
                    ◇ Todos OK?
                   ╱ ╲
                 não  sim
                  │    │
                  ▼    ▼
            ┌──────────┐  ┌──────────────┐
            │ X erros  │  │  Preview     │
            │ revisar  │  │  consolidado │
            └────┬─────┘  └──────┬───────┘
                 │               │
                 ▼               │
            ┌──────────┐        │
            │ Preview  │        │
            │ parcial  │        │
            └────┬─────┘        │
                 │              │
                 └──────┬───────┘
                        │
                  ┌─────┴─────┐
                  │  Enviar   │
                  └─────┬─────┘
                        │
                  ┌─────┴─────┐
                  │  Resumo   │
                  │  final    │
                  └─────┬─────┘
                        │
                        ○
```

---

## 3. Screen Layouts

### Batch Upload Screen

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets     [Histórico] │
├────────────────────────────────────────┤
│                                        │
│   ┌────────────────────────────────┐   │
│   │  Arraste PDFs aqui             │   │
│   │  ou [ Selecionar arquivos ]    │   │
│   └────────────────────────────────┘   │
│                                        │
│   📄 RECEBIM-15_12.pdf     452KB  ✕   │
│   📄 RECEBIM-20_12.pdf     318KB  ✕   │
│   📄 RECEBIM-02_01.pdf     521KB  ✕   │
│                                        │
│   3 arquivos selecionados              │
│                                        │
│   [ PROCESSAR TODOS ]                  │
│                                        │
└────────────────────────────────────────┘
```
← Mesma drop-zone da Phase 1 mas aceitando múltiplos; lista de arquivos com remoção individual antes de processar

### Batch Processing Screen

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets     [Histórico] │
├────────────────────────────────────────┤
│  Processando 3 arquivos...             │
│                                        │
│  ✓ RECEBIM-15_12.pdf                   │
│    2 comprovantes · 6 bolsas           │
│                                        │
│  ◌ RECEBIM-20_12.pdf                   │
│    Extraindo dados...                  │
│                                        │
│  ○ RECEBIM-02_01.pdf                   │
│    Aguardando...                       │
│                                        │
│  ████████████░░░░░░░░  2/3             │
│                                        │
│                     [ Cancelar ]       │
└────────────────────────────────────────┘
```
← Status individual por arquivo permite identificar qual falhou sem parar o lote inteiro

### Batch Success Screen

```
┌────────────────────────────────────────┐
│ 🩸 Hemominas → Sheets     [Histórico] │
├────────────────────────────────────────┤
│                                        │
│          ✓ Lote concluído!             │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │ 3 arquivos processados           │  │
│  │ 5 comprovantes lidos             │  │
│  │ 14 bolsas importadas             │  │
│  │ 0 erros                          │  │
│  └──────────────────────────────────┘  │
│                                        │
│  [ Abrir planilha ]  [ Novo lote ]     │
│                                        │
│                                        │
└────────────────────────────────────────┘
```
← Resumo em números grandes e claros; duas ações: verificar resultado ou começar de novo

---

## 4. Legend

```
◇ Todos OK? : sim → preview consolidado; não → lista erros por arquivo + preview parcial dos que passaram
✓ = arquivo processado com sucesso
◌ = processando agora
○ = na fila
```
