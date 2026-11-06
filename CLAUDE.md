# Document AI Factory

Projeto de hackathon (7 horas). Recebe PDFs de lote com muitas páginas escaneadas, separa cada documento, classifica por tipo, gera OCR pesquisável e manda casos duvidosos para revisão humana.

**Prioridade: fluxo ponta a ponta funcionando antes de qualquer refinamento. Sem over-engineering.**

## Como trabalhamos

- **Supervisão e implementação:** a sessão principal (Opus) só planeja, delega e revisa. A implementação é feita por subagents com `model: sonnet`, um por etapa, em worktree próprio.
- **PRs pequenos:** um PR por entrega, contra `master`. Cada commit tem no máximo ~800 linhas alteradas. Se passar disso, divida. Arquivos gerados e lockfiles não entram nessa conta.
- **Nunca commitar direto na `master`.** Crie uma branch `feat/...`, `fix/...` ou `chore/...`.
- **Sem assinatura nos commits:** não adicione `Co-Authored-By` nem outra linha de atribuição.
- **Não use o agent `gcp`.**
- **Rode de verdade:** nada está pronto sem ter sido executado (`docker compose up`, processar um lote, rodar a avaliação). Mostre a saída real.
- **Pergunte em vez de assumir:** se algo for ambíguo ou depender de informação que você não tem, pare e reporte. Subagents devolvem a dúvida à sessão principal.
- **Não invente métricas:** todo número no README vem de um script que foi rodado.
- **Nunca commite segredos:** chaves ficam em `.env`, que está no `.gitignore`. Mantenha `.env.example` atualizado, sem valores.

### Se estiver atrasado, corte nesta ordem

1. UI Streamlit
2. Correção de fronteiras
3. PDF pesquisável (mantendo a busca por texto)
4. Gemini

Nunca corte o fluxo ponta a ponta nem a avaliação.

## Stack e arquitetura (decidido, não rediscuta)

- Python 3.12, FastAPI, PostgreSQL 16, Redis 7, Docker Compose.
- Serviços: `api` (FastAPI), `worker_ocr_seg` (OCR + segmentação), `worker_classify` (classificação), `ui` (Streamlit, opcional, por último).
- Arquivos em volume local (`/data/lote_<id>/`). Sem S3/MinIO.
- Tudo idempotente: reprocessar um lote ou documento não pode duplicar nem corromper dados.

### Filas (Redis, listas, com ack)

- `BLMOVE fila -> fila:proc`. Remover de `:proc` só após sucesso.
- Retry 3x, depois `dlq`.
- Ao subir, o worker devolve para a fila os jobs presos em `:proc`.
- `segmentar_lote`, payload `{lote_id}`.
- `classificar_documento`, payload `{documento_id}`.

### Fan-in

Coluna `lote.docs_pendentes`, decrementada atomicamente (`UPDATE ... RETURNING`). Em 0, o lote vira `concluido`.

### Estados

- Lote: `recebido`, `ocr`, `classificando`, `concluido`, `erro`.
- Documento: `segmentado`, `classificado`, `em_revisao`, `revisado`, `erro`.

### Tipos documentais

`aso`, `folha_pagamento`, `folha_ponto`, `holerite`, `recibo_ferias`, `atestado_medico`, `contrato_trabalho`.

A lista fica em configuração, em um único lugar, nunca espalhada pelo código.

## Modelos de IA

- **Jev:** classificador principal, só texto, via OpenRouter (`OPENROUTER_API_KEY`, `JEV_MODEL`). Devolve escolha, confiança e probabilidades por opção. **Antes de implementar, faça uma chamada de teste e confirme o formato real da resposta.** Se não houver confiança utilizável, avise e proponha alternativa em vez de inventar.
- **Gemini:** segunda opinião (Google AI Studio, `GEMINI_API_KEY`), com a imagem da primeira página, usado só quando a confiança do Jev for baixa. A confiança autodeclarada do Gemini **não** entra na regra de decisão.
- **Gemini na análise de folha de ponto (Goal 6):** modelo em `GEMINI_ANALISE_MODEL`, padrão `gemini-3.5-flash`. A documentação do Gemini indica esse ID como obsoleto e redirecionado para um modelo mais novo, então registre o modelo realmente devolvido pela API.
- **Jev no score de risco (Goal 6):** usa o tipo `Score` do Jev. Confirme o formato real da resposta em uma chamada de teste, como no classificador.
- Toda decisão de confiança (limiares, roteamento) é feita em código determinístico, não pelo LLM.
- Cache em disco das respostas dos LLMs, com chave = hash da entrada + modelo + prompt, para a demo não depender de rede.
- Em cada classificação, guarde o modelo usado, a versão do prompt e as probabilidades.

