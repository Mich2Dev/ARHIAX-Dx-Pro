install:
	pip install -e .[dev]

run:
	uvicorn arhiax_dx.main:app --host 0.0.0.0 --port 8088 --app-dir src

test:
	pytest -q

audit-check:
	python -m compileall src
	pytest -q

validate-install:
	python -m arhiax_dx.installation

bootstrap-install:
	python -m arhiax_dx.installation_assets
