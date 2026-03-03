# Product Roadmap — PDF-to-Sheets: Banco de Sangue

## Feature Inventory

> Mapeamento completo de todas as features identificadas a partir do input.

| # | Input Feature | Output Feature Name | Phase |
|---|---------------|---------------------|-------|
| 1 | Upload/input do PDF | Upload de PDF | 1 |
| 2 | Parsing/extração de dados do PDF (tabela de hemocomponentes) | Extração de Dados do PDF | 1 |
| 3 | Mapeamento de campos PDF → colunas da planilha | Mapeamento de Campos PDF→Planilha | 1 |
| 4 | Conversão ABO+Rh do PDF para formato GS/RH da planilha (ex: "O"+"P" → "O/POS") | Conversão GS/RH | 1 |
| 5 | Conversão do nome curto do componente (PDF) para nome completo do hemocomponente (planilha) | Mapeamento de Hemocomponentes | 1 |
| 6 | Geração da DATA ENTRADA a partir da data de emissão/recebimento do PDF | Extração de Data de Entrada | 1 |
| 7 | Preenchimento automático da DATA VALIDADE a partir do campo Validade do PDF | Extração de Data de Validade | 1 |
| 8 | Extração do Nº Doação como Nº DA BOLSA | Extração de Nº da Bolsa | 1 |
| 9 | Extração do Volume (ML) | Extração de Volume | 1 |
| 10 | Tratamento de múltiplas páginas/comprovantes no mesmo PDF | Suporte Multi-Página | 1 |
| 11 | Escrita dos dados na Google Sheets (MAPA DE TRANSFUSÃO) | Integração Google Sheets | 1 |
| 12 | Cálculo automático de DIAS ANTES DO VENCIMENTO e STATUS | Campos Calculados (Status/Vencimento) | 2 |
| 13 | Validação dos dados extraídos contra listas da aba BASE (GS/RH, Hemocomponentes, etc.) | Validação contra BASE | 2 |
| 14 | Extração do nome do RESPONSÁVEL RECEPÇÃO do PDF | Extração de Responsável | 2 |
| 15 | Tela de revisão/confirmação antes de enviar para a planilha | Preview e Confirmação | 2 |
| 16 | Detecção de duplicatas (bolsas já cadastradas na planilha) | Detecção de Duplicatas | 2 |
| 17 | Processamento em lote (múltiplos PDFs de uma vez) | Processamento em Lote | 3 |
| 18 | Histórico de importações realizadas | Histórico de Importações | 3 |
| 19 | Dashboard de estoque atual (bolsas por tipo, vencimento próximo) | Dashboard de Estoque | 3 |
| 20 | Notificações de bolsas próximas do vencimento | Alertas de Vencimento | 3 |

**Input feature count:** 20
**Output feature count:** 20 ✓

---

### Core Use Case

Um profissional do banco de sangue do HMOB faz upload de um PDF de "Comprovante de Expedição" da Hemominas e os dados das bolsas de sangue são automaticamente extraídos e inseridos na planilha "MAPA DE TRANSFUSÃO" do Google Sheets, eliminando a digitação manual.

---

## Contexto Técnico

### Campos do PDF (Comprovante de Expedição - Hemominas)

**Cabeçalho:**
- Nº do comprovante, Data de emissão
- Instituição solicitante, Responsável, Documento

**Tabela de produtos (por linha/bolsa):**
- Inst. Coleta (ex: B3013)
- Nº Doação (ex: 25051087)
- Componente (ex: "CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado")
- Cod. ISBT 128 (ex: E6514V00)
- Seq.
- Vol. (ex: 292)
- ABO (ex: O, A, B, AB)
- Rh (ex: P=Positivo, N=Negativo)
- Validade (ex: 08/01/2026)

**Rodapé:**
- Total de Volume(s), Total de bolsa(s) expedida(s)
- Expedido por, Recebido por, datas, temperaturas

### Colunas da Planilha (MAPA DE TRANSFUSÃO)

| Coluna | Campo | Origem |
|--------|-------|--------|
| A | DIAS ANTES DO VENCIMENTO | Calculado (D - hoje) |
| B | STATUS | Calculado (baseado em A) |
| C | DATA ENTRADA | PDF: data recebimento |
| D | DATA VALIDADE | PDF: Validade |
| E | DATA TRANSFUSAO/DESTINO | Preenchido depois (manual) |
| F | DESTINO | Preenchido depois (manual) |
| G | NOME COMPLETO DO PACIENTE | Preenchido depois (manual) |
| H | TIPO DE HEMOCOMPONENTE | PDF: Componente → mapeado para nome completo |
| I | GS/RH | PDF: ABO + Rh → formato "O/POS" |
| J | VOLUME (ML) | PDF: Vol. |
| K | RESPONSÁVEL RECEPÇÃO | PDF: Recebido por / Expedido por |
| L | SETOR DA TRANSFUSAO | Preenchido depois (manual) |
| M | Nº DA BOLSA | PDF: Nº Doação |
| N-S | Prontuários, SUS, Reação, etc. | Preenchido depois (manual) |

### Mapeamento GS/RH

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

---

