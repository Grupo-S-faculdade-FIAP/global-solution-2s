# Conventions

**Project:** global-solution-2s
**Mapped on:** 2026-06-04

Estas convencoes foram observadas no codigo atual e devem ser seguidas em novas alteracoes.

---

## Naming

| Entity | Convention | Example |
|--------|-----------|---------|
| Arquivos Python | snake_case | `risk_assessment.py`, `ingest_weather.py` |
| Funcoes e variaveis | snake_case | `process_s3_image`, `validate_coordinates` |
| Classes | PascalCase | `WeatherService`, `AgriRiskModel` |
| Constantes | UPPER_SNAKE_CASE | `MODEL_PATH`, `YOLO_CONFIDENCE_THRESHOLD` |
| Rotas HTTP | kebab-case e prefixadas por modulo | `/predict/agricultural-risk`, `/storms/recent` |

---

## File Organization

```text
src/
├── app/
│   ├── core/       # configuracao e fundamentos
│   ├── models/     # schemas pydantic
│   ├── routers/    # endpoints por dominio
│   ├── services/   # regras de negocio
│   ├── clients/    # clientes externos
│   ├── lambdas/    # handlers agendados/event-driven
│   └── main.py     # app FastAPI + entrypoint Lambda
├── dashboard/      # app Flask para visualizacao
├── models/         # artefatos de modelo (weights e pkl)
└── tests/          # testes locais da camada src
```

---

## Code Style

- Linguagem principal: Python com type hints.
- Imports em blocos: stdlib -> terceiros -> app local.
- Logging por modulo com `logging.getLogger(__name__)`.
- Validacao de entrada HTTP com Query constraints e Pydantic.
- Configuracao via `BaseSettings` em `app/core/config.py`.

---

## Patterns

### Error Handling

```python
try:
	# chamada de servico externo ou inferencia
	...
except Exception as e:
	raise HTTPException(status_code=500, detail=str(e))
```

### API Responses

```python
# Rotas usam response_model quando aplicavel
@router.get("/weather/current", response_model=WeatherResponse)
def get_weather_current(...):
	return WeatherResponse(...)
```

### Async / Sync

```python
# Ha mistura de handlers sync e async
@router.get("/status")
def status(): ...

@router.post("/detect/storm")
async def detect_storm(...): ...
```

### Imports on-demand

```python
# Em alguns endpoints, imports de servicos sao feitos dentro da funcao
from app.services.agri_risk_model import AgriRiskModel
```

---

## Prohibited Patterns

- Nao hardcodar segredos e ARNs; usar `.env` + settings.
- Nao colocar regra de negocio complexa diretamente em router.
- Nao commitar artefatos temporarios, caches e credenciais.
- Evitar testes que dependem de internet sem fallback de mock.

---

## Git Conventions

Conforme `.github/copilot-instructions.md`:

- Conventional Commits: `<type>(<scope>): <description>`
- Tipos aceitos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`
- Um commit por unidade atomica de trabalho
