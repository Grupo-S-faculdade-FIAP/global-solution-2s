.PHONY: install demo test-api test-storms

VENV_PYTHON := .venv/bin/python

install:
	cd src && $(VENV_PYTHON) -m pip install -r requirements.txt

# API + dashboard na mesma porta (8000) — requer best.pt em src/models/weights/
demo:
	@test -x $(VENV_PYTHON) || (echo "Crie o venv: python3 -m venv .venv && $(VENV_PYTHON) -m pip install -r src/requirements.txt" && exit 1)
	@echo "Iniciando API + dashboard em http://127.0.0.1:8000"
	cd src && ../$(VENV_PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8000

test-api:
	cd src && pytest ../tests/test_api_endpoints.py -q

test-storms:
	cd src && pytest ../tests/test_storm_alerts_query.py -q
