# Short commands for the Docker-based workflow.
# Every target runs inside the `dev` container defined in compose.yaml, so you
# don't need Python, DuckDB, dbt or pytest installed on your computer.
#
#   make help     -> list the commands

# Run containers as your own user so generated files belong to you.
export HOST_UID := $(shell id -u)
export HOST_GID := $(shell id -g)

# `docker compose run --rm dev <cmd>` = start a throwaway container from the
# dev image, run one command, then delete the container. Files written to the
# bind-mounted project folder (data/, warehouse/) stay on your disk.
COMPOSE_RUN := docker compose run --rm
RUN := $(COMPOSE_RUN) dev

.DEFAULT_GOAL := help
.PHONY: help build shell generate-data load query test versions down clean

help: ## Show this list of commands
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  make %-15s %s\n", $$1, $$2}'

build: ## Build the dev image (Python + DuckDB + dbt + pytest)
	docker compose build

shell: ## Open a bash shell inside the dev container
	$(RUN) bash

generate-data: ## Write the synthetic source CSVs to data/source/
	$(RUN) python scripts/generate_data.py

load: ## Full-refresh the CSVs into warehouse/warehouse.duckdb (schema raw)
	$(RUN) python scripts/load_data.py

query: ## Run SQL read-only, e.g. make query SQL="SELECT count(*) FROM raw.orders"
	$(COMPOSE_RUN) -e SQL dev python scripts/query.py

test: ## Run the Python tests
	$(RUN) pytest

versions: ## Print the tool versions inside the container
	$(RUN) sh -c 'python --version && python -c "import duckdb; print(\"duckdb\", duckdb.__version__)" && dbt --version && pytest --version'

down: ## Remove leftover containers/networks (your data and warehouse are kept)
	docker compose down

clean: ## DELETE generated CSVs and the warehouse file (regenerate with make generate-data load)
	rm -f data/source/*.csv warehouse/warehouse.duckdb warehouse/warehouse.duckdb.wal
