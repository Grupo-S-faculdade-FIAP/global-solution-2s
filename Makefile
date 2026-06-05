.PHONY: install demo test test-api test-storms nasa-capture upload-s3 smoke-aws train-ml fetch-inmet train-ml-inmet export-faostat export-faostat-offline train-yolo build-agri build-agri-ci verify-agri-models

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

# Suite com cobertura mínima de 82% (meta +20% sobre baseline ~62%)
test-coverage:
	cd src && PYTHONPATH=. ../$(VENV_PYTHON) -m pytest ../tests/ tests/ -q \
		--cov=app --cov-config=../.coveragerc --cov-report=term-missing --cov-fail-under=82

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

smoke-aws:
	$(VENV_PYTHON) scripts/smoke_aws_e2e.py

train-ml:
	$(VENV_PYTHON) scripts/train_agri_risk_openmeteo.py

fetch-inmet:
	$(VENV_PYTHON) scripts/fetch_inmet_bdmep.py --years 2024

train-ml-inmet:
	$(VENV_PYTHON) scripts/build_agri_pipeline.py --skip-faostat

export-faostat:
	$(VENV_PYTHON) scripts/export_faostat_brazil.py

export-faostat-offline:
	$(VENV_PYTHON) scripts/export_faostat_brazil.py --offline

# Pipeline completo: INMET + FAOSTAT + treino (duplo clique: build_dataset_agri.command)
build-agri:
	$(VENV_PYTHON) scripts/build_agri_pipeline.py

build-agri-ci:
	$(VENV_PYTHON) scripts/build_agri_pipeline.py --ci --skip-faostat

verify-agri-models:
	$(VENV_PYTHON) scripts/build_agri_pipeline.py --verify-only

train-yolo:
	$(VENV_PYTHON) src/yolo_training.py --epochs 40 --batch 8 --recall-focus --validate
