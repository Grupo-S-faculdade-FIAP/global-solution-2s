---
name: document-organization
description: Organiza documentacao, specs e artefatos de entrega do projeto FIAP Global Solutions. Use quando o usuario mencionar organizacao de documentos, limpeza de docs, README, specs, RPI, runbook, entrega FIAP ou revisao de documentacao do projeto.
---

# Document Organization

Use esta skill para criar, mover, revisar ou consolidar documentos do projeto FIAP Global Solutions em Portugues BR.

## Workflow

1. Classifique o documento
   - Determine se e material para avaliador FIAP, operacao, spec interna, memoria do projeto, dado/dataset, runbook/plano ou nota local de modulo.
   - Identifique a fonte canonica antes de copiar informacao: `.specs/project/STATE.md`, `.specs/project/PROJECT.md`, `README.md`, `docs/README.md`, `docs/RPI.md` e guias em `docs/`.

2. Escolha o destino
   - Use a matriz abaixo.
   - Nao crie Markdown novo na raiz sem justificativa clara de entrega ou navegacao.
   - Arquivos temporarios, planos executados e resumos de sessao devem ir para `.specs/quick/` ou para a feature correspondente.

3. Atualize indices e referencias
   - Se criar, mover ou remover docs publicos, revise `README.md` e `docs/README.md`.
   - Se mudar status, decisoes, blockers ou ideias futuras, atualize `.specs/project/STATE.md`.
   - Se mudar visao, metas, stack, escopo ou criterios de sucesso, atualize `.specs/project/PROJECT.md`.

4. Revise consistencia
   - Mantenha PT-BR, nomes tecnicos consistentes e links relativos funcionando.
   - Evite duplicacao longa: resuma e linke a fonte canonica.
   - Preserve `README.md` e `docs/` como caminho principal para o avaliador FIAP.

5. Verifique fatos antes de publicar
   - Nao repita contagem de testes, cobertura, endpoints, comandos, status AWS ou metricas YOLO sem verificar no codigo, Makefile, CI ou docs canonicos.
   - Nunca incluir secrets; use variaveis de ambiente e `.env.example` da raiz.
   - Registre decisoes ou melhorias fora de escopo em `STATE.md` quando necessario.

## Matriz De Destinos

| Destino | Use para |
| --- | --- |
| Raiz | `README.md`, planos/runbooks essenciais de entrega e documentos com justificativa forte para avaliador. |
| `docs/` | RPI, guia de avaliacao, deploy Lambda, CI/CD, YOLO, PDF de entrega e operacao publica. |
| `docs/dados/` | Fontes, datasets, amostras, preparacao e proveniencia de dados. |
| `.specs/project/` | Estado persistente, visao, roadmap, decisoes e memoria do projeto. |
| `.specs/features/` | Spec, design e tasks de features ativas ou arquivadas. |
| `.specs/quick/` | Tarefas pequenas, limpezas pontuais e resumos de execucao curta. |
| `src/*/README.md` | Orientacao local de modulo quando o codigo precisa de contexto proximo. |