## Phase 1 — MVP

> Entregar isto. Validar que o fluxo de extração PDF → planilha funciona corretamente e elimina a digitação manual.

### Feature: Upload de PDF
O usuário faz upload de um arquivo PDF de "Comprovante de Expedição" da Hemominas. Este é o ponto de entrada único da aplicação — sem ele, não há dados para processar.

### Feature: Extração de Dados do PDF
A aplicação lê o PDF e extrai a tabela de hemocomponentes (Inst. Coleta, Nº Doação, Componente, Cod. ISBT, Seq., Vol., ABO, Rh, Validade). Esta é a etapa técnica central que viabiliza toda a automação.

### Feature: Mapeamento de Campos PDF→Planilha
Os campos extraídos do PDF são mapeados para as colunas correspondentes da planilha MAPA DE TRANSFUSÃO (C, D, H, I, J, K, M). Sem este mapeamento, os dados não têm destino.

### Feature: Conversão GS/RH
Converte os campos ABO (O, A, B, AB) e Rh (P, N) do PDF para o formato da planilha (ex: "O/POS", "A/NEG"). A planilha usa um formato diferente do PDF, então a conversão é obrigatória.

### Feature: Mapeamento de Hemocomponentes
Converte o nome curto do componente no PDF (ex: "CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado") para o nome padronizado da planilha (ex: "CHD - Concentrado de Hemácias Desleucocitado"). A aba BASE contém a lista de referência.

### Feature: Extração de Data de Entrada
Extrai a data de recebimento do comprovante para preencher a coluna DATA ENTRADA (C). Campo essencial para o rastreamento cronológico das bolsas.

### Feature: Extração de Data de Validade
Extrai a data de validade de cada bolsa da tabela do PDF para preencher a coluna DATA VALIDADE (D). Fundamental para controle de vencimento.

### Feature: Extração de Nº da Bolsa
Extrai o Nº Doação de cada linha da tabela do PDF para preencher a coluna Nº DA BOLSA (M). Identificador único de cada bolsa no sistema.

### Feature: Extração de Volume
Extrai o volume em ML de cada bolsa para preencher a coluna VOLUME (J). Dado obrigatório no registro.

### Feature: Suporte Multi-Página
O PDF pode conter múltiplas páginas, cada uma sendo um comprovante diferente com sua própria tabela de bolsas. Todas as páginas devem ser processadas em uma única operação.

### Feature: Integração Google Sheets
Os dados extraídos e mapeados são escritos diretamente na planilha Google Sheets "MAPA DE TRANSFUSÃO", adicionando novas linhas. Sem isto, o usuário ainda teria que copiar dados manualmente.

---

## Phase 2 — Enhance

> Construir após validação de que a extração e escrita funcionam. Melhorias baseadas no feedback da Phase 1.

### Feature: Campos Calculados (Status/Vencimento)
Preenche automaticamente DIAS ANTES DO VENCIMENTO (coluna A) e STATUS (coluna B) com base na data de validade. Atualmente estes campos são fórmulas na planilha — garantir que novas linhas os tenham.

### Feature: Validação contra BASE
Antes de escrever na planilha, valida os dados extraídos contra as listas da aba BASE (tipos de hemocomponente válidos, formatos GS/RH aceitos). Previne erros de dados inconsistentes.

### Feature: Extração de Responsável
Extrai o nome de quem expediu/recebeu as bolsas (campos "Expedido por" e "Recebido por" do PDF) para preencher RESPONSÁVEL RECEPÇÃO (K). Dado presente no PDF mas em área de texto livre/manuscrito.

### Feature: Preview e Confirmação
Após a extração, exibe uma tela de revisão mostrando todos os dados que serão inseridos na planilha, permitindo correções antes da escrita definitiva. Rede de segurança contra erros de extração.

### Feature: Detecção de Duplicatas
Antes de inserir, verifica se o Nº DA BOLSA já existe na planilha para evitar registros duplicados. Protege contra reimportação acidental do mesmo comprovante.

---

## Phase 3 — Grow

> Expandir para novas funcionalidades além do fluxo de entrada de bolsas.

### Feature: Processamento em Lote
Permite upload e processamento de múltiplos PDFs simultaneamente, útil quando há acúmulo de comprovantes para registrar. Acelera o fluxo em dias de alto volume.

### Feature: Histórico de Importações
Mantém um log de todos os PDFs processados, com data, quantidade de bolsas importadas e status. Permite auditoria e rastreabilidade do processo.

### Feature: Dashboard de Estoque
Visualização do estoque atual de bolsas por tipo sanguíneo, hemocomponente e proximidade do vencimento. Expande o uso da ferramenta de registro para gestão ativa do estoque.

### Feature: Alertas de Vencimento
Notificações automáticas quando bolsas estão próximas da data de vencimento (configurável: 7, 14, 30 dias). Novo caso de uso: prevenção de desperdício por vencimento.

---

## Completeness Verification

- [x] Every feature from the input appears in the Feature Inventory
- [x] Every feature in the Feature Inventory appears in a Phase section
- [x] Input count (20) = Output count (20)

---

*Each feature description above is input for the Product Specialist prompt.*