## Dados de teste

Gerador de lotes sintéticos: `gerar_lotes.py`, com gabarito `anotacoes.csv` (`lote_id,pagina,inicio_documento,documento_id,tipo,qualidade,observacao`). Verso em branco pertence ao documento anterior (observação `verso_em_branco`).

**Se o gerador não estiver no repositório, peça o caminho. Não o reescreva.**

Os dados sintéticos são otimistas. O README deve registrar que a validação em documentos reais ainda é necessária.

## Ordem de execução

1. Fundação: `docker-compose`, schema SQL, módulo de filas Redis, endpoint de upload. Validar com `docker compose up` e um PDF de teste.
2. Goal 4 (OCR) e Goal 1 (segmentação com regras e TF-IDF), ponta a ponta, sem LLM.
3. Goal 3 com um classificador simples para fechar o fluxo, depois trocar por Jev + Gemini.
4. Goal 5 (roteamento e revisão) e script de avaliação com números reais.
5. Goal 6 (análise de risco das folhas de ponto).
6. Goal 2 (refinamentos de agrupamento/correção) e UI Streamlit.
7. README com como rodar, arquitetura, resultados medidos e limitações.

## Goals

### Goal 1: Detecção de início e fim de cada documento

Segmentação em cascata:

1. Regras determinísticas: página em branco herda o documento anterior; "Página 1 de N" abre documento; "Página k de N" (k>1) continua.
2. Similaridade TF-IDF entre páginas consecutivas: abaixo de um limiar baixo abre documento novo; acima de um limiar alto continua.
3. Faixa ambígua entre os limiares: pergunta Sim/Não ao LLM ("estas duas páginas pertencem ao mesmo documento?"), enviando o fim da página anterior e o início da atual.
4. Reconciliação final: nenhuma página fica sem documento e os intervalos não se sobrepõem.

**Aceite:** script de avaliação que compara com `anotacoes.csv` e imprime, por documento (não por página), precisão e recall das fronteiras e a taxa de documentos exatos (início e fim corretos). Documentos consecutivos do mesmo tipo precisam estar nos testes.

### Goal 2: Agrupamento de páginas

- Persistir `documento` (lote, ordem, `pagina_ini`, `pagina_fim`) e vincular cada `pagina` ao seu `documento_id`.
- `GET /documentos/{id}`: páginas (imagem + texto), tipo, confiança e status.
- `GET /lotes/{id}`: lista de documentos do lote.
- Corrigir fronteiras na revisão: juntar com o anterior e dividir em uma página, recalculando os intervalos (mínimo viável, se sobrar tempo).

**Aceite:** após processar um lote, é possível abrir cada documento pela API e ver exatamente suas páginas na ordem.

### Goal 3: Classificação por tipo documental

- `worker_classify` consome `classificar_documento`, monta o texto (primeiras páginas, truncado em ~6000 caracteres), chama o Jev e devolve tipo, confiança e probabilidades.
- Confiança abaixo do limiar alto: chama o Gemini com a imagem da primeira página. Se discordarem, vai para revisão.
- Ao final, faz o fan-in do lote.
- Baseline obrigatório: TF-IDF + regressão logística sobre o texto do OCR, treinado nos lotes sintéticos. Reportar lado a lado com o Jev.

**Aceite:** F1 macro e matriz de confusão por tipo, medidos por documento, sobre lotes sintéticos que **não** foram usados para ajustar prompt ou limiares.

### Goal 4: OCR pesquisável

