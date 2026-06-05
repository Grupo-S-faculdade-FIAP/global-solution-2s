.PHONY: install demo test test-api test-storms nasa-capture upload-s3

VENV_PYTHON := .venv/bin/python

install:
	cd src && $(VENV_PYTHON) -m pip install -r requirements.txt

# API + dashboard na mesma porta (8000) — requer best.pt em src/models/weights/
demo:
	@test -x $(VENV_PYTHON) || (echo "Crie o venv: python3 -m venv .venv && $(VENV_PYTHON) -m pip install -r src/requirements.txt" && exit 1)
	@echo "Iniciando API + dashboard em http://127.0.0.1:8000"
	cd src && ../$(VENV_PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Suite completa (mesmo comando do CI)
test:
	cd src && PYTHONPATH=. ../$(VENV_PYTHON) -m pytest ../tests/ tests/ -q

test-api:
	cd src && PYTHONPATH=. ../$(VENV_PYTHON) -m pytest ../tests/test_api_endpoints.py -q

test-storms:
	cd src && PYTHONPATH=. ../$(VENV_PYTHON) -m pytest ../tests/test_storm_alerts_query.py -q

# Captura NASA Worldview + upload S3 (requer playwright: playwright install chromium)
nasa-capture:
	cd src && ../$(VENV_PYTHON) -m app.cron.capture_nasa_data

# Upload capturas locais existentes para S3 (opcional: UPLOAD_CV=1 para JPG + YOLO)
upload-s3:
	cd src && ../$(VENV_PYTHON) -m app.cron.upload_nasa_to_s3 $(if $(UPLOAD_CV),--cv,)
