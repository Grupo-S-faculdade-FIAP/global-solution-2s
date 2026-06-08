.PHONY: install demo test test-coverage test-e2e test-frontend test-api test-storms nasa-capture nasa-capture-aws upload-s3 smoke-aws fetch-inmet train-ml-inmet export-faostat export-faostat-offline train-yolo build-agri build-agri-ci verify-agri-models download-gibs augment-dataset build-dataset-full

VENV_PYTHON := .venv/bin/python

install:
	cd src && $(VENV_PYTHON) -m pip install -r requirements.txt

# API + dashboard na mesma porta (8000) — requer best.pt em src/models/weights/
demo:
	@test -x $(VENV_PYTHON) || (echo "Crie o venv: python3 -m venv .venv && $(VENV_PYTHON) -m pip install -r src/requirements.txt" && exit 1)
	@echo "Iniciando API + dashboard em http://127.0.0.1:8000"
	cd src && ../$(VENV_PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Suite completa (mesmo comando do CI; exclui E2E Playwright)
test:
	cd src && PYTHONPATH=. ../$(VENV_PYTHON) -m pytest ../tests/ tests/ -q -m "not e2e"

# Suite com cobertura mínima de 82% (meta +20% sobre baseline ~62%)
test-coverage:
	cd src && PYTHONPATH=. ../$(VENV_PYTHON) -m pytest ../tests/ tests/ -q -m "not e2e" \
		--cov=app --cov-config=../.coveragerc --cov-report=term-missing --cov-fail-under=82

# E2E Playwright — dashboard no browser (requer: python -m playwright install chromium)
test-e2e:
	@test -x $(VENV_PYTHON) || (echo "Crie o venv: python3 -m venv .venv && $(VENV_PYTHON) -m pip install -r src/requirements.txt" && exit 1)
	$(VENV_PYTHON) -m playwright install chromium
	cd src && PYTHONPATH=. ../$(VENV_PYTHON) -m pytest ../tests/e2e/ -q -m e2e

# Frontend: HTML estático (pytest) + E2E Playwright
test-frontend: test-e2e
	cd src && PYTHONPATH=. ../$(VENV_PYTHON) -m pytest ../tests/test_dashboard_html.py -q

test-api:
	cd src && PYTHONPATH=. ../$(VENV_PYTHON) -m pytest ../tests/test_api_endpoints.py -q

test-storms:
	cd src && PYTHONPATH=. ../$(VENV_PYTHON) -m pytest ../tests/test_storm_alerts_query.py -q

# Captura NASA Worldview (requer playwright: playwright install chromium)
nasa-capture:
	cd src && ../$(VENV_PYTHON) -m app.cron.capture_nasa_data

# Captura + JPG em screenshots/ (dispara Lambda S3; sem YOLO local)
nasa-capture-aws:
	cd src && ../$(VENV_PYTHON) -m app.cron.capture_nasa_data --upload-cv-jpg

# Upload capturas locais existentes para S3
# UPLOAD_JPG=1 → só JPG (Lambda); UPLOAD_CV=1 → JPG + YOLO local (dev)
upload-s3:
	cd src && ../$(VENV_PYTHON) -m app.cron.upload_nasa_to_s3 \
		$(if $(UPLOAD_JPG),--upload-jpg,) \
		$(if $(UPLOAD_CV),--cv,)

smoke-aws:
	$(VENV_PYTHON) scripts/smoke_aws_e2e.py

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
	$(VENV_PYTHON) scripts/build_agri_pipeline.py --ci --skip-faostat --skip-ga

verify-agri-models:
	$(VENV_PYTHON) scripts/build_agri_pipeline.py --verify-only

train-yolo:
	$(VENV_PYTHON) src/yolo_training.py --epochs 40 --batch 8 --recall-focus --validate

# Treino com yolov5m + MPS (Apple Silicon) — mais lento mas mais preciso
train-yolo-medium:
	$(VENV_PYTHON) src/yolo_training.py --model yolov5m --epochs 100 --batch 16 \
		--device mps --patience 40 --recall-focus --validate

# ── Dataset YOLO ────────────────────────────────────────────────────────────────

# Baixa ~1620 imagens do NASA GIBS WMS (9 regiões × 90 dias × 2 horários)
# Sem Playwright — download HTTP paralelo (~10–15 min)
download-gibs:
	$(VENV_PYTHON) scripts/goes_pipeline/00_download_gibs.py --limpar --dias 90 --workers 8

# Gera versões augmentadas do dataset base (target: ≥300 imgs em data/training-dataset-1000/)
augment-dataset:
	$(VENV_PYTHON) scripts/goes_pipeline/07_augment_dataset.py --target 300

# Pipeline completo: download GIBS → YOLO labels → augmentação → treino
build-dataset-full:
	$(VENV_PYTHON) scripts/goes_pipeline/00_download_gibs.py --limpar --dias 90 --workers 8
	$(VENV_PYTHON) scripts/goes_pipeline/04_nasa_to_yolo.py --clean --limiar 175 --area 50
	$(VENV_PYTHON) scripts/goes_pipeline/06_audit_labels.py --strict
	$(VENV_PYTHON) scripts/goes_pipeline/07_augment_dataset.py
	$(VENV_PYTHON) src/yolo_training.py --epochs 100 --batch 16 --recall-focus --validate
