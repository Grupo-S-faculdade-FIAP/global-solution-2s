# Convenções — Global Solutions

**Atualizado:** 2026-06-06

## Frontend (dashboard)

Stack: **vanilla JS (ES modules)** + **Jinja partials** + **CSS tokens** + **BFF Flask/FastAPI** em `/api/*`.

### Estrutura de pastas

```
src/dashboard/static/js/
├── app.js              # entry + wiring de eventos (theme, orchestrator)
├── bootstrap.js        # carga inicial paralela (Promise.allSettled)
├── theme.js            # tema claro/escuro
├── charts.js           # Chart.js (render + refresh)
├── core/
│   ├── api.js          # fetchApi (transporte: timeout, retry)
│   ├── api/endpoints.js # contratos HTTP por domínio
│   ├── constants.js    # valores imutáveis (LOC_KEY, BRAZIL_CITIES, …)
│   ├── state.js        # estado mutável + runtime handles (maps, charts)
│   ├── events.js       # pub/sub (on/emit)
│   ├── orchestrator.js # orquestração multi-módulo
│   ├── selectors.js    # IDs compartilhados (SEL.*)
│   ├── dom.js          # helpers DOM (loading, erros)
│   ├── ui.js           # toasts, chip demo/live, safeLoad
│   └── css.js          # leitura de CSS variables
├── maps/               # Leaflet, Windy, localização
└── sections/           # features por seção do dashboard
```

### Regra de dependência

| Camada | Pode importar | Não pode importar |
|--------|---------------|-------------------|
| `core/*` (exceto orchestrator) | `core/*` | `sections/`, `maps/` |
| `core/orchestrator.js` | `core/`, `sections/`, `maps/` | — (camada de wiring) |
| `sections/` | `core/`, `charts.js` | outras `sections/`, `maps/` |
| `maps/` | `core/` | `sections/` |
| `app.js`, `bootstrap.js` | tudo | — |

Comunicação entre camadas paralelas: **`core/events.js`**, nunca import cruzado.

### Eventos canônicos

| Evento | Emissor | Handler |
|--------|---------|---------|
| `location:changed` | `maps/location.js` | `orchestrator` → weather, risk, region map, Windy |
| `weather:loaded` | `sections/climate.js` | `orchestrator` → `ml.syncSlidersFromWeather` |
| `theme:changed` | `theme.js` | `app.js` → charts + map tiles + Windy |
| `dashboard:reload` | `sections/yolo.js` | `orchestrator` → KPIs, gráficos, region map |

### Padrão por section

Cada `sections/*.js` expõe:

- `load*()` — busca via `core/api/endpoints.js` e renderiza a seção
- `bind*()` (opcional) — event listeners locais

Toda `load*()` segue:

1. Limpar erro / loading
2. Chamar endpoint do BFF
3. Renderizar ou fallback `—`
4. `noteResponseSource(r)` quando aplicável

### HTML e CSS

- Markup estrutural nos partials Jinja (`templates/partials/`)
- JS atualiza texto/classes; injeta HTML só para erros dinâmicos
- Cores via `css/tokens.css` (`var(--blue)`, etc.)
- Classes: bloco (`.kpi-card`), estado (`.is-loading`, `.has-error`)
- Não estilizar por ID no CSS

### API

- Browser fala **somente** com `/api/*` (BFF)
- Paths centralizados em `core/api/endpoints.js`
- Header `X-Data-Source`: `live` | `demo` | `unavailable`

### Terceiros

- Chart.js e Leaflet: globals UMD; guard `typeof Chart === "undefined"`
- Windy: isolado em `maps/windy.js`
- Lazy load: Windy e mapa da região via IntersectionObserver
