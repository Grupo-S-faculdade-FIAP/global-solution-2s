# Documentação GS2

Índice da documentação do projeto **global-solution-2s** (FIAP GS 2026.1).

| Documento | Público | Conteúdo |
|-----------|---------|----------|
| [RPI.md](RPI.md) | Tutor / equipe | Relatório de progresso e integração — status técnico formal |
| [GUIA-DE-AVALIACAO.md](GUIA-DE-AVALIACAO.md) | Tutor | Cobertura da rubrica FIAP (temas + responsáveis) |
| [PDF-ENTREGA-ESQUELETO.md](PDF-ENTREGA-ESQUELETO.md) | Equipe | Base para montar o PDF de entrega |
| [Global-Solutions-2-ENTREGA.pdf](Global-Solutions-2-ENTREGA.pdf) | Avaliador | **PDF de entrega FIAP** |
| [Vídeo demonstrativo](https://www.youtube.com/watch?v=W67760WVado) | Avaliador | Apresentação do projeto (≤ 5 min; link canônico também em [README.md](../README.md)) |
| [CI-CD.md](CI-CD.md) | DevOps | GitHub Actions, OIDC, jobs pytest + E2E + deploy Lambda |
| [DEPLOY-LAMBDA.md](DEPLOY-LAMBDA.md) | DevOps | Deploy manual da Lambda `gs2-api` |
| [dados/FAOSTAT_BR_contexto.md](dados/FAOSTAT_BR_contexto.md) | PDF / contexto | Dados agrícolas Brasil (FAOSTAT) para seção de resultados |

**Specs internas:** `.specs/project/` (PROJECT, STATE, ROADMAP, CHECKLIST) · `.specs/codebase/` (arquitetura, testes, stack)

**Auditoria docs (concluída):** `.specs/features/docs-refresh/spec.md` + limpeza 08/06 — métricas canônicas: 440 testes, 82,44% cov, 53 E2E, dataset YOLO 1.361→3.045 tiled, YOLO mAP@0.5 56,5% (P=73,5% em conf=0,55), rótulos proxy documentados (RPI §8.2)

**Wiki AWS (time):** https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s/wiki/AWS%E2%80%90STATE
