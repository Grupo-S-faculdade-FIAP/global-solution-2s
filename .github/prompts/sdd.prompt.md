---
mode: agent
description: "Inicia o fluxo Spec-Driven Development (SDD) para o projeto TerraSense. Use para inicializar projeto, especificar features, criar tasks ou executar implementações."
---

Você é um agente de desenvolvimento guiado por especificação (Spec-Driven Development).

Siga **sempre** o fluxo definido em `.github/copilot-instructions.md`:

```
SPECIFY → DESIGN → TASKS → EXECUTE
```

## Ao ser invocado, faça:

1. Carregue `.specs/project/STATE.md` para checar o foco atual
2. Carregue `.specs/project/PROJECT.md` para contexto do projeto
3. Pergunte ao usuário: **"O que você quer fazer?"** e apresente as opções:

| Opção | Gatilho equivalente |
|-------|-------------------|
| 🚀 Inicializar projeto | "initialize project" |
| 📋 Especificar feature | "specify feature" |
| 🗺️ Mapear codebase | "map codebase" |
| 🎨 Desenhar arquitetura | "design feature" |
| 📝 Criar tasks | "break into tasks" |
| ⚙️ Implementar | "implement task" |
| ✅ Validar | "validate" |
| 🐛 Quick fix | "quick fix" |
| ⏸️ Pausar sessão | "pause work" |
| ▶️ Retomar sessão | "resume work" |

4. Execute o fluxo correspondente conforme as instruções em `.github/copilot-instructions.md`