- Rasterizar com `pdf2image` a 150 dpi, OCR com Tesseract (`-l por`), páginas em paralelo.
- Salvar o texto por página no banco.
- Gerar um PDF pesquisável por documento (OCRmyPDF ou camada de texto sobre a imagem). Se não der tempo, entregar a busca no banco e registrar isso claramente.
- `GET /busca?q=`: full-text search do PostgreSQL (configuração `portuguese`), retornando lote, página e trecho destacado.

**Aceite:** buscar uma palavra presente num documento (ex.: nome de um funcionário) retorna a página correta.

### Goal 5: Confiança e fila de revisão humana

Roteamento em código, com limiares em variáveis de ambiente (`CONF_AUTO`, `CONF_MIN`):

- Confiança >= `CONF_AUTO` e sem desacordo entre modelos: `classificado`.
- Entre `CONF_MIN` e `CONF_AUTO`, ou desacordo: `em_revisao` com o tipo sugerido.
- Abaixo de `CONF_MIN`: `em_revisao` com tipo `desconhecido`.
- Segmentação ambígua também pode marcar o documento para revisão.

Demais entregas:

- `GET /revisao` (fila) e `POST /documentos/{id}/revisao` (corrige o tipo; guarda `tipo_original`, revisor e momento).
- Streamlit mínimo: upload de lote, lista de documentos por lote e tela de revisão com a página, o tipo sugerido e um seletor para confirmar ou corrigir.
- Escolher os limiares pela curva cobertura x precisão nos dados de validação e reportar % automático, precisão na parte automática e % em revisão.

**Aceite:** documentos de baixa confiança aparecem na fila, a correção humana muda o status para `revisado` e o relatório de cobertura x precisão é gerado por script.

### Goal 6: Análise de risco das folhas de ponto

Para documentos do tipo `folha_ponto`, encontrar divergências, com foco principal em horas extras, e gerar um score de risco com base na CLT e na Portaria MTP nº 671/2021.

**Perfil padrão:** tabela `perfil_jornada`, criada com um perfil CLT de referência. Cada parâmetro guarda o valor e a base legal. Confira os valores no texto oficial da CLT e da Portaria antes de usar:

| Parâmetro | Referência |
|---|---|
| Jornada diária de 8h e semanal de 44h | CF art. 7º, XIII; CLT art. 58 |
| Tolerância de 5 min por marcação, até 10 min por dia | CLT art. 58, § 1º |
| Até 2h extras por dia | CLT art. 59 |
| Adicional mínimo de 50% sobre a hora extra | CF art. 7º, XVI |
| Intervalo interjornada de 11h | CLT art. 66 |
| Descanso semanal de 24h | CLT art. 67 |
| Intervalo intrajornada: 1h acima de 6h de jornada; 15 min entre 4h e 6h | CLT art. 71 |
| Noturno das 22h às 5h, adicional de 20%, hora de 52min30s | CLT art. 73 |
| Requisitos do registro de ponto e do espelho | CLT art. 74; Portaria MTP 671/2021 |

**Fluxo:**

1. Documento que termina como `folha_ponto`, inclusive por correção humana, entra na fila `analisar_folha_ponto` (payload `{documento_id}`), consumida pelo serviço `worker_analise`. A análise não participa do fan-in do lote.
2. O Gemini recebe o texto do OCR e o perfil padrão e devolve em JSON as divergências (tipo, data, minutos, base legal, trecho de evidência) e uma análise breve.
3. O Jev recebe a análise e as divergências e devolve o score de risco com as probabilidades por nível.
4. Persistir em `analise_ponto`, uma linha por documento (reprocessar substitui, sem duplicar): perfil usado, divergências, análise, score, probabilidades, modelos e versões dos prompts.
5. `GET /documentos/{id}/analise-ponto` devolve o resultado.

O score é apoio à auditoria, não parecer jurídico. A convenção coletiva e o acordo de compensação podem alterar os limites do perfil padrão. O README deve registrar as duas ressalvas.

**Aceite:** uma folha de ponto com horas extras acima do limite gera divergências com data, minutos e base legal, além do score; uma folha regular gera score menor. Não reporte métrica de acurácia sem um gabarito de divergências.
