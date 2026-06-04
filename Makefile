.PHONY: install demo test-api test-storms

install:
	cd src && pip install -r requirements.txt

# API (8000) + Dashboard Flask (5000) — requer best.pt em src/models/weights/
demo:
	@echo "Iniciando API em :8000 e Dashboard em :5000"
	@echo "Abra http://localhost:5000"
	@(cd src && uvicorn app.main:app --host 0.0.0.0 --port 8000) & \
	 sleep 2 && \
	 cd src && python dashboard/app.py

test-api:
	cd src && pytest ../tests/test_api_endpoints.py -q

test-storms:
	cd src && pytest ../tests/test_storm_alerts_query.py -q
