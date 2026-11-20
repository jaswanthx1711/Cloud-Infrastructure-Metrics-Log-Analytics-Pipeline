.PHONY: help install run dashboard test export setup-dbt clean all

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

run: ## Run the full ETL pipeline
	python3 etl/pipeline.py

dashboard: ## Launch the Streamlit dashboard (runs pipeline first if DB missing)
	@[ -f data/analytics.db ] || $(MAKE) run
	python3 -m streamlit run dashboard/kpi_dashboard.py

test: ## Run the test suite
	python3 -m pytest tests/ -v

export: ## Export CSVs / Excel / BI files
	python3 etl/export_for_bi.py

setup-dbt: ## Copy dbt profiles example to ~/.dbt/profiles.yml
	@mkdir -p ~/.dbt
	@cp dbt/profiles.yml.example ~/.dbt/profiles.yml
	@echo "Copied dbt/profiles.yml.example -> ~/.dbt/profiles.yml. Edit it to set your DB path."

clean: ## Remove generated data and analytics database
	rm -rf data/raw data/processed data/bi_exports data/analytics.db
	@echo "Cleaned generated data."

all: install run test ## Install deps, run pipeline, run tests
