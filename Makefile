.PHONY: setup run test lint validate-content db-init db-reset

setup:
	pip install -r requirements-dev.txt

run:
	streamlit run src/pcc/main.py

test:
	pytest --cov

lint:
	ruff check src tests
	ruff format --check src tests
	mypy src/pcc/domain src/pcc/workflow

validate-content:
	python scripts/validate_content.py

db-init:
	python scripts/init_db.py

db-reset:
	python scripts/reset_demo.py
